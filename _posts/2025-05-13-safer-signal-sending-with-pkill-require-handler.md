---
layout: post
title: "Preventing outages with pkill's new --require-handler flag"
description: "A safer approach to using signals in production systems, avoiding service outages when signal handlers are removed."
---

A little while ago, I wrote an [article about the dangers of signals in
production](https://developers.facebook.com/blog/post/2022/09/27/signals-in-prod-dangers-and-pitfalls/),
where I detailed a particularly frustrating outage in Meta production caused by
the removal of a SIGHUP handler. At Meta, we have a service called
[LogDevice](https://engineering.fb.com/2017/08/31/core-infra/logdevice-a-distributed-data-store-for-logs/).
As many other daemons do, LogDevice had a signal handler registered for SIGHUP,
with the goal being to reopen the log file after rotation. All pretty innocuous
stuff.

One day, the team cleaned up their codebase and removed some unused features,
including the code that responded to SIGHUP signals, which was now unneeded as
it was handled in another way. They thought they had also removed all callsites
which sent SIGHUP.

Everything worked fine for a few weeks until, suddenly, service nodes started
dropping at an alarming rate in the middle of the night, and a LogDevice outage
occurred. As it turned out, there was a logrotate configuration that was still
configured to send SIGHUP to the process after rotating logs. With the handler
now removed, the default behaviour for SIGHUP in the kernel kicked in instead
-- to immediately terminate the process.

Importantly this wasn't just on one machine, but across a whole cluster.
Services, of course, must be designed to handle restarts or machines or racks
falling offline, but when thousands of servers terminate at once, things become
far more complicated. Replicas need to promote primaries en masse, connection
pools collapse, cache coherency breaks down, and eventually, you simply don't
have enough capacity to run your service properly.

## Why are signals so problematic?

The fundamental issue is that many signals, including the widely used `SIGHUP`,
have a default disposition of terminating the process. This reflects the
literal meaning embedded in `SIGHUP`'s name -- "hangup" -- which indicates the
terminal connection was severed, making continued process execution
unnecessary. This original meaning remains valid today, and is used in places
like remote SSH sessions where disconnection triggers process termination.

SIGHUP has, however, also started moonlighting with an additional purpose:
requesting applications to reload their configuration or rotate their logs.
This mixed interpretation of `SIGHUP` emerged because daemon processes
typically run detached from any controlling terminal, so since these background
services wouldn't naturally receive terminal disconnection signals, `SIGHUP`
was repurposed by application authors. Unfortunately, these mixed signals about
`SIGHUP`'s meaning create a confusing interface with competing
interpretations.

{% sidenote %}
Many innocent looking signals have default dispositions that are actually quite
perilous. Here are a few others that terminate by default that you might not
expect:

- `SIGUSR1` and `SIGUSR2`: These are "user-defined signals" that you can
   ostensibly use however you like. But because these terminate by default,
   if you implement USR1 for some specific need and later don't need that, you
   can't just safely remove the code. You have to consciously think to
   explicitly ignore the signal. That's really not going to be obvious even to
   every experienced programmer.
- `SIGPROF`: Designed as part of profiling timer expiration. Apparently your
  program's time may be up in more ways than one.
- ...and `SIGIO`, `SIGPOLL`, `SIGHUP`, etc.

Having these terminate by default is a dangerous footgun for application
developers, but it's unfortunately one we have to live with due to backwards
compatibility.
{% endsidenote %}

This exact scenario has caused multiple production incidents at Meta, and I've
heard similar stories from colleagues at other companies. It's particularly
insidious because:

1. The change that removes the signal handler often seems harmless
2. Testing rarely catches it because the signal isn't triggered until much
   later
3. The failure can occur weeks or months after the code change

## Mitigating with \-\-require-handler

As part of my work to mitigate some of the dangers around signals, I've [added a
new flag to `pkill` called
`--require-handler`](https://gitlab.com/procps-ng/procps/-/merge_requests/165) (or `-H` for short). This flag
ensures that signals are only sent to processes that have actually registered a
handler for that signal.

For an example of how it can avoid these kinds of incidents, let's look at a
typical logrotate configuration that you might find in the wild:

{% highlight bash %}
/var/log/cron
/var/log/maillog
/var/log/messages
/var/log/secure
/var/log/spooler
{
    sharedscripts
    postrotate
        /bin/kill -HUP `cat /var/run/syslogd.pid` || true
    endscript
}
{% endhighlight %}

This pattern is extremely common in system administration scripts. It reads a
PID from a file and sends a signal directly. However, it has no way to verify
whether the process actually has a handler for that signal before sending it.

We can combine the new `pkill -H` flag with pkill's existing `-F` flag (which
reads PIDs from a file) to create a much safer alternative:

{% highlight bash %}
/var/log/cron
/var/log/maillog
/var/log/messages
/var/log/secure
/var/log/spooler
{
    sharedscripts
    postrotate
        pkill -H -HUP -F /var/run/syslogd.pid
    endscript
}
{% endhighlight %}

This version only sends a `SIGHUP` signal if the process has a `SIGHUP`
handler, preventing accidental termination. It's also a lot simpler than the
original shell command, with fewer moving parts and subshells.

It's worth also noting that `pkill -H` doesn't silently hide the problem. When
no process with a matching handler is found, it returns exit code 1, which
means your log rotation or other scripts will explicitly fail, triggering
alerts in monitoring systems. Instead of an unexpected process termination that
might go undetected until service degradation occurs, you now have a specific,
actionable error that points directly to the root cause: a missing signal
handler.

To be clear: `pkill -H` is not intended to replace proper engineering practices
like thorough auditing of signal senders, rigorous testing, canaries, or
careful code reviews. Rather, it provides an additional safety net when,
inevitably, things slip through the cracks when those processes inevitably miss
something in complex systems. The goal is to transform an uncontrolled,
catastrophic failure (termination of a service process widely across a fleet)
into a controlled, traceable one (a failed log rotation that triggers an
alert).

## How does it work?

So how does `pkill` detect whether a process has a signal handler registered?
The answer lies in the Linux procfs interface, specifically in
`/proc/[pid]/status`.

If you examine this file for any extant process, you'll find several
signal-related fields:

{% highlight bash %}
% grep '^Sig' /proc/self/status
SigQ:   0/254456
SigPnd: 0000000000000000
SigBlk: 0000000000000000
SigIgn: 0000000000000000
SigCgt: 0000000000000400
{% endhighlight %}

The key field here is `SigCgt` (that is, "signals caught"), which shows which
signals have userspace handlers registered in this process. These fields are
hexadecimal bitmaps where each bit represents a signal number. If bit N-1 is
set, it means there's a handler for signal N. From `man 5 proc_pid_status`:

{% cc %}
> SigBlk, SigIgn, SigCgt: Masks (expressed in hexadecimal) indicating signals
> being blocked, ignored, and caught (see `signal(7)`).
<div class="citation">from <a href="https://man7.org/linux/man-pages/man5/proc_pid_status.5.html">man 5 proc_pid_status</a></div>
{% endcc %}

So to interpret these, we first decode these from hexadecimal, and then check
the relevant bit position. For `SIGUSR1`, for example, we can see the value the
value is 10:

{% highlight bash %}
% kill -l USR1
10
{% endhighlight %}

So since we have a userspace signal handler if bit N-1 is set, we should check
if bit 9 is set.

That's exactly how this new feature works, too. When you call `pkill -H`, we
read the bitmap from `/proc/[pid]/status` and check if the bit corresponding to
the signal is set:

{% cc %}
{% highlight c %}
static unsigned long long unhex(const char *restrict in) {
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

static int match_signal_handler(const char *restrict sigcgt,
                                const int signal) {
    return sigcgt &&
           (((1UL << (signal - 1)) & unhex(sigcgt)) != 0);
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
void handler(int sig) {
    (void)sig;
    hup = 1;
}

int main() {
    struct sigaction sa = {.sa_handler = handler};
    if (sigaction(SIGHUP, &sa, 0) < 0) {
        exit(1);
    }

    FILE *f = fopen("/tmp/handler.pid", "w");
    if (!f) {
        exit(1);
    }
    if (fprintf(f, "%d\n", getpid()) < 0) {
        exit(1);
    }
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

$ pkill -H -HUP -F /tmp/handler.pid
$ # Process is still alive and handled the signal

$ pkill -H -USR1 -F /tmp/handler.pid
$ # No match (no USR1 handler), so no signal sent
{% endhighlight %}

Now let's try a process without a handler:

{% highlight c %}
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main() {
    FILE *f = fopen("/tmp/nohandler.pid", "w");
    if (!f) {
        exit(1);
    }
    if (fprintf(f, "%d\n", getpid()) < 0) {
        exit(1);
    }
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

`pkill -H` is most valuable in system management contexts where signals are
traditionally used for control, such as:

1. When telling a service to reopen or rotate its logs
2. When asking a service to reload its config
3. When controlling long running processes through signals

For example, you can audit your `/etc/logrotate.d/` directory and update any
`postrotate` scripts that send signals from something like this:

{% highlight bash %}
/var/log/nginx/*.log {
    daily
    rotate 14
    # ...
    postrotate
        kill -HUP $(cat /var/run/nginx.pid)
    endscript
}
{% endhighlight %}

...to something like this:

{% highlight bash %}
/var/log/nginx/*.log {
    daily
    rotate 14
    # ...
    postrotate
        pkill -H -HUP -F /var/run/nginx.pid
    endscript
}
{% endhighlight %}

With this, when there is no signal handler registered, the `pkill` command will
exit with a non-zero status code, causing your logrotate job to fail. This
failure becomes a useful signal in itself, as you can leverage this behaviour
to find no longer needed signal senders and investigate the best course of
action.

## Due diligence

In general, when removing a signal handler from your application, it pays to do
some spelunking and dig through any code or configuration that might send that
signal to your process. This might include:

- System tools like logrotate, systemd units, or cron jobs
- Management scripts or tools
- Monitoring systems that might send signals
- Any other services that interact with yours

Here is a small [bpftrace](https://bpftrace.org/) program which can also help.
Pass it a pid on the command line, and it will tell you which signals are being
sent to that pid, and by which process:

{% highlight bash %}
#!/usr/bin/env bpftrace

BEGIN {
    if ($# < 1) {
        printf("Usage: ./sigcheck.bt PID\n");
        exit();
    }
    @target = $1;
    printf("Tracing signals sent to PID %d, ^C to end\n", @target);
}

tracepoint:signal:signal_generate
/ args->pid == @target /
{
    @sig_count[args->sig]++;
    /* pid/comm are from the _sending_ pid */
    printf("pid=%-6d comm=%-16s sig=%d\n", pid, comm, args->sig);
}

END {
    printf("\nSignal summary for PID %d:\n", @target);
    print(@sig_count);
    clear(@target);
    clear(@sig_count);
}
{% endhighlight %}

    $ sudo ./sigcheck.bt 882492
    Attaching 3 probes...
    Tracing signals sent to PID 882492, ^C to end
    from pid=1      comm=systemd          sig=1
    from pid=885998 comm=kill             sig=10
    from pid=1      comm=systemd          sig=1
    ^C
    Signal summary for PID 882492:
    @sig_count[1]: 2
    @sig_count[10]: 1

This program can help you find signals being sent that you might not be
expecting before you land a change to remove a signal handler.

Using `pkill -H` adds a safety net, but where possible it's still ideal to
clean up all signal senders when removing a handler, and prefer to use other
kinds of IPC (like [varlink](https://varlink.org/) or similar) to signal for
state changes where possible. All in all, `pkill -H` provides a simple but
effective defence in depth safeguard against one of the most common
signal-related problems in production environments. This isn't a silver bullet
for all signal related issues -- signals still have many other problems as
detailed in my previous article -- but for systems where signals can't be
entirely avoided, this flag adds a meaningful layer of protection.

In terms of eliminating the straggling signal senders in our production
environment, we've found that a combined strategy works best:

- Using `pkill -H` as a safety net when setting up signal senders
- Monitoring and providing data around signal use through eBPF
- Improving process resilience and IPC strategy over time to not use signals
  where possible

This multi-layered approach helps us balance our production safety needs
without producing long-term cruft in the form of unused signals.

`pkill -H` was released as part of procps-ng 4.0.3, which should be in most
distributions now. While signals might be deeply entrenched in Unix and Linux,
that doesn't mean we can't make them safer to use, and `pkill -H` is one step
towards that goal. For new applications, I still recommend using more explicit
IPC mechanisms when possible, but for every system where that's not practical,
using `pkill -H` is a great way to eliminate this class of outage entirely.

Many thanks to [Craig](https://gitlab.com/csmall) for reviewing the patch, and
[Diego](https://flameeyes.blog/) and [Michael](https://github.com/michaelneu)
for providing suggestions on this post.
