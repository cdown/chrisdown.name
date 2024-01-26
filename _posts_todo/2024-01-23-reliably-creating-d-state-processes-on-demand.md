---
layout: post
title: "Creating controllable D state (uninterruptible sleep) processes on demand"
---

tl;dr:

- Use `vfork` for a D state that can be controlled via signals.
- Use `fsfreeze` for a D state which cannot be controlled via signals.

But wait, how can any D state process be controlled by signals anyway? Isn't
the whole point that they are uninterruptible? If you are wondering this, read
on and you will likely find out some new things about how Linux works
internally :-)

---

At [work](https://meta.com) several years ago I received what at the time I
thought was a pretty niche and one-off request. A team in the containerisation
space was testing container teardown robustness, and wanted to make sure that
their software was robust to D state processes holding things up. I gave them
some ideas, they implemented it, and that was that.

The D (typically written out as "uninterruptible sleep") state is a process
state where a process is sleeping and cannot be woken up in userspace. This can
become a problem for things like init systems or containerisation platforms
where the unwavering persistence of such processes must be planned for and have
strategies in place in order to avoid them blocking forward progress. These
processes are typically thought about as being the equivalent of an immovable
object: a process where no signal and no input is likely to result in any
forward progress, at least for the timebeing.

Fast forward to today, and I think I must have seen this request at least four
or five times in the years since. As three examples from the top of my head:

1. The aforementioned container teardown case;
2. A team building system monitoring tooling that wanted D state processes for
   their integration tests;
3. Testing for the kernel team's diagnostics tool, which as part of its
   functions gathers kernel stacks of D state tasks.

So while this may still be a highly specialised request, there's clearly a
noticeable void in readily accessible knowledge on the subject.

For those who are interested, we will also discuss some interesting Linux
arcana, some of the dangers of sharing virtual memory space, and some things
you may well not know about D state process internals. :-)

## Why would anyone want to test this?

One example of where this is used is in DMA transfers and the like. DMA allows
hardware subsystems to access the main system memory for reading/writing
independently of the CPU, which is essential for efficient handling of large
volumes of data. Programs generally must not be interrupted in the midst of
such operations because DMA transfers are not typically designed to accommodate
or recover from partial or interrupted reads or writes.

These states can become a problem for things like init systems or
containerisation platforms where these stubborn processes may block things like
tearing down a container, a user session, or the entire system on shutdown, and
as such all systems like this must implement measures to deal with them.

Here's a tangible example of how that might manifest in a production
environment with a container engine.

There is a job in production that interfaces with hardware. This hardware may
-- legitimately or less legitimately -- take a long time to do DMA transfers.
Once a DMA transfer has started, it can't be stopped until the hardware says
it's done, and in order to ensure that, the process enters D state.

During this whole process, the scheduler that decides which jobs should be on
which machines (like Kubernetes' scheduler, for example) decides that this
container should be evicted from this machine. Normally that's pretty
straightforward: ask the container to shut down itself, and if it takes too
long, send it SIGKILL. After that we can do some cleanup for any state we might
have had, and we're more or less done.

D states complicate this. Because D states cannot typically be interrupted in
order to preserve system integrity, they typically don't even respond to
`SIGKILL`, the most brutal of signals. This can cause problems: now we still
have a process running from this container, and we want to tear it down right
now.

What the right action is here depends on the container engine, but the exact
choice is not really the point: once you've made your choice on how to handle
this, the next step is to produce a test to make sure that the behaviour you've
settled on for this scenario is stable across versions and configurations, and
that requires being able to create and destroy D state processes for testing on
demand, which is not something that it's immediately obvious how to do.

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
nowadays, which has more sensible semantics and is much more configurable. For
this case, though, we only need `vfork`'s behaviour, which is to suspend the
parent application in D state. Here is an example of how one might reliably
create a D state process with `vfork`:

{% highlight c %}
#include <unistd.h>

int main(void)
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

This will then reliably enter D state until a terminal signal is sent:

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

static void __attribute__((noinline)) run_child(void)
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

`__attribute__((noinline))` is generally a good idea in order to make sure that
the stack space used in the child is separate from the stack space used by the
parent, avoiding the compiler potentially doing optimisations that might result
in stack interleaving.

Here's an example of its use, showing that it can't simply be terminated by
Ctrl-C:

{% highlight bash %}
% ./dstate
^C^C^C^C^C^C
EXIT
%
{% endhighlight %}

## Why do we block signals in both the parent and child?

In the example above one might typically visualise our intention as being to
satisfy some condition in the child in order to unblock the parent. However,
you may also notice that in this code example, signals are blocked not only in
the child, but also the parent. But surely that's not necessary since the
parent is in D state anyway, right? Well, let's try it without the signals
blocked in the parent:

{% highlight bash %}
% ./dstate & { sleep 0.1; ps -o pid,state,cmd -p "$!"; kill "$!"; }
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

To see what I mean, let's look at the kernel source to see how `vfork` is
implemented. Depending on your libc and version, the `vfork` that you call from
your application is likely either a thin wrapper around the `clone` or `vfork`
syscalls. They do the same thing behind the scenes -- `vfork` calls into the
`clone` code path `kernel_clone`:

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

`CLONE_VFORK` is the `clone()` flag that specifies to suspend the parent
process until the child has completed. In `kernel_clone`, we see the following
code:

{% highlight c %}
if (clone_flags & CLONE_VFORK) {
    if (!wait_for_vfork_done(p, &vfork))
        ptrace_event_pid(PTRACE_EVENT_VFORK_DONE, pid);
}
{% endhighlight %}

Okay, so what does `wait_for_vfork_done` do?

{% highlight c %}
static int wait_for_vfork_done(struct task_struct *child,
                               struct completion *vfork)
{
    unsigned int state = TASK_UNINTERRUPTIBLE |
                         TASK_KILLABLE | TASK_FREEZABLE;
    int killed;

    cgroup_enter_frozen();
    killed = wait_for_completion_state(vfork, state);
    cgroup_leave_frozen(false);

    if (killed) {
        task_lock(child);
        child->vfork_done = NULL;
        task_unlock(child);
    }

    put_task_struct(child);
    return killed;
}
{% endhighlight c %}

`TASK_KILLABLE` is a state that
[Matthew][] introduced in 2.6.25. It was
created because, while in some cases we do actually need to shield the process
from any signal interaction at all, in some cases it's fine as long as we know
the process will terminate with no more userspace instructions executed. For
example, in this vfork case, we have to block to avoid both tasks accessing the
same address space, but there's no reason for us to continue to wait if the
next thing we're going to do is simply terminate -- it's a waste of time and of
a process.

`TASK_KILLABLE` was introduced to solve these kinds of cases. Instead of being
fully uninterruptible, when we recieve a signal we check if the signal is fatal
(that is, it's either a non-trappable fatal signal, or the program has no
userspace handler for it), and if it is, we terminate the process without
allowing it to execute any more userspace instructions.

We use this pretty widely in the kernel nowadays where possible:

{% highlight bash %}
% git grep -ihc _killable | paste -sd+ | bc
539
{% endhighlight %}

As such, you may well find that some of the D states that processes enter on
your system actually are terminable after all.

## Wait, that's illegal

I'm sure that some people reading the code I provided above are wondering
whether it's legal or not, given the fact that we are sharing the parent's
memory space. Here's what POSIX [has to say about
vfork](https://pubs.opengroup.org/onlinepubs/009696799/functions/vfork.html):

> The `vfork()` function shall be equivalent to `fork()`, except that the
> behavior is undefined if the process created by `vfork()` either modifies any
> data other than a variable of type `pid_t` used to store the return value
> from `vfork()`, or returns from the function in which `vfork()` was called,
> or calls any other function before successfully calling `_exit()` or one of
> the `exec` family of functions.

It makes sense that access to the parent's memory (and thus doing basically
anything other than `exec` (which replaces the process entirely) or `_exit`
(which is really just a syscall) is not POSIX-legal in the child forked by
vfork, because the parent cannot reasonably have the stack mutated under it
without its knowledge. But wait, didn't we just call a function? That's
certainly going to make use of the stack, right?

The good news it that in reality (or at least for some version of reality on
Linux with any real libc), things are not that dire. Just as one example,
CPython -- which is used and tested for with more diversity than the vast
majority of software in use today -- uses it in much the same way:

{% highlight c %}
Py_NO_INLINE static pid_t do_fork_exec(/* ... */)
{
    pid_t pid;
    PyThreadState *vfork_tstate_save;

    /* ... */

    vfork_tstate_save = PyEval_SaveThread();
    pid = vfork();
    if (pid != 0) {
        // Not in the child process, reacquire the GIL.
        PyEval_RestoreThread(vfork_tstate_save);
    }

    /* ... */

    if (pid != 0) {
        // Parent process.
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
calling child functions (see
[here](https://github.com/python/cpython/blob/v3.12.1/Modules/_posixsubprocess.c#L812-L823)
and
[here](https://github.com/python/cpython/blob/v3.12.1/Modules/_posixsubprocess.c#L553-L571)).
I think it would be safe to say that, despite some POSIX book banging and
semantics discussion, the world has not collapsed into a fiery pit yet as a
result.

So why is this okay enough to make it into codebases like CPython's? Well, when
the parent process continues its operation, additional stack data is simply
going to end up in the unallocated portion of the stack. The paused parent's
stack pointer register is still independent, even with `vfork`, so things just
continue about their merry way. All in all, despite standards ire, the whole
thing is relatively safe (if a little unpleasant).

## How can I survive SIGKILL, then?

While the above approach is nice and self contained and serves most use cases
for testing, its major downside is that it doesn't survive a SIGKILL, as
SIGKILL is always a deadly signal, and cannot be caught in userspace. In order
to survive that, we need to find a callsite which sets `TASK_UNINTERRUPTIBLE`
without `TASK_KILLABLE`.

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

From `man 8 fsfreeze`:

> `fsfreeze` suspends and resumes access to an filesystem. `fsfreeze` halts new
> access to the filesystem and creates a stable image on disk. `fsfreeze` is
> intended to be used with hardware RAID devices that support the creation of
> snapshots.

Importantly, this freeze is implemented by (among other things) indefinitely
taking exclusive write access over the filesystem's
[superblock](https://unix.stackexchange.com/a/4403/10762). The filesystem
superblock contains much of the high level, mission critical information for
the filesystem, and taking exclusive write access over it is tantamount to
denying any modification to the filesystem.

Importantly, this is implemented in `sb_wait_write`, which is implemented via
an array of per-CPU read-write semaphores:

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
will survive a `SIGKILL`, and the only way out is to unfreeze the filesystem.

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

No amount of killing will unblock this -- the filesystem must be unfrozen to
make forward progress. As you can see, it still exists even after a `kill -9`:

    % kill -9 21135
    % cat /proc/21135/comm
    mkdir

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

    % sudo /tmp/e
    PID 33088 is now in D state. Press <Enter> to unfreeze and clean up.

While slightly less self-contained than the `vfork` method, since it requires
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
2. **set_current_state(TASK_UNINTERRUPTIBLE)**: Of course, one can also just
   write a kernel module to do whatever one wants. This is easily the most
   complicated option to maintain long term, especially in a testing pipeline.
   It requires elevated privileges, and you have the extra bonus of potentially
   screwing up scheduling entirely depending on how you go about it.

All in all, the simplicity and flexibility of the `vfork` and `fsfreeze`
approaches make them ideal for most use cases. They don't require complex
setup, are controllable and reliable, and can easily be modified to be suitable
for different testing conditions.

Many thanks to [Johannes](https://github.com/hnaz), [Matthew][],
[Sam](https://samwho.dev/), and [Javier](https://hondu.co/) for reviewing this
post.

[Matthew]: https://kernelnewbies.org/MatthewWilcox
