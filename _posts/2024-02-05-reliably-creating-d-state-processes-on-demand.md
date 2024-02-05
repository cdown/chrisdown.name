---
layout: post
title: "Creating controllable D state (uninterruptible sleep) processes"
description: "tl;dr: using vfork(), one can create a process in a D state that is _not_ immune to signal interruption. But wait, how can any D state process be \"not immune to signal interruption\"?"
---

tl;dr:

- Using `vfork()`, one can create a process in a D state that is _not_ immune to
  signal interruption.
- Using `fsfreeze`, one can create a process in a D state that is immune to
  signal interruption.

But wait, how can any D state process be "not immune to signal interruption"?
Isn't the whole point of D state processes that they are uninterruptible? If
you are wondering this, read on and you will likely find out some new things
about how Linux works internally :-)

---

Imagine you're a system administrator responsible for maintaining containers
across production. One day, you encounter a problem: while trying to roll out a
new version of a container -- and thus first have to stop the old container --
the old container will not stop because some of the processes in it are stuck
and unresponsive.

These kinds of processes are typically represented with the code "D" in `ps`,
`top`, and other similar tools. D state (typically written out in full as
"uninterruptible sleep") is a process state where a process is forced to sleep
and cannot be woken up in userspace. This can be necessary in some cases when
it's unsafe for the process to continue execution, and we'll go over some of
the cases where it is needed in a moment.

As a real world example, at [work](https://meta.com) several years ago, one of
the teams that works on our internal containerisation system,
[Twine](https://research.facebook.com/publications/twine-a-unified-cluster-management-system-for-shared-infrastructure/),
was checking that their software could properly destroy containers with D state
processes present, and needed to produce them on demand as part of their
integration tests. I gave them some advice, it was implemented, and I thought
that's probably the last I'd ever hear of it.

Fast forward to today, and I think I must have seen this request at least four
or five times in the years since. Just as one recent additional example, I
recently got asked about this as part of testing for the Meta kernel team's
diagnostics tool, which as one of its functions gathers kernel stack traces of
D state tasks in order to work out what they are waiting for, in case it's a
kernel issue that bears investigating further.

So while this may still be a relatively specialised request, there's clearly a
noticeable void in readily accessible knowledge on the subject given the number
of times that this has now come up. I will -- of course -- simply answer the
question of how to go about this, but for those who are interested, we will
also discuss some interesting Linux arcana, some of the dangers of sharing
virtual memory space, and some things you may well not know about D state
process internals along the way. :-)

## Why would anyone want to test this?

The most common way that processes enter D state is while doing DMA transfers
and other hardware interactions, and while waiting for certain kinds of kernel
synchronisation primitives. DMA, for example, allows hardware subsystems to
access the main system memory for reading/writing independently of the CPU,
which is essential for efficient handling of large volumes of data. Because
this access is gated as part of the process context itself, programs generally
must not be interrupted in the midst of such operations because DMA transfers
are not typically designed to accommodate or recover from partial or
interrupted reads or writes.

<div class="sidenote sidenote-right">
On modern kernels, such processes can have their memory freed from the system
perspective using <code><a
href="https://lwn.net/Articles/864184/">process_mrelease()</a></code> when they
are scheduled to be killed before the next userspace instruction, but this
still doesn't change the fact that memory in use for DMA can't be used until
the process fully terminates. This is because the physical pages are still
pinned by the device for the lifetime of the DMA request.
</div>

For example, when a program reads or writes from your storage, what is
typically really happening is that the storage device's hardware is directly
accessing the system's main memory to transfer data. This is achieved through
DMA, which bypasses the CPU. Instead of the CPU reading data into memory and
then writing it to the disk (or vice versa), DMA allows the storage device to read
or write directly to or from the memory. This direct pathway is vastly more
efficient than doing this through the CPU, but it also means that we must guard
the process from interruption in order to keep this memory pinned for hardware
use during the transaction.

These states can become a problem for things like init systems or
containerisation platforms, where the unwavering persistence of these stubborn
processes may block things like tearing down a container, a user session, or
the entire system on shutdown. As such, all systems that implement teardown for
groups of processes must implement measures to deal such issues.

Here's a real example of how that can manifest in a production environment with
a container engine.

<script src="/js/mermaid.min.js?{{ site.data["gitrev"] }}"></script>
<script>
mermaid.initialize({
  theme: 'default',
  themeVariables: {
    fontFamily: '"Open Sans", sans-serif',
    clusterBkg: '#fff5ad',
    clusterBorder: '#aaaa33',
    edgeLabelBackground: '#fff5ad',
  }
});
</script>
<div class="sidenote sidenote-right">
<pre class="mermaid">
sequenceDiagram
    participant CE as Container Engine
    participant P as Process
    participant K as Kernel

    P->>K: DMA
    K->>P: D state

    Note over CE,K: The hardware takes a long time to finish or has<br>a bug, so we are stuck in D state indefinitely, and<br>cannot be signalled to terminate. Meanwhile...

    Note over CE: The container<br>engine is<br>told to shut<br>down the container.
    CE->>P: TERM signal
    P--xCE: No reaction

    Note over CE: After a grace period,<br>the container engine<br>notices the process is<br>still running and uses<br>more forceful methods.

    CE->>P: KILL signal
    P--xCE: No reaction

    Note over CE: The container engine is now<br>blocked shutting down,<br> waiting for processes<br>to terminate.
</pre>

<p>In reality, sending signals like <code>SIGTERM</code> and
<code>SIGKILL</code> goes through the kernel, but that's omitted in this
diagram for brevity. <span class="non-sidenote-only">Here's a more textual
description of the same diagram.</span></p>
</div>

Let's suppose that there is a job in production that interfaces with hardware.
This hardware may -- legitimately or less legitimately -- take an indefinite
time to do DMA transfers. Once a DMA transfer has started, it can't be stopped
until the hardware says it's done, and in order to ensure that, the process
enters D state.

Imagine that while we are stuck for some indefinite period in D state, the
scheduler that decides which jobs should be on which machines (like Kubernetes'
scheduler, for example) decides that this container should be evicted from this
machine. Normally that's pretty straightforward: ask the container to shut down
itself, and if it takes too long, send it `SIGKILL`. After that we can do some
cleanup for any state we might have had, and we're more or less done.

D states complicate this quite a bit, because they cannot typically be
interrupted. In order to preserve system integrity, they typically don't even
respond to `SIGKILL`, the most brutal of signals. This can cause problems: now
we still have a process running in this container, and any forward progress is
blocked.

In systemd, the way we handle D state processes remaining after the stop
timeout has expired is by marking the unit as failed:

    % systemctl --user status foo.service
    Active: failed (Result: timeout)

    [...]

    State 'stop-sigterm' timed out. Killing.
    Killing process 1282704 with signal SIGKILL.
    Processes still around after final SIGKILL. Entering failed mode.
    Failed with result 'timeout'.

This is a fairly passive approach: it's still up to the user to decide what
they should do with a "failed" unit, and we don't directly take any action to
try to rectify the situation.

Keeping the unit around keeps all the metadata around in one place (like which
pids are causing the hold up), which is definitely a positive: it helps not
only in debugging, but also helps container engines using systemd units to
decide whether it's still safe to start a new service or not given the
situation.

Other more active interventions include (but are not limited to):

1. **Reboot the machine**: This is dangerous and is generally not suitable for
   a generic init system like systemd. Doing this must be decided by the user
   directly (or a service they have written). Rebooting is very slow and
   heavyweight, may lose state, reduces fleetwide capacity, and is very
   cumbersome if the issue happens widely. This method may also hide actual
   driver or kernel bugs, and definitely needs to be rate limited at the fleet
   level in terms of number of reboots a second or minute.
2. **Consider the D state processes as no longer part of the failed unit**: In
   this case, resources are still taken by the process in D state, and are now
   separately accounted for (and potentially are made more difficult to reason
   about). On some rollouts that may actively hide issues, or introduce hard to
   debug new ones. It may also not be safe to start the new container if the
   old processes are still around because of reasons like resource usage or
   synchronisation issues.

The right course of action here depends on what's decided by those making the
container engine, but the exact choice is not really the point. The more
important bit is that once you've made your choice on how to handle this, the
next step is to produce a test to make sure that the behaviour you've settled
on for this scenario remains stable across versions and configurations, and
that requires being able to create and destroy D state processes for testing on
demand. Linux actively tries to avoid processes entering uninterruptible sleep
whenever possible, as these processes can be particularly troublesome to deal
with. For this reason it's not immediately obvious how to create a process
which can reliably enter and exit uninterruptible sleep on demand for testing.

## D states outside of I/O context

While D states might immediately bring to mind disk activity, we actually use
them for all sorts of things in the kernel. As a general rule, the kernel uses
D states to block processes in any situation where it's unsafe to allow the
process to proceed further for the time being.

Enter `vfork()`. `vfork()` is a specialised system call primarily designed to
be used as part of the process of creating new processes. Unlike the more
widely known `fork()`, which typically uses copy-on-write and thus must at the
very least create new virtual mappings to the physical pages in question,
`vfork()` allows the child process to directly share the parent's virtual
address space temporarily without any copying whatsoever. This is much cheaper
if you are just going to immediately clobber the child with a new process image
using `exec`, as in the case of process creation, where copying all the pages
would be needlessly wasteful.

But how can that be safe? Surely two processes sharing the same virtual memory
address space is a recipe for disaster? Well, `vfork()` suspends the parent
application for the period that the child is using its address space, and it
suspends it in D state until the child either dies or calls an `exec` function
to replace the process image. As with `fork()`, `vfork()`s return code is 0
when running in the child, and the PID of the child when running in the parent,
which we can use to determine which we are in when resuming execution.

Once spawned, the child can see and modify everything in the parent's address
space. Likewise, once the parent wakes up again, it too will see all and any
changes performed in the child. The only safety is that both processes can't
run at the same time, but other than that, pretty much all bets are off.

Choreographing a long-lived D state process with `vfork()` works something like
the following:

<div class="sidenote sidenote-right">
<pre class="mermaid">
{% raw %}
graph TD
    start[Program started] --> vfork
    subgraph parent[" "]
        vfork["vfork()"]
        d_start{{Enter<br>D state}}
        d_exit{{Exit<br>D state}}
        return[return 0]
        vfork --> d_start
        d_start -. Wait for<br>child to<br>finish .- d_exit
        d_exit --> return
    end

    subgraph child[" "]
        pause["pause()"]
        exit["Kernel<br>kills<br>child"]
        vfork -- Uncopied<br>clone<br>created --> pause
        pause -. Wait for<br>terminal<br>signal .- exit
        exit --> d_exit
    end

    send_sig["Signal sent<br>to child"] --> exit

    exit --> clone_exit["vforked child<br>exits without cleanup"]
    return --> prg_exit["Program exited"]
{% endraw %}
</pre>

<p>Dotted lines represent transitions that depend on some external action.</p>

<p>Also note that we'll never actually reach <code>_exit()</code> in the child
because the kernel will tear down the child the moment it sees that there's no
userspace signal handler for the terminal signal, but the effects are basically
the same.</p>

<div class="non-sidenote-only"><p>Here's what the relevant code looks
like:</p></div>
</div>

{% highlight c %}
#include <unistd.h>

__attribute__((noinline)) static void run_child(void)
{
    pause();
    _exit(0);
}

int main(void)
{
    pid_t pid = vfork();

    if (pid == 0) {
        run_child();
    } else if (pid < 0) {
        return 1;
    }

    return 0;
}
{% endhighlight %}

This will then reliably enter D state until a terminal signal is sent to the
child:

{% highlight bash %}
% cc -o dstate dstate.c
% ./dstate & sleep 0.1; ps -o pid,state,cmd -p "$!"
[1] 780629
    PID S CMD
 780629 D ./dstate
% pkill -P "$!"
[1]  + done       ./dstate
{% endhighlight %}

`$!` is the process ID of the last background pipeline, which in this case is
`./dstate &`. `pkill -P` kills its child.

`__attribute__((noinline))` is a good idea in order to make sure that
the stack space used in the child is separate from the stack space used by the
parent. By preventing inlining, we ensure that the function creates a distinct
stack frame on entry, and in the context of the `vfork()`ed child, this means
that any stack manipulation occurs neatly in a separate frame, and not in the
parent's stack frame. Without it, the compiler may perform optimisations that
result in interleaved data between the parent and child, which could result in
stack corruption when the parent resumes. We'll go a little more into how
exactly that works and why it's necessary very shortly.

The goal here is to keep the child alive for as long as we want to have our
parent in D state. `pause()` here waits until a terminal signal is sent, and
can be modified to suit whatever needs you happen to have. For example, if your
test involves sending signals and so you want to ignore those, you can instead
wait for the text "EXIT" on stdin:

{% highlight c %}
#include <assert.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#define EXIT_STRING "EXIT\n"

__attribute__((noinline)) static void run_child(void)
{
    char input[sizeof(EXIT_STRING)];

    while (1) {
        if (fgets(input, sizeof(input), stdin) == NULL) {
            if (ferror(stdin)) {
                fprintf(stderr,
                        "Error reading stdin in child\n");
            }
            if (feof(stdin)) {
                fprintf(stderr,
                        "EOF waiting for exit string\n");
            }
            break;
        }
        if (strcmp(input, EXIT_STRING) == 0) {
            break;
        }
        if (strlen(input) == sizeof(input) - 1 &&
            input[strlen(input) - 1] != '\n') {
            /* Partial line read, clear it */
            int c;
            while ((c = getchar()) != '\n' && c != EOF)
                ;
        }
    }

    _exit(0);
}

int main(void)
{
    pid_t pid;
    sigset_t set;

    sigfillset(&set);
    assert(sigprocmask(SIG_BLOCK, &set, NULL) == 0);

    pid = vfork();

    if (pid == 0) {
        run_child();
    } else if (pid < 0) {
        return 1;
    }

    return 0;
}
{% endhighlight %}

Here's an example of its use, showing that it can't simply be terminated by
Ctrl-C:

{% highlight bash %}
% ./dstate
^C^C^C^C^C^C
EXIT
%
{% endhighlight %}

## Wait, that's illegal

I'm sure that some people reading the code I provided above are wondering
whether it's legal or not, given the fact that we are sharing the parent's
memory space. Here's what the POSIX spec, which Linux generally tries to
somewhat adhere to, [has to say about
`vfork()`](https://pubs.opengroup.org/onlinepubs/009696799/functions/vfork.html):

> The `vfork()` function shall be equivalent to `fork()`, except that the
> behavior is undefined if the process created by `vfork()` either modifies any
> data other than a variable of type `pid_t` used to store the return value
> from `vfork()`, or returns from the function in which `vfork()` was called,
> or calls any other function before successfully calling `_exit()` or one of
> the `exec` family of functions.

It makes sense that access to the parent's memory (and thus doing basically
anything other than `exec` (which replaces the process entirely) or `_exit()`
(which is really just a syscall) is not POSIX-legal in the child forked by
`vfork()`, because the parent cannot reasonably have its internal state mutated
under it without its knowledge. But wait, didn't we just call a function?
That's certainly going to make use of the stack, which will later be visible to
the parent, right?

The good news it that in reality (or at least for some version of reality on
Linux with any real libc), things are not that dire. Just as one example,
CPython -- which is used and tested with far more diversity than the vast
majority of software in use today -- uses it in [much the same
way](https://github.com/python/cpython/blob/v3.12.1/Modules/_posixsubprocess.c#L773-L782):

{% highlight c %}
Py_NO_INLINE static pid_t do_fork_exec(/* ... */)
{
    pid_t pid;
    PyThreadState *vfork_tstate_save;

    /* ... */

    vfork_tstate_save = PyEval_SaveThread();
    pid = vfork();
    if (pid != 0) {
        /* Not in the child process, reacquire the GIL. */
        PyEval_RestoreThread(vfork_tstate_save);
        return pid;
    }

    /* Child process. */

    if (preexec_fn != Py_None) {
        PyOS_AfterFork_Child();
    }

    child_exec(exec_array, argv, envp, cwd,
               /* ... */);
    _exit(255);
    return 0;
}
{% endhighlight %}

As you can see, in their case, it's used as part of a vastly more complex
process of forking children which is also _guaranteed_ to push to stack by
calling child functions. I think it would be safe to say that, despite some
POSIX book banging and semantics discussion, the world has not collapsed into a
fiery pit yet as a result.

So why is this okay enough to make it into codebases like CPython's? Well,
let's come back to an elided form of our code from earlier:

{% highlight c %}
__attribute__((noinline)) static void run_child(void)
{
    char input[sizeof(EXIT_STRING)];
    int c;

    /* ... */

    _exit(0);
}

int main(void)
{
    pid_t pid;
    sigset_t set;

    /* ... */

    pid = vfork();

    if (pid == 0) {
        run_child();
    } else if (pid < 0) {
        return 1;
    }

    return 0;
}
{% endhighlight %}

<div class="sidenote sidenote-right">
<p>Let's take a look at how this might look on an x86_64 stack just before
<code>_exit(0)</code>:</p>

<table>
<thead>
  <tr>
    <th>Function</th>
    <th>Stack</th>
    <th>Parent register</th>
    <th>Child register</th>
  </tr>
</thead>
<tbody>
  <tr>
    <td class=center colspan=4>[stuff before <code>main()</code>]</td>
  </tr>
  <tr>
    <td rowspan=4><code>main()</code></td>
    <td>Return address</td>
    <td></td>
    <td></td>
  </tr>
  <tr>
    <td>Saved frame pointer</td>
    <td>Frame pointer</td>
    <td></td>
  </tr>
  <tr>
    <td><code>pid_t pid</code></td>
    <td></td>
    <td></td>
  </tr>
  <tr>
    <td><code>sigset_t set</code></td>
    <td></td>
    <td></td>
  </tr>
  <tr>
    <td rowspan=4><code>run_child()</code></td>
    <td>Return address</td>
    <td>Stack pointer</td>
    <td></td>
  </tr>
  <tr>
    <td>Saved frame pointer</td>
    <td></td>
    <td>Frame pointer</td>
  </tr>
  <tr>
    <td><code>char input[]</code></td>
    <td></td>
    <td></td>
  </tr>
  <tr>
    <td><code>int c</code></td>
    <td></td>
    <td></td>
  </tr>
  <tr>
    <td class=center colspan=2>[unallocated]</td>
    <td></td>
    <td>Stack pointer</td>
  </tr>
</tbody>
</table>

<p>In reality:</p>

<ol>
<li>The compiler may choose to use registers instead of the stack for storing
some of the local variables due to their small size, and</li>
<li>The compiler may omit the frame pointer entirely and just rely on using the
stack pointer</li>
</ol>

<p>...but the general principle and effects are nevertheless the same.</p>
</div>

When the parent process continues its operation, additional stack data is
simply going to end up in what is -- from the parent's perspective, at least --
the unallocated portion of the stack. It doesn't know that its stack pointer is
pointing to the return address for `run_child()`, from its perspective,
whatever is at that memory is semantically meaningless.

This happens because even though `vfork()` shares the address space, it _does
not_ share registers between the child and parent. Importantly, this means that
the parent's stack pointer and frame pointer registers are still independent
from those in the child. This independence extends to all registers, including
the instruction pointer register (which stores the next instruction to
execute), and this is how the parent resumes at `vfork()` instead of trying to
continue from what the child has already done when it wakes up.

While there might be some more stuff on the stack, the parent doesn't care:
from its perspective what's contained in those addresses is meaningless and can
be ignored or overwritten at will, and as such things just continue about their
merry way.

All in all, despite standards ire, the whole thing is pretty safe.

## Why do we block signals in both the parent and child?

In the example above one might typically visualise our intention as being to
satisfy some condition in the child (like writing "EXIT" in our second example)
in order to unblock the parent. However, you may also notice that in this code
example, signals are blocked not only in the child, but also the parent. But
surely that's not necessary since the parent is in D state anyway, right? Well,
let's try it without the signals blocked in the parent:

{% highlight bash %}
% ./dstate & sleep 0.1; ps -o pid,state,cmd -p "$!"; kill "$!"
[1] 866239
    PID S CMD
 866239 D ./dstate
[1]  + terminated  ./dstate
{% endhighlight %}

Wait, what? How come we were able to terminate a D state process?

My experience is that most system administrators and Linux users are not aware
of the fact that a D state process doesn't actually have to be uninterruptible.
All a D state process represents is a process which cannot execute any more
userspace instructions, but blocking all signals is only one interpretation of
how to achieve that, and it's not necessary in all circumstances.

To see what I mean, let's look at the kernel source to see how `vfork()` is
implemented. Depending on your libc and version, the `vfork()` that you call from
your application is likely either a thin wrapper around the `clone()` or `vfork()`
syscalls. They do the same thing behind the scenes -- [`vfork()` calls into the
`clone()` code path
`kernel_clone()`](https://github.com/torvalds/linux/blob/0dd3ee31125508cd67f7e7172247f05b7fd1753a/kernel/fork.c#L3005-L3013):

{% highlight c %}
SYSCALL_DEFINE0(vfork)
{
    struct kernel_clone_args args = {
        .flags       = CLONE_VFORK | CLONE_VM,
        .exit_signal = SIGCHLD,
    };

    return kernel_clone(&args);
}
{% endhighlight %}

This is the definition of the `vfork()` syscall, with no ("0") arguments, hence
`SYSCALL_DEFINE0(vfork)`. `kernel_clone()` is the kernel path that handles
`clone()`, which itself is a generic syscall for creating new processes.

Setting `kernel_clone()`'s flags to `CLONE_VFORK` and `CLONE_VM` requests the
traditional `vfork()` behaviour: share the virtual memory space, and suspend
the parent process until the child has completed. That is, the effects of
running `vfork()` or `clone()` with the appropriate flags in a program are
effectively the same.

In `kernel_clone()`, [we see the following
code](https://github.com/torvalds/linux/blob/0dd3ee31125508cd67f7e7172247f05b7fd1753a/kernel/fork.c#L2944-L2947):

{% highlight c %}
if (clone_flags & CLONE_VFORK) {
    if (!wait_for_vfork_done(p, &vfork))
        ptrace_event_pid(PTRACE_EVENT_VFORK_DONE, pid);
}
{% endhighlight %}

Okay, so [what does `wait_for_vfork_done()`
do](https://github.com/torvalds/linux/blob/0dd3ee31125508cd67f7e7172247f05b7fd1753a/kernel/fork.c#L1588-L1606)?

{% highlight c %}
static int wait_for_vfork_done(struct task_struct *child,
                               struct completion *vfork)
{
    unsigned int state = TASK_UNINTERRUPTIBLE |
                         TASK_KILLABLE | TASK_FREEZABLE;
    int killed;

    /* ... */

    killed = wait_for_completion_state(vfork, state);

    /* ... */

    return killed;
}
{% endhighlight c %}

`TASK_KILLABLE` is a state that [Matthew][] introduced in 2.6.25. It was
created because, while in some cases we do actually need to shield the process
from any signal interaction at all, in some cases it's fine as long as we know
the process will terminate with no more userspace instructions executed. For
example, in this `vfork()` case, we have to block to avoid both tasks accessing the
same address space, but there's no reason for us to continue to wait if the
next thing we're going to do is simply terminate -- it's a waste of time and of
a process.

`TASK_KILLABLE` was introduced to solve these kinds of cases. Instead of being
fully uninterruptible, when we receive a signal we check if the signal is fatal
(that is, it's either a non-trappable fatal signal, or the program has no
userspace handler for a signal with a default terminal disposition), and if it
is, we terminate the process without allowing it to execute any more userspace
instructions.

We use `TASK_KILLABLE` pretty widely in the kernel nowadays where possible:

{% highlight bash %}
linux % git grep -ihc _killable | paste -sd+ | bc
539
{% endhighlight %}

As such, you may well find that some of the D states that processes enter on
your system actually are terminable after all.

## How can I survive SIGKILL, then?

While the above approach is nice and self contained and serves most use cases
for testing, its major downside is that it doesn't survive a `SIGKILL`, as
`SIGKILL` is always a deadly signal, and cannot be caught in userspace. In
order to survive that, we need to find a way from userspace to enter a state
which sets `TASK_UNINTERRUPTIBLE` without `TASK_KILLABLE`.

Those of you who have worked in the storage space may also know about disk and
filesystem snapshots. Linux has, over time, added support for these kinds of
things through
[LVM](https://en.wikipedia.org/wiki/Logical_Volume_Manager_%28Linux%29) and
other mechanisms. LVM in particular adds more sophisticated management of disk
space and filesystems on top of existing Unix paradigms, like the capability to
resize filesystems, manage multiple disks as one, and most importantly for this
discussion, they introduced the ability to do disk snapshotting, where you take
a snapshot of a filesystem at a particular moment in time.

There are also other mechanisms which make use of some of the LVM
infrastructure in order to do things like snapshots in an external context. One
of those mechanisms that we can leverage here is `fsfreeze`.

From [`man 8 fsfreeze`](https://man.archlinux.org/man/fsfreeze.8):

> `fsfreeze` suspends and resumes access to a filesystem. `fsfreeze` halts new
> access to the filesystem and creates a stable image on disk. `fsfreeze` is
> intended to be used with hardware RAID devices that support the creation of
> snapshots.

This freeze is implemented by (among other things) indefinitely taking
exclusive write access over the filesystem's
[superblock](https://unix.stackexchange.com/a/4403/10762). The filesystem
superblock contains much of the high level, mission critical information for
the filesystem, and taking exclusive write access over it is tantamount to
denying any modification to the filesystem.

[This is implemented in
`freeze_super()`](https://github.com/torvalds/linux/blob/0dd3ee31125508cd67f7e7172247f05b7fd1753a/fs/super.c#L1961),
which implements its freezing via an array of per-CPU read-write semaphores
within the superblock structure:

{% highlight c %}
static void sb_wait_write(struct super_block *sb, int level)
{
    percpu_down_write(sb->s_writers.rw_sem + level - 1);
}

int freeze_super(struct super_block *sb,
                 enum freeze_holder who)
{
    /* ... */

    sb_wait_write(sb, SB_FREEZE_WRITE);
    sb_wait_write(sb, SB_FREEZE_PAGEFAULT);
    sb_wait_write(sb, SB_FREEZE_FS);

    /* ... */
}
{% endhighlight %}

Importantly, we need to acquire the writer side of one of these semaphores when
modifying files or directories in order to safely queue changes to the
superblock. For our needs, per-CPU read-write locks in the kernel have a useful
property: when the lock takes the slow path (i.e. the lock is held in such a
way that we cannot acquire it right now), it puts the process requesting it in
`TASK_UNINTERRUPTIBLE` without `TASK_KILLABLE`. This means that our process
will survive a `SIGKILL` while in D state, and the only way out is to unfreeze
the filesystem.

For example, here is the kernel stack we get trapped in trying to acquire the
previously writer locked read-write semaphore when trying to do a `mkdir` on a
frozen filesystem:

    % cat /proc/21135/stack
    [<0>] percpu_rwsem_wait+0x116/0x140
    [<0>] mnt_want_write+0x8f/0xc0
    [<0>] filename_create+0x7c/0x1b0
    [<0>] do_mkdirat+0x5f/0x180
    [<0>] __x64_sys_mkdir+0x49/0x70
    [<0>] do_syscall_64+0x61/0xe0
    [<0>] entry_SYSCALL_64_after_hwframe+0x6e/0x76

No amount of killing will unblock this for now -- the filesystem must be
unfrozen to make forward progress. As you can see, it still exists even after a
`kill -9`:

    % kill -9 21135
    % ps -o pid,state,cmd -p 21135
      PID S CMD
    21135 D mkdir /tmp/tmp.dBgYmOjJOO/dir

To understand why this is, it helps to know that on Linux, signal delivery is
not instantaneous and is instead handled by what's called a "signal queue". D
state processes without <code>TASK_KILLABLE</code> receive pending signals when
they transition out of D state, so this `SIGKILL` will still be properly
delivered, but only when the filesystem that `mkdir` is acting upon is
unfrozen. You can see these signals in `SigPnd` (signals pending) in
`/proc/pid/status`:

    % grep SigPnd: /proc/21135/status
    SigPnd:	0000000000000100

{% sidenote %}
`SigPnd`, `SigBlk`, and other similar fields are bitmaps of signals, encoded in
hexadecimal. Here's an example program which can decode them:

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

It's important to understand that while in the D state, these processes are not
"ignoring" the signals -- rather, the kernel defers signal handling until the
process is in a safe state to receive them. This is a mechanism to ensure
system stability, especially during sensitive operations like DMA, where
interrupting or prematurely terminating a process could lead to unsound
behaviour.

Here's how we can reproduce this reliably as a script. This example is in bash,
but of course, you can more or less write this in any language that suits your
needs.

{% highlight bash %}
#!/bin/bash -e

src=$(mktemp)
dest=$(mktemp -d)

if (( EUID != 0 )); then
    echo 'You need to be root.' >&2
    exit 1
fi

# fsfreeze needs a supported filesystem. ext4 is
# one, but you can use others, see FILESYSTEM
# SUPPORT in `man 8 fsfreeze'.
fallocate -l 8M -- "$src"
mkfs.ext4 -q -- "$src"

mount -o loop -- "$src" "$dest"

fsfreeze -f -- "$dest"

unfreeze() {
    fsfreeze -u -- "$dest"
    umount -- "$dest"
    rm "$src"
}
trap unfreeze EXIT

mkdir "$dest"/dir &
d_pid=$!

i=0
while true; do
    read -r _ _ state _ < /proc/"$d_pid"/stat
    if [[ $state == D ]]; then
        break
    fi
    if (( ++i % 1000 == 0 )); then
        printf 'Waiting for %d to enter D state...\n' \
            "$d_pid" >&2
    fi
done

printf 'PID %d is now in D state. ' "$d_pid"
printf 'Press <Enter> to unfreeze and clean up.'
read
{% endhighlight %}

Run this script as root, and you should get a process which is now in D state,
with the PID for that process in the output. Press Enter to tear down the
filesystem and take the process out of D state.

    % sudo ./dstate-fsfreeze
    PID 33088 is now in D state. Press <Enter> to unfreeze and clean up.

While slightly less self-contained than the `vfork()` method, since it requires
creating a filesystem and having elevated privileges, this method is the way
you likely want to go if you need a non-`TASK_KILLABLE` D state.

## Other approaches

There are a few other "controllable" (i.e. you can enter and exit D state on
demand) ways to do this. Here are some of them I've seen people suggest over
the years with some assessments:

1. **Dropping NFS traffic**: It seems this is the tool that a lot of people
   reach for, maybe because it's so reliable at producing D states during
   normal operation ;-) The basic premise involves running an NFS client and
   server on a single host, and then using iptables or BPF to drop packets on
   demand. However, this requires quite a bit of setup, and it's not very
   reliable since what exactly will happen and for how long depends a lot on
   client and server configuration, and some amount of blind luck.
2. **Writing a kernel module**: Of course, one can also just write a kernel
   module to do whatever one wants. This is easily the most complicated option
   to maintain long term, especially in a testing pipeline. It requires
   elevated privileges, and you have the extra bonus of potentially screwing up
   scheduling entirely depending on how you go about it.

All in all, the simplicity and flexibility of the `vfork()` and `fsfreeze`
approaches make them ideal for most use cases. They don't require complex
setup, are controllable and reliable, and can easily be modified to be suitable
for different testing conditions.

Many thanks to [Johannes](https://github.com/hnaz), [Matthew][],
[Sam](https://samwho.dev/), [Tejun](https://github.com/htejun),
[Yonghong](https://github.com/yonghong-song), [Javier](https://hondu.co/), and
my wife [Lin](https://www.linkedin.com/in/linzhao1/) for reviewing this post
and providing suggestions.

[Matthew]: https://kernelnewbies.org/MatthewWilcox
