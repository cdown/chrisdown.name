---
layout: post
title: "Creating D state (uninterruptible sleep) processes on demand"
---

At [work](https://meta.com) several years ago I received what at the time I
thought was a pretty niche and one-off request. A team in the containerisation
space was testing container teardown robustness, and wanted to make sure that
their software was robust to D state processes holding things up. I gave them
some ideas, they implemented it, and that was that.

Fast forward to today, and I think I must have seen this request at least four
or five times in the years since. Just as three examples that are
straightforward enough, I can think of:

1. The aforementioned container teardown case;
2. A team building system monitoring tooling that wanted D state processes for
   their integration tests;
3. Testing for the kernel team's diagnostics tool, which as part of its
   functions gathers kernel stacks of D state tasks.

So while this may still be a highly specialised request, there's clearly a
noticeable void in readily accessible knowledge on the subject. Hopefully this
article can improve that somewhat :-)

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

int main(void) {
{
    pid_t pid = vfork();
    if (pid == 0) {
        pause();
        _exit(0);
    } else if (pid < 0) {
        return 1;
    }
    return 0;
}
{% endhighlight %}

This will then reliably enter D state until a signal is sent:

{% highlight bash %}
% cc -o dstate dstate.c
% ./dstate & { sleep 0.1; ps -o pid,state,cmd -p "$!"; }
[1] 780629
    PID S CMD
 780629 D ./dstate
% kill "$!"
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

void __attribute__((noinline)) run_child(void)
{
    char input[sizeof(EXIT_STRING)];

    while (1) {
        if (fgets(input, sizeof(input), stdin) == NULL) {
            break;
        }
        if (strcmp(input, EXIT_STRING) == 0) {
            break;
        }
        if (strlen(input) == sizeof(input) - 1 &&
            input[strlen(input) - 1] != '\n') {
            /* Partial line read, clear it */
            int c;
            while ((c = getchar()) != '\n' && c != EOF);
        }
    }

    _exit(0);
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
    } else if (pid < 0) {
        return 1;
    }

    return 0;
}
{% endhighlight %}

And an example of its use:

{% highlight bash %}
% ./dstate
^C^C^C^C^C^C
EXIT
%
{% endhighlight %}

# Wait, that's illegal

Here's what POSIX [has to say about
vfork](https://pubs.opengroup.org/onlinepubs/009696799/functions/vfork.html).

> The vfork() function shall be equivalent to fork(), except that the behavior
> is undefined if the process created by vfork() either modifies any data other
> than a variable of type pid_t used to store the return value from vfork(), or
> returns from the function in which vfork() was called, or calls any other
> function before successfully calling _exit() or one of the exec family of
> functions.

It makes sense that access to the parent's memory (and thus doing basically
anything other than `exec` (which replaces the process entirely) or `_exit`
(which is really just a plain syscall) is not POSIX-legal in the child forked
by vfork because the parent cannot reasonably have the stack mutated under it
without its knowledge. But wait, didn't we just call a function?

The good news it that in reality (or at least for some version of reality on
Linux with any real libc), things are not that dire. CPython, for example,
which is used and tested for with more diversity than the vast majority of
software in use today, uses it in much the same way. In their case, it's used
as part of a vastly more complex process of forking children which is
also _guaranteed_ to push to stack by calling child functions (see
[here](https://github.com/python/cpython/blob/v3.12.1/Modules/_posixsubprocess.c#L812-L823)
and
[here](https://github.com/python/cpython/blob/v3.12.1/Modules/_posixsubprocess.c#L553-L571)).
I think it would be safe to say that, despite some POSIX book banging and
semantics discussion, the world has not collapsed yet as a result.

So why is this okay in reality? Well, when the parent process continues its
operation, additional stack data is simply going to end up in the unallocated
portion of the stack. The paused parent's stack pointer register is still
independent, even with `vfork`, so things just continue about their merry way
regardless of standards ire.

## Other approaches

There are a few other "controllable" (i.e. you can enter and exit D state on
demand) ways to do this. Here are some of them I've seen people suggest over
the years with some assessments:

1. **fsfreeze**: If you really need a process in a disk I/O related D state,
   this is how I would go about it. In its simplest form, all you need to do is
   `mkfs` a supported filesystem in a file, mount it to a loop device, call
   `fsfreeze -f` on the filesystem, and then try to do some I/O. This approach
   is highly reliable and can be easily activated and deactivated, but the
   setup involved is significantly more burdensome than the `vfork` option,
   which is mostly standalone. This also requires elevated privileges, whereas
   the `vfork` approach does not.
2. **Dropping NFS traffic**: It seems this is the tool that a lot of people
   reach for, maybe because it's so reliable at producing D states during
   normal operation ;-) However, this requires quite a bit of setup, and it's
   not very reliable since it depends a lot on client and server configuration
   what will really happen and for how long.
3. **set_current_state(TASK_UNINTERRUPTIBLE)**: Of course, one can also just
   write a kernel module to do whatever one wants. This is easily the most
   complicated option to maintain long term, especially in a testing pipeline.
   It requires elevated privileges, and you have the extra bonus of potentially
   screwing up scheduling entirely depending on how you go about it.

All in all, the simplicity and flexibility of the vfork approach make it ideal
for most use cases. It doesn't require complex setup, is easily controllable
and reliable, can easily be modified to be suitable for different testing
conditions, and it's generally fairly self contained.
