---
layout: post
title: "Creating D state (uninterruptible sleep) processes on demand"
---

At [work](https://meta.com) several years ago I received what at the time I
thought was a pretty niche request. A team in the containers space was testing
container teardown, and wanted to make sure that their software was robust to D
state processes. I gave them some ideas, they implemented it, and that was
that. Fast forward to today, and I think I must have seen this request at least
four or five time in my time at the company, which suggests that while this may
still be a niche request, there's clearly a noticeable void in readily
accessible knowledge on the subject. Hopefully this article can improve that
somewhat :-)

## Why would anyone want to test this?

The D (uninterruptible sleep) state is a process state where a process is
sleeping and cannot be interrupted or killed directly by signals<sup>* see
`TASK_KILLABLE` note</sup>. This can become a problem for things like init
systems or containerisation platforms where the unwavering persistence of such
processes must be planned for and have strategies in place to not block forward
progress.

<small><sup>*</sup> This is true in the majority of cases, but we do also have
`TASK_KILLABLE` where fatal signals (i.e. signals with terminal state and no
userspace signal handler) can still terminate the application in this
state.</small>

One example of where this is used is in DMA transfers and the like. DMA allows
hardware subsystems to access the main system memory for reading/writing
independently of the CPU, which is essential for efficient handling of large
volumes of data. Programs generally must not be interrupted in the midst of
such operations because DMA transfers are not typically designed to accommodate
or recover from partial or interrupted reads or writes.

These states can become a problem for things like init systems or
containerisation platforms where the unwavering persistence of such processes
must be planned for and have strategies in place to not block forward progress.

## D states outside of I/O context

While D states might immediately bring to mind disk activity, we actually use
them for all sorts of things in the kernel. For example, we also use them to
block processes where we cannot safely make progress for other reasons.

Enter `vfork`. `vfork` is a specialized system call primarily designed for
creating new processes. Unlike the more widely known `fork`, which typically
uses copy-on-write and thus must at the very least create new virtual mappings
to the physical pages in question, `vfork` allows the child process to directly
share the parent's virtual address space temporarily.

Both are more typically supplanted by `clone()` with the appropriate flags
nowadays, which has more sensible semantics and is much more configurable. That
allow for (for example) having both the calling process and the child running
simultaneously in same virtual memory space if you pass `CLONE_VM` but not
`CLONE_VFORK`. Goodness gracious!

For this case, though, we want `vfork`'s behaviour, which is to suspend the
parent application in D state. Here is how we can reliably create a D state
process with `vfork`:

{% highlight c %}
#include <unistd.h>

int exit_logic(void) {

int main(void) {
{
    pid_t pid = vfork();
    if (pid == 0) {
        pause(); /* or some other exit logic for the child */

        /* It's not safe to continue after child stack modifications, so make
         * sure we don't execute any more userspace instructions for the whole
         * process group. */
        kill(0, SIGKILL);
    } else if (pid < 0) {
        return 1;
    }
    return 0;
}
{% endhighlight %}

This will then reliably create a D state process until a signal is sent:

{% highlight bash %}
scratch % cc -o dstate dstate.c
scratch % ./dstate & { sleep 0.1; ps -o pid,state,cmd -p "$!"; }
[1] 780629
    PID S CMD
 780629 D ./dstate
scratch % kill "$!"
[1]  + terminated  ./dstate
{% endhighlight %}

`pause()` can be modified to suit. For example, if your test involves sending
signals and so you want to ignore those, you can instead wait for the text
"EXIT" on stdin:

{% highlight c %}
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#define EXIT_STRING "EXIT\n"

void run_child(void) {
    char input[sizeof(EXIT_STRING)];

    while (1) {
        if (fgets(input, sizeof(input), stdin) == NULL) {
            break;
        }
        if (strcmp(input, EXIT_STRING) == 0) {
            break;
        }
    }
}

int main(void)
{
    pid_t pid;
    sigset_t set;

    sigfillset(&set);
    sigprocmask(SIG_BLOCK, &set, NULL);

    pid = vfork();

    if (pid == 0) {
        run_child();
        sigprocmask(SIG_UNBLOCK, &set, NULL);
        kill(0, SIGKILL);
    } else if (pid < 0) {
        return 1;
    }
    return 0;
}
{% endhighlight %}

But why is it that we need `kill(0, SIGKILL)`, anyway? Well, stack modification
(and thus doing basically anything other than `exec` or `_exit`) is not
POSIX-legal in the child forked by vfork, because the parent cannot reasonably
have the stack mutated under it without its knowledge.<sup>* see CPython
note</sup>

<small><sup>*</sup>  Well, that's what POSIX says, at least. In reality on
Linux with any real libc, things are not that dire. CPython, for example, uses
it as part of a vastly more complex process of forking children which is
guaranteed to push to stack by calling child functions and the world hasn't
collapsed yet (see
[here](https://github.com/python/cpython/blob/v3.12.1/Modules/_posixsubprocess.c#L812-L823)
and
[here](https://github.com/python/cpython/blob/v3.12.1/Modules/_posixsubprocess.c#L553-L571)).
In reality, when the parent process continues its operation, additional stack
pushes are going to end up in the unallocated portion of the stack. The paused
parent's stack pointer register is still independent, even with `vfork`, so
things just continue about their merry way regardless of any POSIX ire.</small>

While the parent cannot handle the signal right now, it will be queued in the
kernel's signal queue. This ensures that no more userspace instructions for
this now highly fragile process will be executed, and the kernel will simply
tear down the process entirely.

The simplicity and flexibility of the vfork approach make it ideal for most use
cases. It doesn’t require complex setup, can easily be modified to be suitable
for different testing conditions, and it's generally fairly self contained.

## D states in I/O context
