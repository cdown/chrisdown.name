---
layout: post
title: "The curious case of squashfs page faults"
---

Here's an interesting issue I and [Tejun](https://github.com/htejun) looked at
a few days back that I thought might be interesting to share with a wider
audience.

squashfs lives an incredibly versatile life. Many Linux users know it as the
read-only filesystem that has powered almost the entire history of Linux Live
CDs (excluding early efforts such as Yggdrasil and DemoLinux). Many Linux
programmers also know it as a versatile filesystem for embedded use due to its
support for transparent compression. Those looking at the history of squashfs
changes inside the kernel will also see many changes from us (Facebook),
Google, and many other industry names, as it also serves a purpose serving
production traffic at scale.

One thing we use squashfs for is transporting large amounts of static data that
compress well: bytecode, certain types of static resources, etc. We then
transfer these squashfs images over the network to the servers providing
compute power for the service, mount the squashfs mounts, and away we go.

So here we are after transporting the squashfs images, getting ready to use the
files inside in the program. We go to load them in the program, and usually all
goes well. Sometimes, however, when under I/O contention on the underlying
block device, an interesting situation happens -- we seem to stall, but even
worse than we would usually expect for this level of I/O contention. Take a
look at the following two kernel stacks for two threads from the application,
and have a think about what looks weird here.

Here's how one thread looks:

     #0 [ffffc9000d6778c0] __schedule at ffffffff818eed27
     #1 [ffffc9000d677940] schedule at ffffffff818ef386
     #2 [ffffc9000d677958] io_schedule at ffffffff810b3a06
     #3 [ffffc9000d677970] bit_wait_io at ffffffff818efaf1
     #4 [ffffc9000d677988] __wait_on_bit at ffffffff818ef724
     #5 [ffffc9000d6779c8] out_of_line_wait_on_bit at ffffffff818ef892
     #6 [ffffc9000d677a38] __wait_on_buffer at ffffffff8124d3d7
     #7 [ffffc9000d677a48] squashfs_read_data at ffffffffa01fc1b8 [squashfs]
     #8 [ffffc9000d677ac0] squashfs_cache_get at ffffffffa01fc6ad [squashfs]
     #9 [ffffc9000d677b28] squashfs_get_datablock at ffffffffa01fce41 [squashfs]
    #10 [ffffc9000d677b38] squashfs_readpage_block at ffffffffa01ff8a8 [squashfs]
    #11 [ffffc9000d677bb8] squashfs_readpage at ffffffffa01fdbed [squashfs]
    #12 [ffffc9000d677c50] __do_page_cache_readahead at ffffffff8119c6a8
    #13 [ffffc9000d677d08] filemap_fault at ffffffff81190f15
    #14 [ffffc9000d677dd0] __do_fault at ffffffff811c28fe
    #15 [ffffc9000d677df0] __handle_mm_fault at ffffffff811c71a9
    #16 [ffffc9000d677ea0] handle_mm_fault at ffffffff811c78d1
    #17 [ffffc9000d677ed0] __do_page_fault at ffffffff81050f39
    #18 [ffffc9000d677f40] do_page_fault at ffffffff810511bc
    #19 [ffffc9000d677f50] page_fault at ffffffff818f49a2

Here's how some other threads look -- the stack is similar, but subtly
different:

     #0 [ffffc900085e7a58] __schedule at ffffffff818eed27
     #1 [ffffc900085e7ad8] schedule at ffffffff818ef386
     #2 [ffffc900085e7af0] squashfs_cache_get at ffffffffa01fc7fa [squashfs]
     #3 [ffffc900085e7b58] squashfs_get_datablock at ffffffffa01fce41 [squashfs]
     #4 [ffffc900085e7b68] squashfs_readpage_block at ffffffffa01ff8a8 [squashfs]
     #5 [ffffc900085e7be8] squashfs_readpage at ffffffffa01fdbed [squashfs]
     #6 [ffffc900085e7c80] __do_page_cache_readahead at ffffffff8119c6a8
     #7 [ffffc900085e7d38] ondemand_readahead at ffffffff8119c859
     #8 [ffffc900085e7d80] page_cache_sync_readahead at ffffffff8119cb21
     #9 [ffffc900085e7d90] generic_file_read_iter at ffffffff8119021a
    #10 [ffffc900085e7e48] __vfs_read at ffffffff81217dbe
    #11 [ffffc900085e7ec8] vfs_read at ffffffff81218c2c
    #12 [ffffc900085e7ef8] sys_read at ffffffff8121a106
    #13 [ffffc900085e7f38] do_syscall_64 at ffffffff8100285d

In the first stack, we're trying to read in data as part of a [major
fault](https://en.wikipedia.org/wiki/Page_fault#Major). Essentially, this means
that we want to read some particular memory which is related to a file, but
don't have it loaded in to memory. As such, we have to actually perform I/O to
service the request for data by loading it into main memory, and in this case
the file is on a squashfs mount, so we need to call squashfs-specific functions
to access it.

In the second stack, we're trying to read a file from disk using the `read`
syscall. That's what `sys_read` (frame 12) does, although it passes most of the
hard work to `vfs_read` (frame 11). Eventually, this works out that it should
call squashfs-specific functions to read from the squashfs filesystem,
resulting in the call to [`squashfs_readpage` at frame
5](https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux-stable.git/tree/fs/squashfs/file.c?h=linux-4.15.y#n453).

Both stacks end in `schedule()`, which is a thin wrapper around the
[`__schedule()`
function](https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux-stable.git/tree/kernel/sched/core.c?h=linux-4.15.y#n3288).
`__schedule()` is a way of voluntarily hinting to the kernel's CPU
scheduler that we are about to perform a slow operation (like disk I/O) and
that it should consider finding another process to schedule instead of us for
now. This is good, as it allows us to see when it is a good idea to go ahead
and pick a process that will actually make use of the CPU instead of one which
is waiting for a response from something that may take a while.

Disk or network I/O are big reasons that an application may voluntarily signal
the scheduler to choose another process, and that's certainly what we see in
the first stack -- `io_schedule()` is a wrapper around `schedule()` that also
does some statistical accounting for things like
[iowait](https://www.ibm.com/developerworks/community/blogs/AIXDownUnder/entry/iowait_a_misleading_indicator_of_i_o_performance54?lang=en),
and indicates the reason we chose to `schedule()` is because of I/O.

The second stack gets more interesting when you look at it in comparison with
the first one, and when you consider that many threads are blocked in it. We've
called `schedule()`, as before, but this time it's not because of I/O. Instead,
the reason we schedule is because of something related to getting data from the
squashfs block cache (as indicated by `squashfs_cache_get` being the frame
above). Intriguing!

Looking at `fs/squashfs/cache.c`, which is where `squashfs_cache_get` is
defined, we can see that squashfs internally uses a fixed-size cache as part of
its read/decompress path. 


While using squashfs is totally fine, before I get started I'd like to suggest
that if you are thinking about starting a new production service that needs
transparent compression, consider using [btrfs with compression
support](https://btrfs.wiki.kernel.org/index.php/Compression) -- it's generally
more featureful and has been built with consideration for modern situations
that were uncommon or didn't exist when squashfs was invented, like resource
enforcement with cgroups, huge numbers of accessing threads, etc, etc. In my
experience there are generally less surprises when using btrfs nowadays
compared to squashfs.


