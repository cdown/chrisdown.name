---
layout: post
title: "The curious case of stalled squashfs reads"
---

Here's an interesting issue I and [Tejun](https://github.com/htejun) looked at
a few days ago that I thought might be interesting to share with a wider
audience. I hope it can serve as an example that kernel internals aren't just a
black box when it comes to debugging, and it's possible to work these things
out with a little patience and a careful eye.

squashfs lives an incredibly versatile life. Many Linux users know it as the
read-only filesystem that has powered almost the entire history of Linux Live
CDs (excluding early efforts such as Yggdrasil and DemoLinux). Many Linux
programmers also know it as a versatile filesystem for embedded use due to its
support for transparent compression. Those looking at the history of squashfs
changes inside the kernel will also see changes from Facebook, Google, and many
other industry names, as it also serves a purpose serving production traffic at
scale.

One thing we use squashfs for is transporting large amounts of static data that
compress well: bytecode, certain types of static resources, etc. We then
transfer these squashfs images over the network to the servers providing
compute power for the service, mount the squashfs mounts, and away we go.

Visualise such a situation: we've just finished transporting the squashfs
images and are getting ready to use the files inside in the program. We go to
load files from within this squashfs mount within the program, and usually all
goes well. Sometimes, however, many of the program's threads seem to stall
while trying to read data from this squashfs image, resulting in slower startup
times. In this case, we found this when testing I/O limits as part of
cgroup v2 work -- in this case we expect I/O throughput to be reduced, but we
don't expect applications to stall entirely. Take a look at the following two
kernel stacks for two threads from the application, and have a think about what
looks weird here.

Here's how one thread looks (derived from `/proc/[pid]/task/[tid]/stack`):

     #0 __schedule
     #1 schedule
     #2 io_schedule
     #3 bit_wait_io
     #4 __wait_on_bit
     #5 out_of_line_wait_on_bit
     #6 __wait_on_buffer
     #7 squashfs_read_data
     #8 squashfs_cache_get
     #9 squashfs_get_datablock
    #10 squashfs_readpage_block
    #11 squashfs_readpage
    #12 __do_page_cache_readahead
    #13 filemap_fault
    #14 __do_fault
    #15 __handle_mm_fault
    #16 handle_mm_fault
    #17 __do_page_fault
    #18 do_page_fault
    #19 page_fault

Here's how some other threads look -- the stack is similar, but subtly
different:

     #0 __schedule
     #1 schedule
     #2 squashfs_cache_get
     #3 squashfs_get_datablock
     #4 squashfs_readpage_block
     #5 squashfs_readpage
     #6 __do_page_cache_readahead
     #7 ondemand_readahead
     #8 page_cache_sync_readahead
     #9 generic_file_read_iter
    #10 __vfs_read
    #11 vfs_read
    #12 sys_read
    #13 do_syscall_64

In the first stack, we're trying to read in data as part of a [major
fault](https://en.wikipedia.org/wiki/Page_fault#Major). Essentially, this means
that we want to read some particular memory which is backed by persistent
storage, but don't have it loaded in to memory. As such, we have to actually
perform I/O to service the request for data by loading it into main memory, and
in this case the file is on a squashfs mount, so we need to call
squashfs-specific functions (like `squashfs_readpage`) to access it.

In the second stack, we're trying to read a file from disk using the `read`
syscall. That's what `sys_read` (frame 12) does, although it passes most of the
hard work to `vfs_read` (frame 11). Eventually, again, this works out that it
should call squashfs-specific functions to read from the squashfs filesystem,
resulting in the call to [`squashfs_readpage` at frame
5](https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux-stable.git/tree/fs/squashfs/file.c?h=linux-4.15.y#n453).

Both stacks end in `schedule()`, which is a thin wrapper around the
[`__schedule()`
function](https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux-stable.git/tree/kernel/sched/core.c?h=linux-4.15.y#n3288)
inside the kernel. `__schedule()` here is a way of voluntarily hinting to the
kernel's CPU scheduler<sup>* well, kind of</sup> that we are about to perform a high-latency operation
(like disk or network I/O) and that it should consider finding another process
to schedule instead of us for now. This is good, as it allows us to signal to
the kernel that it is a good idea to go ahead and pick a process that will
actually make use of the CPU instead of wasting time on one which can't
continue until it's finished waiting for a response from something that may
take a while.

<small><sup>*</sup> `schedule()` is also used in some involuntary cases when
`TIF_NEED_RESCHED` is set, but I could write a whole other post on preemptible
kernels, `TIF_NEED_RESCHED`, and the like, so I won't go into that here. You
can tell the difference here because this path is not in interrupt handling,
which is the main place where involuntary context switches using `schedule()`
happen. We also have some kind of "implicitly voluntary" cases -- the main one
being returning from a syscall. `schedule()` can also be called as part of
`preempt_enable` (when we enable preemption) and `cond_resched` (which is
basically just `schedule()` with more checks up front). If this note was
confusing, don't worry, you don't need it to understand the rest of the post
:-)</small>

Disk or network I/O are big reasons that an application may voluntarily signal
the scheduler to choose another process, and that's certainly what we see in
the first stack -- `io_schedule()` is a wrapper around `schedule()` that also
does some statistical accounting for things like
[iowait](https://www.ibm.com/developerworks/community/blogs/AIXDownUnder/entry/iowait_a_misleading_indicator_of_i_o_performance54?lang=en),
and indicates that the reason we chose to `schedule()` is because of I/O.

The second stack gets more interesting when you look at it in comparison with
the first one, and when you consider that many threads are blocked in it. We've
called `schedule()`, as before, but this time it's not because of I/O. Instead,
the reason we schedule is because of something related to getting data from the
squashfs block cache as indicated by `squashfs_cache_get` being the frame
above the call to `schedule()`.

Looking at `fs/squashfs/cache.c`, which is where `squashfs_cache_get` is
defined, we can see from the code structure that [squashfs internally uses a
fixed-size cache as part of its read/decompress
path](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/fs/squashfs/cache.c?h=v4.16#n65).
If we read into `squashfs_cache_get` a bit, we start to see where we might
become blocked in this function. One place that clearly stands out is where we
explicitly [wait until a cache entry is available for
use](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/fs/squashfs/cache.c?h=v4.16#n83):

{% highlight c %}
/*
 * Block not in cache, if all cache entries are used
 * go to sleep waiting for one to become available.
 */
if (cache->unused == 0) {
    cache->num_waiters++;
    spin_unlock(&cache->lock);
    wait_event(cache->wait_queue, cache->unused);
    spin_lock(&cache->lock);
    cache->num_waiters--;
    continue;
}
{% endhighlight %}

`wait_event` here is what we're really looking for -- it's where we start
waiting for a cache entry to become available so that we can use it. If no
cache entry is available we simply wait and then notify the CPU scheduler
(through the aforementioned `schedule()`) that it should do something else
until we're ready. This brings up two related questions: how big is the cache?
How many blocks can we read simultaneously before we end up waiting here?

Looking at the the next frame up, `squashfs_get_datablock()` that calls
`squashfs_cache_get()`, [we can see that the cache being used in the blocking
stack is hardcoded to be
`msblk->read_page`](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/fs/squashfs/cache.c?h=v4.16#n404):

{% highlight c %}
/*
 * Read and decompress the datablock located at <start_block> in the
 * filesystem.  The cache is used here to avoid duplicating locking and
 * read/decompress code.
 */
struct squashfs_cache_entry *squashfs_get_datablock(struct super_block *sb,
				u64 start_block, int length)
{
	struct squashfs_sb_info *msblk = sb->s_fs_info;

	return squashfs_cache_get(sb, msblk->read_page, start_block, length);
}
{% endhighlight %}

All we have to do now is find where `msblk->read_page` is initialised to find
the cache size. Searching for `->read_page` [reveals this piece of code
in
fs/squashfs/super.c](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/fs/squashfs/super.c?h=v4.16#n209):

{% highlight c %}
/* Allocate read_page block */
msblk->read_page = squashfs_cache_init("data",
    squashfs_max_decompressors(), msblk->block_size);
{% endhighlight %}

The second parameter passed to `squashfs_cache_init()` here is the number of
cache entries available. Here, it's set to the same value as
`squashfs_max_decompressors()`, which is the number of decompressor threads
that squashfs can use. The fact that the number of available cache entries is
directly set to the number of decompressor threads is somewhat intriguing, as
it implies that calling this a "cache" in this case is somewhat misleading --
this isn't really a cache, it's really just a work area for temporary storage.
We don't really cache anything in the read cache past its initial use.

Now the big question is what the value returned from
`squashfs_max_decompressors()` is. Looking at its definition shows it in three
files:

- In fs/squashfs/decompressor_multi.c, it's defined as the number of online
  CPUs, multiplied by two;
- In fs/squashfs/decompressor_multi_percpu.c, it's defined as the number of
  *possible* CPUs. "Possible" here means the total number of possible CPUs that
  may come online (for example, via hotplug);
- In fs/squashfs/decompressor_single.c, it's just hardcoded to `return 1`.

Usually when there are multiple definitions of a single function in the kernel,
it means that there is a config option which decides which is eventually passed
to the compiler. This case is no exception, and [we can see the following in
fs/squashfs/Makefile](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/fs/squashfs/Makefile/?h=v4.16):

    squashfs-$(CONFIG_SQUASHFS_DECOMP_SINGLE) += decompressor_single.o
    squashfs-$(CONFIG_SQUASHFS_DECOMP_MULTI) += decompressor_multi.o
    squashfs-$(CONFIG_SQUASHFS_DECOMP_MULTI_PERCPU) += decompressor_multi_percpu.o

Ok, so which of these is the one enabled on the machine having the issue? One
useful config option which most people have enabled is `CONFIG_IKCONFIG_PROC`,
which emits the config for the currently running kernel at `/proc/config.gz`.
Using that we can now tell which of these config options we have enabled, and
thus which file we actually considered during compilation:

    $ zgrep CONFIG_SQUASHFS_DECOMP_ /proc/config.gz
    CONFIG_SQUASHFS_DECOMP_SINGLE=y
    # CONFIG_SQUASHFS_DECOMP_MULTI is not set
    # CONFIG_SQUASHFS_DECOMP_MULTI_PERCPU is not set

Well, this is interesting. Since our kernel was configured to use a single
squashfs decompressor, and now we know that the number of decompressors is
directly used as the number of cache entries, we also now know that this means
that we can only do one major fault or read at a time within a block as any
further reads occurring at the same time will become blocked in the
`wait_event()` code mentioned earlier. This clearly shows as being the reason
why we get descheduled from the CPU, and thus the reason why overall forward
progress of our program stalls.

![Priority inversions? In *my* Linux? It's more likely than you think.](/images/blog/squashfs/archer.png)

This setting probably makes some sense in squashfs's embedded usecases where
memory savings are critical, but it doesn't really on production servers. As of
kernel 4.16, using a single decompressor is still the default decompressor
setting for most architectures when you enable squashfs. I'll likely start a
conversation about changing this for an upcoming release.

So, how should we fix this? In most cases, changing your kernel config to use
`CONFIG_SQUASHFS_DECOMP_MULTI` should work around this issue well enough by
introducing higher concurrency limits (the number of online CPUs multiplied by
two, as mentioned above), thus avoiding having to wait for the cache entry to
become free to continue reading from squashfs. This is still somewhat of a
workaround for the way that squashfs does decompression, though, rather than a
real fix.

While the suggested workaround will probably be fine for most use cases, it's
worth also pointing out that if you are thinking about starting a new
production service that needs transparent compression, you might consider using
[btrfs with compression
support](https://btrfs.wiki.kernel.org/index.php/Compression) -- it's generally
more featureful and has been built with consideration for modern situations
that were uncommon or didn't exist when squashfs was invented, like resource
enforcement with cgroups, huge numbers of accessing threads, etc, etc. In my
experience there are generally fewer surprises when using btrfs nowadays
compared to squashfs.

I know plenty of people who get stuck when encountering issues that seem to
lead into the kernel. Hopefully this post can help you become more familiar
with some of the common tropes encountered when looking at kernel issues, and
possibly give you the confidence to dive into a few yourself :-)

Many thanks to [Rahul](https://github.com/rahulg) for proofreading this post.
