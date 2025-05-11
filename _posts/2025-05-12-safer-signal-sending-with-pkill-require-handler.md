---
layout: post
title: "Preventing outages with pkill's new --require-handler"
description: "A safer approach to using signals in production systems, avoiding service outages when signal handlers are removed."
---

A little while ago, I wrote an [article about the dangers of signals in
production](https://developers.facebook.com/blog/post/2022/09/27/signals-in-prod-dangers-and-pitfalls/),
where I detailed a particularly frustrating outage in Meta production caused by
the removal of an innocent looking SIGHUP handler. The story goes something
like this:

1. An application uses SIGHUP for some useful purpose (configuration reload,
   log rotation).
2. Later, this functionality is deprecated or removed, and the signal handler
   is removed too.
3. However, one callsite sending the signal (often in logrotate or a service
   manager) is missed.
4. Later, when this callsite fires, the application begins terminating when it
   receives the now unhandled signal.
5. Production goes down in the middle of the night.

While avoiding signals altogether is ideal for many cases, realistically
they're deeply embedded in the Linux ecosystem, so as part of my work trying to
improve Linux quality and safety I've been working on ways to make signals less
dangerous when they're unavoidable.

This type of outage is particularly insidious because the change that
introduces it seems innocent, and the failure often happens weeks later. To
address this exact problem, I've added the new `--require-handler` flag to
`pkill` that provides a safety net for situations just like this.

## The dangers of signals

To understand the underlying problem here, let me briefly recap the incident
that inspired it. At Meta, we have a service called
[LogDevice](https://engineering.fb.com/2017/08/31/core-infra/logdevice-a-distributed-data-store-for-logs/).
Along with all its other useful functionality, it had a SIGHUP handler to
manage log file rotation. One day, the team cleaned up their codebase and
removed some unused features, including the code that responded to SIGHUP
signals.

Everything worked fine for a few weeks until suddenly, service nodes started
dropping at an alarming rate in the middle of the night. As it turned out,
there was a logrotate configuration that was still sending SIGHUP to the
process when rotating logs. With the handler removed, the default behaviour for
SIGHUP in the kernel kicked in: immediate termination.

The fundamental issue is that many signals, including the commonly used
`SIGHUP`, have a default disposition of terminating the process. This is a
relic from the early Unix days when `SIGHUP` meant "hangup" -- that is, the
terminal connection was severed, and there was no point in the process
continuing to run. Today, `SIGHUP` is widely used for a different purpose: to
request applications to reload their configuration or rotate their logs.

{% sidenote %}
Many innocent looking signals have default dispositions that are actually quite
perilous. Here are a few that terminate by default but are often repurposed:

- `SIGHUP`: Originally for "terminal hangup", and if this was used only as it
   was originally intended, defaulting to terminate would be sensible. With the
   current mixed usage meaning "reopen files," this is dangerous.
- `SIGUSR1` and `SIGUSR2`: These are "user-defined signals" that you can
   ostensibly use however you like. But because these are terminal by default,
   if you implement USR1 for some specific need and later don't need that, you
   can't just safely remove the code. You have to consciously think to
   explicitly ignore the signal. That's really not going to be obvious even to
   every experienced programmer.
- `SIGIO`: Used for asynchronous I/O. Or killing your process. It's a 50/50.

Having these terminate by default is a dangerous footgun for application
developers, but it's unfortunately one we have to live with due to backwards
compatibility.
{% endsidenote %}

This exact scenario has caused multiple production incidents at Meta, and I've
heard similar stories from colleagues at other companies. It's particularly
insidious because:

1. The change that removes the signal handler often seems harmless
2. Testing rarely catches it because the signal isn't triggered in test environments
3. The failure can occur weeks or months after the code change

## Mitigating with --require-handler

As part of my work to mitigate some of the dangers around signals, I've added a
new flag to `pkill` called `--require-handler` (or `-H` for short). This flag
ensures that signals are only sent to processes that have actually registered a
handler for that signal.

Let's look at a typical logrotate configuration that you might find in the
wild:

{% highlight bash %}
/var/log/cron
/var/log/maillog
/var/log/messages
/var/log/secure
/var/log/spooler
{
    sharedscripts
    postrotate
        /bin/kill -HUP `cat /var/run/syslogd.pid 2> /dev/null` 2> /dev/null || true
    endscript
}
{% endhighlight %}

This pattern is extremely common in system administration scripts. It reads a
PID from a file and sends a signal directly. But it has no way to verify
whether the process actually has a handler for that signal before sending it.

With the new `--require-handler` flag, we can combine it with pkill's existing
`-F` flag (which reads PIDs from a file) to create a much safer alternative:

{% highlight bash %}
/var/log/cron
/var/log/maillog
/var/log/messages
/var/log/secure
/var/log/spooler
{
    sharedscripts
    postrotate
        pkill -H -HUP -F /var/run/syslogd.pid 2> /dev/null || true
    endscript
}
{% endhighlight %}

This version only sends a SIGHUP signal if the process has a handler,
preventing accidental termination. It's also a lot simpler than the original
shell command, with fewer moving parts and subshells.

## How does it work?

So how does `pkill` detect whether a process has a signal handler registered?
The answer lies in the Linux procfs interface, specifically in
`/proc/[pid]/status`.

If you examine this file for any running process, you'll find several
signal-related fields:

{% highlight bash %}
$ cat /proc/self/status
...
SigQ:   0/31367
SigPnd: 0000000000000000
SigBlk: 0000000000000000
SigIgn: 0000000000380004
SigCgt: 0000000180000000
...
{% endhighlight %}

The key field here is `SigCgt` (that is, "signals caught"), which shows which
signals have userspace handlers registered. These fields are hexadecimal
bitmaps where each bit represents a signal number. If bit N-1 is set, it means
there's a handler for signal N.

The implementation of the `--require-handler` flag is quite straightforward. It
reads this bitmap from `/proc/[pid]/status` and checks if the bit corresponding
to the signal is set:

{% cc %}
{% highlight c %}
static unsigned long long unhex (const char *restrict in)
{
    unsigned long long ret;
    char *rem;
    errno = 0;
    ret = strtoull(in, &rem, 16);
    if (errno || *rem != '\0') {
        xwarnx(_("not a hex string: %s"), in);
        return 0;
    }
    return ret;
}

static int match_signal_handler (const char *restrict sigcgt, const int signal)
{
    return sigcgt && (((1UL << (signal - 1)) & unhex(sigcgt)) != 0);
}
{% endhighlight %}
<div class="citation"><a href="https://gitlab.com/procps-ng/procps/-/blob/092ecde3601eb3979335ec1ff1fe598044c4b58f/src/pgrep.c">src/pgrep.c</a> from procps-ng</div>
{% endcc %}

{% sidenote %}
Here's a standalone program which can decode hexadecimal bitmaps like `SigCgt`,
`SigPnd`, and the like:

{% highlight c %}
#define _GNU_SOURCE

#include <inttypes.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int exit_code = 0;

static void print_signals(uint64_t bitmap)
{
    for (int sig = 1; sig < NSIG; ++sig) {
        if (bitmap & (1ULL << (sig - 1))) {
            const char *sig_name = sigabbrev_np(sig);
            if (sig_name) {
                printf("%s\n", sig_name);
            } else {
                fprintf(stderr, "Unknown signal: %d\n",
                        sig);
                exit_code = 1;
            }
        }
    }
}

int main(int argc, char *argv[])
{
    uint64_t bitmap;

    if (argc != 2) {
        fprintf(stderr, "Usage: %s <bitmap>\n", argv[0]);
        return EXIT_FAILURE;
    }

    if (sscanf(argv[1], "%" SCNx64, &bitmap) != 1) {
        fprintf(stderr, "Invalid signal bitmap hex: %s\n",
                argv[1]);
        return EXIT_FAILURE;
    }

    print_signals(bitmap);

    return exit_code;
}
{% endhighlight %}

Provide the signal bitmap from `/proc/pid/status`, and this program will tell
you which signal(s) are pending:

    % cc -o signal-bitmap signal-bitmap.c
    % ./signal-bitmap 0000000000000100
    KILL
{% endsidenote %}

Let's see this in action with a concrete example. First, let's create a simple
program that installs a SIGHUP handler:

{% highlight c %}
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

static volatile sig_atomic_t hup;
void handler(int sig){ (void)sig; hup = 1; }

int main(){
    struct sigaction sa = { .sa_handler = handler };
    if (sigaction(SIGHUP, &sa, 0) < 0) exit(1);

    FILE *f = fopen("/tmp/test.pid", "w");
    if (!f) exit(1);
    if (fprintf(f, "%d\n", getpid()) < 0) exit(1);
    fclose(f);

    for (;;) {
        pause();
        if (hup) {
            hup = 0;
            printf("Reloading...\n");
        }
    }
}
{% endhighlight %}

If we compile and run this program, we can then check if it has a SIGHUP
handler using our new flag:

{% highlight bash %}
$ grep SigCgt /proc/12345/status
SigCgt: 0000000000000001

$ pkill -H -HUP -F /tmp/test.pid
$ # Process is still alive and handled the signal

$ pkill -H -USR1 -F /tmp/test.pid
$ # No match (no USR1 handler), so no signal sent
{% endhighlight %}

Now let's try a process without a handler:

{% highlight c %}
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(){
    FILE *f = fopen("/tmp/nohandler.pid", "w");
    if (!f) exit(1);
    if (fprintf(f, "%d\n", getpid()) < 0) exit(1);
    fclose(f);
    pause();
}

{% endhighlight %}

And test it:

{% highlight bash %}
$ grep SigCgt /proc/12346/status
SigCgt: 0000000000000000

$ pkill -H -HUP -F /tmp/nohandler.pid
$ # No match, nothing happens
$ pkill -HUP -F /tmp/nohandler.pid
$ # Process terminated due to unhandled SIGHUP
{% endhighlight %}

## Real world implementation

`--require-handler` is most valuable in system management contexts where
signals are traditionally used for control, such as:

1. **Log rotation scripts**: When telling a service to reopen its logs
2. **Configuration management**: When asking a service to reload its config
3. **Service control scripts**: When controlling long running processes

For example, you can audit your `/etc/logrotate.d/` directory and update any
`postrotate` scripts that send signals:

{% highlight bash %}
# Before
/var/log/nginx/*.log {
    daily
    rotate 14
    # ...
    postrotate
        kill -HUP $(cat /var/run/nginx.pid)
    endscript
}

# After
/var/log/nginx/*.log {
    daily
    rotate 14
    # ...
    postrotate
        pkill -H -HUP -F /var/run/nginx.pid || true
    endscript
}
{% endhighlight %}

The `|| true` ensures that even if no processes match (because they don't have
handlers), the logrotate script still succeeds. Use it if that's the behaviour
you want.

## Why not just... fix your code?

Some might ask why one shouldn't just have the code keep the signal handler
even if you don't need it any more. That's certainly an option -- you could
keep an empty handler that does nothing. But there are several issues with this
approach, most notably that over time, you'd accumulate handlers for signals
that your application no longer uses, making the code less clear. Developers
now need to remember which signals must keep handlers even though they're no
longer used, and it's unclear if they can be used again for other purposes
later.

The `--require-handler` flag gives us a better solution by moving the safety
check from the application to the signal sender, which is much closer to where
the actual problem occurs.

In general, when removing a signal handler from your application, do a thorough
search for any code or configuration that might send that signal to your
process. This includes:

- System tools like logrotate, systemd units, or cron jobs
- Management scripts or tools
- Monitoring systems that might send signals
- Any other services that interact with yours

`--require-handler` adds a safety net, but where possible it's still ideal to
clean up all signal senders when removing a handler.

All in all, the new `--require-handler` flag in `pkill` provides a simple but effective
safeguard against one of the most common signal-related problems in production
environments. This isn't a silver bullet for all signal related issues --
signals still have many other problems as detailed in my previous article --
but for systems where signals can't be entirely avoided, this flag adds a
meaningful layer of protection.

The new functionality is in procps-ng 4.0.3, which should be in most
distributions now. While signals might be deeply entrenched in Unix and Linux,
that doesn't mean we can't make them safer to use. The `--require-handler` flag
is one small step toward that goal. For new applications, I still recommend
using more explicit IPC mechanisms when possible, but for existing systems,
this flag can help prevent those dreaded midnight wake-up calls when logrotate
innocently goes about its business. :-)

And many thanks to [Craig](https://gitlab.com/csmall) for reviewing the patch!
