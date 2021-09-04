---
layout: post
title: "tmpfs inode corruption: introducing inode64"
---

A few months ago I got a report from a service owner that their service was
crashing when trying to access certain files stored in tmpfs. This service
provides a way to do things like builds on niche architectures/platforms, and
as part of that retrieves and stores a large cache of required files for the
requisite job in `/dev/shm`, preventing needing them to fetch for other jobs
with the same dependencies.

As part of this lifecycle, this service stores a mapping from each file's inode
number to its own metadata relevant to the data retrieved. Simple enough, and
on the face of it this seems fine: generally the contract the kernel provides
is that as long as the device, inode number, and generation are the same, this
is guaranteed to point to the same data during the lifetime of the kernel.

This is made even simpler by the fact that tmpfs doesn't support inode
generations -- `ioctl(FS_IOC_GETVERSION)` returns `ENOTTY`:

{% highlight c %}
#include <sys/ioctl.h>
#include <sys/fcntl.h>
#include <linux/fs.h>
#include <stdio.h>
#include <errno.h>
#include <stdlib.h>

int main(int argc, char* argv[])
{
    int generation, fd;

    if (argc != 2)
        return EXIT_FAILURE;

    fd = open(argv[1], O_RDONLY);

    if (fd < 0)
        return EXIT_FAILURE;

    if (ioctl(fd, FS_IOC_GETVERSION, &generation)) {
        perror("ioctl");
        return EXIT_FAILURE;
    }

    printf("%d\n", generation);
}
{% endhighlight %}

    % : > /dev/shm/test
    % ./generation /dev/shm/test
    ioctl: Inappropriate ioctl for device

As such, that just leaves device and inode number to distinguish identity, and
since we're always using /dev/shm as the base with no descendant mountpoints,
storing the inode number alone should be enough.

## Production says no

So far, everything sounds good, but it was not so in production. On machines
with high uptimes, the team responsible for this service was seeing
intermittent failures that appeared to be caused by inode number collisions:

    [root@service ~]# cd /dev/shm/svc
    [root@service svc]# stat ApplyTuple.h
      File: 'ApplyTuple.h'
      Size: 7270            Blocks: 16         IO Block: 4096
    Device: 14h/20d Inode: 3924537249  Links: 5
    Access: (0555/-r-xr-xr-x)  Uid: (    0/    root)
    Access: 2020-12-19 09:30:01.378353516 -0800
    Modify: 2020-12-19 09:30:01.378353516 -0800
    Change: 2020-12-19 09:30:01.378353516 -0800
    Birth: -
    [root@service svc]# stat PriorityUnboundedQueueSet.h
      File: 'PriorityUnboundedQueueSet.h'
      Size: 3302            Blocks: 8          IO Block: 4096
    Device: 14h/20d Inode: 3924537249  Links: 3
    Access: (0555/-r-xr-xr-x)  Uid: (    0/    root)
    Access: 2020-12-19 09:29:53.007252542 -0800
    Modify: 2020-12-19 09:27:23.370451978 -0800
    Change: 2020-12-19 09:27:29.575526501 -0800
    Birth: -
    [root@service svc]# cksum ApplyTuple.h PriorityUnboundedQueueSet.h
    2624198482 7631 ApplyTuple.h
    3677425165 5658 PriorityUnboundedQueueSet.h

Well, this is not good. Notice that the reported inode number for both of these
files is 3924537249, but we not only have two clearly distinct inodes -- for
example, inodes store the modification times, and those don't line up -- but
also completely different data entirely. Clearly something has gone quite
wrong.

## Volatile inode numbers

On non-volatile filesystems, inode numbers are typically finite and often have
some kind of implementation-defined semantic meaning (eg. implying where the
inode is disk). Take for example ext4's bytes-per-inode ratio, which is
configurable with `mkfs.ext4 -i`. This behaviour means that it's typically very
hard to get inode number collisions without significant filesystem corruption.

On the other hand, tmpfs doesn't have such limits, since it doesn't actually
need to store inode data outside of memory, and thus worry about inode
placement. In reality, a tmpfs inode is very bare bones, and the inode number
(for example) is just taken from a global incrementing counter,
`get_next_ino()`. The code backing that counter is literally as simple as this:

{% highlight c %}
#define LAST_INO_BATCH 1024
static DEFINE_PER_CPU(unsigned int, last_ino);

unsigned int get_next_ino(void)
{
        unsigned int *p = &get_cpu_var(last_ino);
        unsigned int res = *p;

#ifdef CONFIG_SMP
        if (unlikely((res & (LAST_INO_BATCH-1)) == 0)) {
                static atomic_t shared_last_ino;
                int next = atomic_add_return(LAST_INO_BATCH,
					     &shared_last_ino);

                res = next - LAST_INO_BATCH;
        }
#endif

        res++;
        /* get_next_ino should not provide a 0 inode number */
        if (unlikely(!res))
                res++;
        *p = res;
        put_cpu_var(last_ino);
        return res;
}
{% endhighlight %}

What this says is essentially this:

1. Each CPU has its own `last_ino` variable, with its own distinct value.
2. Get the value of this CPU's `last_ino` variable.
3. Assuming you're on a multiprocessing (SMP) system -- which you are, because
   it's 2021 -- try to do some batching so that CPUs don't have to synchronise
   too often. Each CPU gets a batch of 1024 slots, and then it has to come back
   to get another 1024, and so on.

Looks pretty simple, right? Unfortunately, there's something awry that you
might miss if you just skim over the code, and don't look closely at the
function and variable types: they're all `unsigned int`. On an x86_64 machine,
an `unsigned int` is 32 bits wide, and it's pretty trivial to exceed 2^32
incrementations of the get_next_ino() counter if you're creating a lot of
files. We also don't try to reuse inode numbers from freed inodes (and we'll
come back to that a little later).

If you're a kernel developer, you probably already know that the kernel
actually has a special type for inode numbers, `ino_t`, and on x86_64 machines,
it's 64 bits wide. As such a trivial fix might simply be to change
`get_next_ino` and `last_ino` to be of type `ino_t`. When I tested this, this
appeared to work with no obvious ramifications, but there was a comment above
which gave some pause:

{% highlight c %}
/*
 * On a 32bit, non LFS stat() call, glibc will generate
 * an EOVERFLOW error if st_ino won't fit in target struct
 * field.
 */
{% endhighlight %}

So the problem is that if you have a 32-bit executable compiled without
`_FILE_OFFSET_BITS=64` on a system with a 64-bit wide `ino_t`, glibc's `stat()`
will simply fail with EOVERFLOW for inode numbers greater than 2^32. As such,
we need a support option for those who need to preserve this legacy behaviour,
while still allowing more modern systems to avoid this issue.

## Intermediate storage issues

There is also one more problem: I mentioned earlier that `get_next_ino()` is a
_global_ pool -- we also use it for things like sockets, pipes, and other
things that are disconnected from physical storage on the backing filesystem.
While the original issue was largely isolated to tmpfs, changing
`get_next_ino()` as a whole meant that some ramifications are harder to
predict.

For example, we have code in prod that tries produce a mapping of sockets to a
list of pids which use them. In order to do this, we use the netlink interface
to query for sockets in a particular state we care about (say, `LISTEN`), and
then iterate /proc/pid/fd to find the process or processes which have this
socket open.

The net subsystem stores some of its information in its own structs for
reference later. One of the things which it stores is the inode number for the
socket:

{% highlight c %}
int inet_diag_msg_attrs_fill(struct sock *sk, struct sk_buff *skb,
                             struct inet_diag_msg *r, int ext,
                             struct user_namespace *user_ns,
                             bool net_admin)
{
        /* ... */
        r->idiag_inode = sock_i_ino(sk);
        /* ... */
}
{% endhighlight %}

If you just skim this, this looks fine. But what about if we actually look at
the type of `idiag_inode` in `struct inet_diag_msg`?

{% highlight c %}
struct inet_diag_msg {
        __u8        idiag_family;
        __u8        idiag_state;
        __u8        idiag_timer;
        __u8        idiag_retrans;

        struct inet_diag_sockid id;

        __u32        idiag_expires;
        __u32        idiag_rqueue;
        __u32        idiag_wqueue;
        __u32        idiag_uid;
        __u32        idiag_inode;  /* uh oh */
};
{% endhighlight %}

...oh dear. `struct inet_diag_msg` explicitly stores the inode number as a
32-bit wide unsigned integer, and we end up with a similar issue as described
earlier with a 32-bit userland, just with no nice error handling this time.
Instead, we simply overflow entirely. This means that this code strategy no
longer works because stat() (using `ino_t`) and netlink (using `__u32`) no
longer agree about the socket's inode number:

{% highlight bash %}
# netlink says 3293907245 due to overflow,
# but proc says 16178809133
 
% ls -l /proc/996/fd
total 0
lrwx------ 1 root root 64 Feb 19 03:19 0 -> /dev/null
lrwx------ 1 root root 64 Feb 19 03:19 1 -> socket:[16178809133]
{% endhighlight %}

At this point it became pretty clear that changing `get_next_ino` itself was
not going to work -- there are too many callsites already depending on its
behaviour, and there are even callsites like the example here that transcend
into userspace. No, if this was to be fixed in a way that could be accepted
upstream, one would have to change how tmpfs handles inode numbering itself,
and get it away from `get_next_ino()` entirely.

## Resolution

After quite a bit of back and forth, my patches in ["tmpfs: per-superblock
i_ino
support"](https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/patch/?id=e809d5f0b5c912fe981dce738f3283b2010665f0)
and ["tmpfs: support 64-bit inums
per-sb"](https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/patch/?id=ea3271f7196c65ae5d3e1c7b3f733892c017dbd6)
were merged into kernel 5.9.

In essence, the patches move tmpfs' inode allocation away from the get_next_ino
shared pool, in favour of our own
[superblock](http://www.linfo.org/superblock)-based
system, and add support for 64-bit inodes using the `inode64` tmpfs mount
option (or allow having it on by default by enabling `CONFIG_TMPFS_INODE64`
when compiling the kernel).

We now use `ino_t` everywhere, and for legacy users we simply emulate the old
behaviour by doing manual wraparounds when we reach UINT_MAX. This also allows
us to catch these cases when they happen and print a warning for the system
administrator to act on, suggesting to move to inode64.

Arch Linux also [moved to enable this by
default](https://twitter.com/unixchris/status/1374081759181205506) from kernel
5.9-ARCH onwards, which means this feature has been tested widely on real
workloads. Thanks, Arch folks!

In conclusion:

- This issue has likely been the root cause of a non-trivial number of
  unreproducible or transient failures in systems which are dependent on inode
  numbering. Reproducing this issue is heavily dependent on the system state,
  requires a workload which practises heavy file creation in tmpfs, and is
  typically likely to manifest as transient errors which go away when retried.
  As such, this issue has likely been a significant cause of hard to pin down
  unreliability in such systems for a significant period of time.
- If you rely on tmpfs inode numbering in production, I strongly recommend
  mounting it with `inode64` or compiling your prod kernels with
  `CONFIG_TMPFS_INODE64` in order to get 64-bit inode numbering for tmpfs.
