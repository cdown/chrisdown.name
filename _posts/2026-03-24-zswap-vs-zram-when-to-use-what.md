---
layout: post
title: "Debunking zswap and zram myths"
description: "zswap and zram are fundamentally different approaches with different philosophies. If in doubt, use zswap."

---

tl;dr:

**If in doubt, prefer to use zswap. Only use zram if you have a highly specific reason to.**

In terms of architecture:

- *zswap* sits in front of your disk swap, compresses pages in RAM, and
  automatically tiers cold data to disk. It integrates directly with the
  kernel's memory management and distributes pressure gracefully.
- *zram* is a compressed RAM block device with a hard capacity limit. When you
  put swap on it and it fills up, there is no automatic eviction, and the
  kernel has very little leverage to do anything about the situation. The
  system either OOMs or falls back to lower-priority swap, causing LRU
  inversion (see below). It only really makes sense for extremely
  memory-constrained embedded systems, diskless setups, or cases with specific
  security requirements around keeping private data off persistent storage.
  Swap on zram is also increasingly unsupported upstream.

My advice is:

- **Do not run zram alongside disk swap** wherever possible. In such setups,
  zram fills fast RAM with cold, stale pages while pushing your active working
  set onto slow disk, making things actively worse than if you had no
  compressed swap at all.
- **If you must use zram**, pair it with a userspace OOM manager like
  [systemd-oomd](https://www.freedesktop.org/software/systemd/man/latest/systemd-oomd.service.html)
  or [earlyoom](https://github.com/rfjakob/earlyoom). Without one, the kernel's
  OOM killer can leave the system hung for minutes before acting, as it often
  only fires after exhausting many cycles of aggressive reclaim that often
  accomplish nothing (more on this below).
- **On servers, zram has additional significant problems.** One major one is
  that its memory usage is totally segregated from the rest of the system, and as
  such is not charged to any cgroup, breaking isolation semantics.

---

I recently received a question from a reader about compressed swap technologies
on Linux:

> I read your articles about memory management (swap) on Linux, finally some
> words from the expert :) instead of internet experts "you have 32GB - disable
> it".
>
> It'd be nice to have a follow-up about zswap or zram ... :) if they're good
> (on desktop with 32GB RAM or more), which one is better and why ... I
> understand how they work (from descriptions), but it's difficult to measure
> it and compare in real life. Again, a lot of "internet experts" just say
> "zram - because you don't wear your SSD" ...

Well, first of all, since I'm writing this article, clearly flattery will get
you everywhere ;-)

It is true that there is a lot of confusion and misinformation on the internet
about when to use zswap versus zram, and the tradeoffs between them. I've
worked on kernel memory management and swap code for the better part of a
decade now, and I've seen these technologies evolve and some of the common
misconceptions that arise around them.

The short answer for most people is: use zswap. Do not use zram without an
extensive understanding of the risks it may pose to your workloads. But
understanding why (and understanding when zram may actually be the right call)
requires going into how each of these two technologies work in the kernel
itself.

## Architectural differences

Most people think of zswap and zram simply as two different flavours of the
same thing, compressed swap -- a mechanism to offload pages from physical RAM,
typically to disk, to compressed RAM, or through both in sequence. Superficially,
that's correct -- they both hold swapped pages -- but they make fundamentally
different bets about how the kernel should handle memory pressure, and picking
the wrong one for your situation can actively make things worse than having no
swap at all.

The most significant difference between them lies in where they sit in the
kernel's storage hierarchy, and thus, what they are capable of signalling to
the rest of the kernel:

- zram acts as a compressed block device, essentially a virtual disk in RAM.
  When a process needs to swap, the kernel treats swap on zram like it does on
  any other block device, sending I/O requests through the block layer.
  Importantly, once zram fills up, it's just another storage device that's
  reached capacity. There's no automatic mechanism to move data elsewhere,
  which means cold pages that were swapped out first stay locked in fast RAM
  with no way to evict them. As you can imagine, that's typically very bad.
- zswap, on the other hand, is more integrated with the memory management
  subsystem. It acts as a compression layer that sits in front of your disk
  swap. When a process needs to swap, zswap intercepts the page before it
  reaches disk, decides whether to compress it, and if it does, it stores it in
  a memory pool. When that pool fills up, zswap uses its own heuristics to
  evict the least recently used pages to your backing swap device, aiming to
  keep your hot data present in the compressed RAM cache.

To put it another way, zram provides a hard capacity limit, whereas zswap
provides automatic tiering between faster (that is, compressed RAM) and slower
swap (that is, your disk) and gracefully degrades as memory pressure increases.
For most people, graceful degradation is what you want, but let's look at how
these play out in practice.

### zram's block device architecture

zram creates a compressed block device that acts as standalone swap. The
typical procedure for setting up swap on zram is to:

1. Create a zram device by loading the module with `modprobe zram`
2. Set `/sys/block/zram0/comp_algorithm` (the compression algorithm to use) and `/sys/block/zram0/disksize` (the virtual device capacity)
3. `mkswap` on `/dev/zram0`
4. `swapon` on `/dev/zram0`

You may notice that this looks pretty much exactly like what you would do if
you were setting up swap on a partition, and that's not a coincidence: the
kernel sees it as just another storage device through the block layer (see
[zram_submit_bio()](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/block/zram/zram_drv.c?h=v6.19#n2658)).

This makes zram a natural fit for embedded systems: it's completely
self-contained, with no dependency on disk storage, which these systems likely
don't have in the first place. When you're on an embedded controller or a
Raspberry Pi with an SD card, zram gives you some amount of memory offload
without any external dependencies. All pretty reasonable so far.

However, when you *do* have disk storage available (like an SSD), zram's block
device architecture creates some significant constraints. The kernel is
essentially naive to zram being any different from a typical block device on a
slow disk, and so applies its normal disk-oriented defaults to it. As just one
example, there is a kernel tunable called `vm.page-cluster` that decides how
many pages we want to read ahead when we are faulting in a single swap page.
It is logarithmic, so for example, if `vm.page-cluster` is 4, we would read in
2^4 pages to try to amortise disk work ahead of time while it's cheap and
sequential. This is more important on hard drives, but there is still a
meaningful performance delta between random and sequential reads even on modern
NAND.

When we started working on using zram on Quest (since it runs on Android, which
makes use of zram), one problem we ran into was `vm.page-cluster`: it defaults
to 3, meaning the kernel reads 2^3 pages at once from swap as a readahead
optimisation. When reading from disk, that's sensible: pages near each other on
disk tend to be needed near each other in time, so it's good to amortise. But
with zram, this assumption no longer holds at all, and in fact works against
you quite considerably. With zram, compressed pages have no locality, so you're
paying for 8 swap-ins every time you need 1. Importantly, this is neither
something specific to Quest, nor `vm.page-cluster`, it's more a consequence of
the kernel treating zram like any other block device. `vm.page-cluster` is at
least tunable, but there are other assumptions baked into the kernel that
aren't even exposed as sysctls. In many cases the kernel will fight against
you, and it takes a lot of effort and knowledge to get this right.

### zswap's memory management integration

By comparison, zswap doesn't create a block device at all -- it integrates
directly into the kernel's memory management subsystem. That distinction is
more significant than it might sound: because zswap is woven into the reclaim
path itself, the kernel actually knows which pages in the zswap pool are hot
and which are cold. zram, being just another block device, has no such
visibility.

That awareness is the basis for automatic tiering, and it's the main reason
that zswap degrades significantly better than zram when there is memory
pressure.

{% sidenote %}
To enable zswap, check if it's already on with `cat
/sys/module/zswap/parameters/enabled`. Most major distributions enable it by
default. If not:

    echo 1 > /sys/module/zswap/parameters/enabled

To make it persistent across reboots, add `zswap.enabled=1` to your kernel
command line.

On allocator selection, prefer zsmalloc over the older z3fold or zbud
allocators. zsmalloc achieves much higher compression ratios by grouping
similar objects, whereas the older allocators use fixed-size objects that tend
to waste space. z3fold and zbud (along with the zpool interface itself) have
been removed from the upstream kernel, so on a current kernel you don't need to
set this. On distro kernels that still carry them, you may need to explicitly
select zsmalloc:

    echo zsmalloc > /sys/module/zswap/parameters/zpool
{% endsidenote %}

So how does all of this work? Well, when the kernel needs to swap out a page,
it calls `swap_writeout()`, which gives zswap first dibs to intercept it:

{% cc %}

{% highlight c %}
int swap_writeout(struct folio *folio, struct swap_iocb **swap_plug)
{
    /* ... */

    if (zswap_store(folio)) { /* zswap has called bagsy on the page */
        count_mthp_stat(folio_order(folio), MTHP_STAT_ZSWPOUT);
        goto out_unlock;
    }
    if (!mem_cgroup_zswap_writeback_enabled(folio_memcg(folio))) {
        folio_mark_dirty(folio);
        return AOP_WRITEPAGE_ACTIVATE;
    }

    __swap_writepage(folio, swap_plug);
    return 0;
out_unlock:
    folio_unlock(folio);
    return ret;
}
{% endhighlight %}

<div class="citation"><a href="https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/mm/page_io.c?h=v6.19#n240">swap_writeout()</a> from Linux 6.19</div>

{% endcc %}

If `zswap_store()` returns `true`, the page has been stored in compressed RAM
and never touches the disk. Only if zswap declines (or it isn't enabled) does
the kernel fall back to writing to the backing swap device.

Here's what `zswap_store()` does internally:

{% cc %}

{% highlight c %}
bool zswap_store(struct folio *folio)
{
    /* ... */

    /* Check if we've hit pool size limits */
    if (zswap_check_limits())
        goto put_objcg;

    /* Get the current compression pool */
    pool = zswap_pool_current_get();
    if (!pool)
        goto put_objcg;

    /* Try to compress and store each page in the folio */
    for (index = 0; index < nr_pages; ++index) {
        struct page *page = folio_page(folio, index);
        if (!zswap_store_page(page, objcg, pool))
            goto put_pool;
    }

    ret = true;  /* Success! */

put_pool:
    zswap_pool_put(pool);
put_objcg:
    obj_cgroup_put(objcg);

    /* If we failed because pool was full, queue work to shrink it */
    if (!ret && zswap_pool_reached_full)
        queue_work(shrink_wq, &zswap_shrink_work);
check_old:
    return ret;
}
{% endhighlight %}

<div class="citation"><a href="https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/mm/zswap.c?h=v6.19#n1494">zswap_store()</a> from Linux 6.19</div>

{% endcc %}

You might notice this `queue_work(shrink_wq, &zswap_shrink_work)` business.
What that does is to, since we have just found out that zswap is full, queue a
worker to automatically evict some cold pages to disk. It eventually calls into
[shrink_worker()](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/mm/zswap.c?h=v6.19#n1324),
which handles this reclamation.

This tight integration with the rest of the memory management subsystem, and
the fact that other mm code is aware of the nature of this storage is what sets
zswap significantly apart from zram. zswap acts as a transparent compression
layer *in front of* your SSD swap, not as a separate storage tier, like how
zram does it. When the pool fills up, it automatically triggers the shrinker to
evict cold pages to disk.

## LRU inversion

But wait, Chris, I set a priority on my zram swap device. So isn't that the
same as this "tiered" architecture with zswap?

Unfortunately, this logic is one of the most common ways people hoist
themselves with their own zram shaped petard. The story goes something like
this:

1. A page is ready to be swapped, and goes into `swap_writeout()`.
2. There's no zswap, only zram, so the kernel just looks down the list of swap
   devices to find the highest priority one.
3. zram is configured with the highest swap priority, so it gets chosen as long
   as it has space.

This all sounds fine on paper, right? Sure, and that's exactly why it keeps
catching people out. So what's the catch?

Well, the problem is in how the kernel allocates swap space across multiple
devices. The kernel has a function called `swap_alloc_slow()` which is
responsible for finding the right device and cluster to write to:

{% cc %}

{% highlight c %}
/* Rotate the device and switch to a new cluster */
static void swap_alloc_slow(swp_entry_t *entry, int order)
{
    unsigned long offset;
    struct swap_info_struct *si, *next;

    spin_lock(&swap_avail_lock);
start_over:
    plist_for_each_entry_safe(si, next, &swap_avail_head, avail_list) {
        /* Rotate the device and switch to a new cluster */
        plist_requeue(&si->avail_list, &swap_avail_head);
        spin_unlock(&swap_avail_lock);
        if (get_swap_device_info(si)) {
            offset = cluster_alloc_swap_entry(si, order, SWAP_HAS_CACHE);
            put_swap_device(si);
            if (offset) {
                *entry = swp_entry(si->type, offset);
                return;
            }
            if (order)
                return;
        }

        spin_lock(&swap_avail_lock);
        /* ... continue to next device if this one is full ... */
    }
}
{% endhighlight %}

<div class="citation"><a href="https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/mm/swapfile.c?h=v6.19#n1341">swap_alloc_slow()</a> from Linux 6.19</div>

{% endcc %}

What this code basically says is, higher priority devices get used first. That
sounds fine, right? Of course it does, that's why users [configure it this way
all the
time](https://forum.endeavouros.com/t/zram-vs-zswap-why-choose-one-over-the-other/75980/5).
But such users have unwittingly created a trap that grows more and more likely
with more uptime.

The trap is this: since the swap on the zram device has the highest priority,
the kernel prefers zram for all allocations. When zram fills up, it switches to
the disk based swap for all future allocations.

That means that without intervention, your precious zram gets filled with
whatever pages *happened to be swapped out first*. That is usually completely
inversely correlated with the pages that you actually need *now*.

In a typical desktop session, these pages are usually cold, initialisation-time
data that is evicted early to make room for (say) the browser you just opened.
These cold pages then permanently occupy the fast zram. Meanwhile, as your
session continues and memory pressure persists, the newer, potentially "hotter"
pages (like recent browser tabs you are actively switching between) are forced
to spill over to the lower-priority device: the slow mechanical disk or SSD.

This is what is termed *LRU inversion*: your fastest storage tier is clogged
with the coldest data, with no way to evict it, and that actively forces your
working set onto the slowest storage. In this case, zram isn't just failing to
help here, it is, instead, actively making things worse than having no
compressed swap at all. And even worse, the longer the system has been running,
the more broken things get: warm pages drift to disk, cold pages calcify in
zram, and the gap between what zram is holding and what you actually need keeps
widening. Great!

{% animation %}
{
  "type": "storage-tiers",
  "panels": {
    "zram": "zram (priority) + disk swap",
    "zswap": "zswap + disk swap"
  },
  "fastCap": 4,
  "outcomes": {
    "zram": {"text": "Pages 5 and 6 have to be read from slow disk", "good": false},
    "zswap": {"text": "Pages 5 and 6 can be read from RAM", "good": true}
  },
  "steps": [
    {
      "desc": "System starts. Pages are swapped out over time as memory fills. Page 1 is the first (oldest) page evicted; page 6 will be the most recently evicted.",
      "zram":  {"fast": [],         "slow": []},
      "zswap": {"fast": [],         "slow": []},
      "need": []
    },
    {
      "desc": "Pages 1 and 2 swapped out, this is cold startup data (init processes, early libraries). Both land in the fast tier.",
      "zram":  {"fast": [1, 2],     "slow": []},
      "zswap": {"fast": [1, 2],     "slow": []},
      "need": []
    },
    {
      "desc": "Pages 3 and 4 arrive. The fast tier (4 slots) is now full in both cases.",
      "zram":  {"fast": [1, 2, 3, 4], "slow": []},
      "zswap": {"fast": [1, 2, 3, 4], "slow": []},
      "need": []
    },
    {
      "desc": "Page 5 arrives. zram's fast tier is full so it goes straight to disk. zswap evicts the coldest page (1) to disk and keeps page 5 in fast RAM.",
      "zram":  {"fast": [1, 2, 3, 4], "slow": [5]},
      "zswap": {"fast": [2, 3, 4, 5], "slow": [1]},
      "need": []
    },
    {
      "desc": "Page 6 arrives. zram sends it to disk again. zswap evicts page 2, keeping the freshest data in fast RAM.",
      "zram":  {"fast": [1, 2, 3, 4], "slow": [5, 6]},
      "zswap": {"fast": [3, 4, 5, 6], "slow": [1, 2]},
      "need": []
    },
    {
      "desc": "Memory pressure hits. You switch to browser tabs opened recently that require pages 5 and 6. They need to be faulted back in. Where are they?",
      "zram":  {"fast": [1, 2, 3, 4], "slow": [5, 6]},
      "zswap": {"fast": [3, 4, 5, 6], "slow": [1, 2]},
      "need": [5, 6]
    }
  ]
}
{% endanimation %}

Beyond the placement problem, there is also a real overhead being paid on both
sides. Every page entering zram costs CPU cycles to compress. Every access to a
page still in zram requires a minor fault and decompression back into main
memory before it can be used. You are paying compression and decompression
overhead entirely on data you are not actively using, while the data you do
need grinds through slow disk I/O.

### zram writeback and its limitations

Now, that's where the discussion would end if I was writing this a few years
ago. :-) But since kernel 4.14, zram has writeback support, which is an
attempt to address this problem.

With writeback configured, zram can write back pages that are idle or do not
compress well. This means modern zram setups *can* theoretically implement
tiering, but:

1. It requires manual configuration rather than happening automatically in the
   kernel reclaim path, and
2. It requires you to think about and set up a reasonable method to go about
   the writeback and heuristics.

Maybe that doesn't sound so difficult. Allow me to try to convince you
otherwise.

To achieve similar behaviour to zswap, where incompressible or idle pages are
moved to disk, you must create your own solution. One problem is that you
cannot simply point zram writeback at a swap file or your existing swap
partition. The writeback interface, instead, requires a dedicated, unformatted
block device. With
[`zram-generator`](https://github.com/systemd/zram-generator), that looks
something like this:

{% highlight ini %}
[zram0]
zram-size = ram / 2
writeback-device = /dev/sda4
{% endhighlight %}

Another problem is that you must repartition your disk to create a dedicated
partition for zram backing, or manage loopback devices (which adds overhead).
You also cannot share this space with the system's hibernation swap or other
data easily.

An even bigger hurdle is actually going about the flushes. Even with the device
attached, zram does not write out pages to it automatically, and the kernel has
no internal heuristic to decide when to move data from zram to the backing
device, because zram is not integrated enough into the mm subsystem to achieve
that effectively.

Instead, you must create a systemd timer or a cron job to manually trigger this
flush, and even this is not that easy.

For example, to flush out pages that zram could not compress, it is as simple
as:

    echo huge > /sys/block/zram0/writeback

...but to flush idle or cold data, it is even more complex. Because zram is
agnostic of the fact that it has swap on it, as opposed to any other kind of
data, zram doesn't inherently track LRU age in a way that allows simple
eviction. You first have to tell the kernel to mark pages as idle, and then
tell zram to write them out.

    echo 3600 > /sys/block/zram0/idle # 1h
    echo idle > /sys/block/zram0/writeback

As [Sam](https://samwho.dev/) put it while reviewing this article, it's "the
IKEA of memory management" -- fine when you're assembling a [dombås wardrobe](https://manuall.co.uk/ikea-dombas-wardrobe/),
but it's going to be you that's feeling like a dombås when this comes to bite you in production.

As well as the complexity, zram is architecturally at quite a disadvantage
compared to zswap's native LRU tiering.

For example, in zram, this age check is a one-time event. When you run your
script or timer, it takes a snapshot of the current state. If a page becomes
cold 5 minutes later, it stays in RAM until you run the script again. There's
no connection to the reclaim process or shrinkers, and if memory pressure
suddenly rises, it may be too late to run your script.

Compare that with zswap, where the LRU list is evaluated as part of the normal
memory reclamation lifecycle. As soon as memory pressure rises, the kernel
looks at the live list of pages as part of reclaim and evicts the oldest ones
immediately. The effect in concrete terms is that with zram, a memory spike
that hits between your script running means your application is going to disk
swap at the worst possible moment. By comparison, with zswap, the kernel
responds naturally as the pressure happens.

There is also a granularity problem. With zram, you have to guess a magic
number to perform eviction based on time (like 24 hours). If you guess too
high, you waste RAM. If you guess too low, you flush data that you might have
actually wanted. The system, after all, only does what you say, and without
extensive profiling over time, it is hard to know what to tell it to be
effective.

By comparison, in zswap, there is no magic number, and it dynamically balances
the LRU based on pressure. If you have plenty of RAM and there's no pressure,
it keeps data indefinitely. If you are starving for RAM, it aggressively evicts
the oldest data, whether it's 24 hours old or 24 minutes old. It has
introspection into and the ability to negotiate with the rest of the system,
and thus it can make better decisions.

Ultimately, zram writeback is a workaround, not a solution. It's not so much
that it can't be made to work in some academic sense -- of course it can. The
problem is that all of the nasty edge cases show up at exactly the wrong moment:
mid-spike, when memory pressure is highest and your carefully guessed thresholds
are most likely to be wrong. I would strongly recommend that you do not go about
managing your memory in this way.

## zswap's automatic tiering (and its performance cliffs)

As described above, zswap's tight mm integration gives you all of that for
free, which has the suspicious smell of a free lunch. And for most workloads,
it is indeed somewhat of a free lunch, but there are some catches worth being
aware of.

zswap's tiering mechanism works through two distinct shrinker mechanisms that
are easy to conflate, so it's worth understanding both upfront.

The first -- `zswap_shrinker_count()` (and its companion
`zswap_shrinker_scan()`) -- exist as part of the *dynamic* shrinker. It is
triggered independently by memory reclaimers (like kswapd, direct reclaimers,
and by proactive reclaimers like
[Senpai](https://github.com/facebookincubator/senpai)), not by pool limits. Its
job is to dynamically size the zswap pool based on memory access patterns,
compressibility, and memory pressure, with the goal that you ideally never hit
the static pool limits at all. In practice in production at Meta, hitting the
static pool limit is rare, because this dynamic shrinker keeps things in check
before they get that far. On memory-constrained systems like laptops, you may
see it more.

The *second* shrinker,
[shrink_worker()](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/mm/zswap.c?h=v6.19#n1324),
is the limit-based fallback that only fires when the pool limit is actually
hit. That's where the performance cliff lives, and there's more on that below.

The tricky part is deciding how many pages to evict. Evict too few and the pool
keeps filling, evict too many and you thrash pages back in from disk
immediately after. Here's how `zswap_shrinker_count()` handles that:

{% cc %}

{% highlight c %}
static unsigned long zswap_shrinker_count(
        struct shrinker *shrinker,
        struct shrink_control *sc)
{
    /* zswap shrinker_count basically answers the question of
     * how many pages we should evict from zswap to the
     * backing swap device. */

    struct lruvec *lruvec =
        mem_cgroup_lruvec(sc->memcg, NODE_DATA(sc->nid));

    /* This is how often we had to fetch data from slow disk
     * recently. We track this to avoid thrashing. */
    atomic_long_t *nr_disk_swapins =
        &lruvec->zswap_lruvec_state.nr_disk_swapins;

    /* ... */

    /* Subtract from the lru size the number of pages that
     * were recently swapped in from disk. The idea is that
     * had we protected this many more pages in the zswap
     * LRU from eviction, those disk swapins would not have
     * happened. */
    nr_disk_swapins_cur = atomic_long_read(nr_disk_swapins);
    do {
        if (nr_freeable >= nr_disk_swapins_cur)
            nr_remain = 0;
        else
            nr_remain = nr_disk_swapins_cur - nr_freeable;
    } while (!atomic_long_try_cmpxchg(
        nr_disk_swapins, &nr_disk_swapins_cur, nr_remain));

    nr_freeable -= nr_disk_swapins_cur - nr_remain;
    if (!nr_freeable)
        return 0;

    /* Scale eviction by compression ratio. If compression is
     * good (stored is small), we evict fewer pages to avoid
     * wasting I/O for small gains. */
    return mult_frac(nr_freeable, nr_backing, nr_stored);
}
{% endhighlight %}

<div class="citation"><a href="https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/mm/zswap.c?h=v6.19#n1208">zswap_shrinker_count()</a> from Linux 6.19</div>

{% endcc %}

That is to say, rather than relying on static thresholds or periodic polls,
zswap evicts based on live feedback from the reclaim path, tracking actual disk
swap-in rates and compression ratios. Cold pages drain to the SSD the moment
pressure builds. When memory is truly scarce, the compressed pool is holding
your active working set rather than data you stopped touching hours ago, and
the page faults that matter most stay in fast compressed RAM rather than going
to disk.

But there is, as always, a catch. When zswap hits its `max_pool_percent` limit,
`zswap_check_limits()` causes `zswap_store()` to reject the page and return
false. This wakes up `shrink_worker()` to evict cold pages to disk, but that
work happens *asynchronously* -- the current page is not stored in zswap and
has to go somewhere right now.

What happens next depends on the cgroup's writeback mode:

1. If writeback is enabled for that cgroup (which is the default), the page
   falls through to `__swap_writepage()` and goes directly to disk, bypassing
   the zswap cache entirely.
2. If writeback is disabled for that cgroup, the page cycles back to the active
   list instead, which avoids disk I/O but means the reclaimer must try again
   later.

This means that under heavy memory pressure with writeback enabled, zswap can
start sending pages straight to disk without warning. This creates a
performance cliff where the system suddenly drops swap performance from the
magnitude you might expect from RAM access to the magnitude you might expect
from disk access. This is not worse than zram's behaviour, but it is something
to bear in mind.

## Performance characteristics and trade-offs

Both technologies trade CPU cycles for reduced I/O -- and under normal
operation, their overhead profiles are broadly comparable. The differences that
matter are in the failure modes, and those differences are significant.

### Handling incompressible data

Compressed swap is obviously useful when data compresses well. What's less
obvious is what happens when it doesn't, and the two technologies make opposite
bets here.

zswap can detect incompressible pages during compression and reject them,
sending them straight to disk. This saves both RAM (by not storing poorly
compressed data) and CPU cycles (by not repeatedly trying to compress
incompressible data). You can see how often zswap has done that in the
`reject_compress_poor` counter in `/sys/kernel/debug/zswap/`.

By comparison, zram compresses everything regardless of compression ratio by
default. zram tracks these poorly-compressed pages in its `huge_pages`
statistic, but will happily store even 4KB pages that compress to 3.9KB,
wasting both memory and CPU.

This means zswap usually has better worst-case behaviour for workloads with lots
of incompressible data, though the difference is often negligible in practice
for typical mixed workloads.

The behaviour when zswap rejects an incompressible page has also evolved in
recent kernel versions. By default, as you saw earlier in `swap_writeout()`, a
rejected page falls through to `__swap_writepage()` and goes to disk. But for
workloads where any swap I/O is undesirable, the kernel now supports a
per-cgroup writeback disabled mode (kernel 6.8+). When disabled for a cgroup,
any page rejected by zswap -- whether for incompressibility, pool limits, or
any other reason -- cycles back to the active list rather than going to disk.
This prevents a form of LRU inversion where warm incompressible pages hit disk
ahead of much colder but compressible pages. To enable it:

    echo 0 > /sys/fs/cgroup/<cgroup>/memory.zswap.writeback

There is, however, a downside to writeback-disabled mode: if memory pressure is
high and a cgroup is generating a lot of incompressible data, reclaimers can
end up in a pathological loop -- repeatedly attempting to compress the same
incompressible pages, failing, cycling them back to the active list, and trying
again. With no disk fallback, there is no way to make forward progress, which
can cause serious problems in production. We are working on an approach that would keep
incompressible pages in the zswap pool as-is rather than cycling them,
organised in a per-cgroup LRU so the shrinker can evict them to disk once they
turn cold.


### SSD wear considerations

Another reason some people say to prefer zram over zswap is that they believe
that it [reduces SSD
wear](https://forums.kicksecure.com/t/enable-and-use-zram-instead-for-swap/654/2) -- that is to say, they believe
using it reduces disk I/O.

But this is folly. RAM is finite. If you are filling your RAM with some kind of
data, eventually, when all of your RAM is used, the data needs to go somewhere.

Memory in most cases on both servers and desktops is dominated by two types of
pages. One is anonymous pages, like your program heap and stack data. The other
is file pages, that is, the disk cache. If you use zram without a physical
backing device, you effectively lock all anonymous data in RAM. When memory
pressure hits, the kernel has no choice but to aggressively evict the file
cache to make room.

If those evicted file pages are "dirty" (that is, they contain modified data),
the kernel is forced to write them to the SSD to free up space and make forward
progress. Even if they are "clean" (that is, they are unmodified), they are
dropped, forcing the SSD to read them again the next time they are needed. By
refusing to swap out cold, unused anonymous data to a physical disk via zswap
or swap partition, you strangle the page cache. This forces the system to
constantly flush and re-read active files.

**Using only zram removes disk swap I/O, but it instead simply serves to shift
pressure on to the page cache. Under memory pressure, more file cache may be
dropped (leading to rereads) or written back (if dirty). With disk-backed swap
(or zswap), the system can often evict cold anonymous pages instead, which may
reduce cache churn, and thus reduce I/O. That means that zram can actually
_increase_ total disk I/O if not well managed.**

The real goal is to keep the active working set in RAM -- and disk swap,
used well, helps you do that by giving cold anonymous pages somewhere to go
rather than forcing cold and hot data to compete for the same pool.

We have some concrete numbers to show this in practice. On Instagram, which
runs on Django and is largely memory bound, we ran a test where we moved from
their existing setup (with swap entirely disabled) to a setup with disk swap
and zswap tiering. Django workers accumulate significant cold heap state over
their lifetime, like forked processes with duplicated memory, growing request
caches, Python object overhead, you get the idea. The results were twofold:

- We achieved roughly 5:1 compression. That's a huge benefit for such a memory
  bound workload, and also enables us to consider further stacking workloads.
- Enabling zswap reduced disk writes by up to 25% compared to having no swap at
  all(!).

As you can imagine, as a result of this test, Instagram has been using zswap
for many years now.

Now, some of you may be looking at this wondering how adding swap could ever
reduce disk I/O. How on Earth can it be that ever adding _more_ disk-based
memory offloading would decrease that?

Well, you might think you will never use all of your RAM. But on Linux, we
don't actually leave RAM empty. The kernel follows the philosophy that unused
RAM is wasted RAM, and automatically filling any slack space with the page
cache and other nice-to-have things, like copies of files, libraries, and disk
data to speed up future access.

As part of this, the kernel daemon `kswapd` proactively wakes up to reclaim
memory when free space dips below certain watermarks and works to balance
memory usage. In the ideal case, we want to always have pages available to
immediately allocate without having to sleep for reclaim, so it manages
pressure as a normal state of operation to ensure there is always a buffer for
immediate allocation.

That reclaim has to go somewhere, and with only zram, there's only one place
for it to go: the file cache. With disk-backed swap (or zswap in front of it),
the kernel has a choice -- it can reclaim whichever is colder, whether that's
anonymous pages or file cache, based on recency and access patterns. The I/O
that does happen is deliberate rather than desperate.

Of course, Instagram's workload is particularly favourable for zswap, so take
the exact numbers with a grain of salt. But nonetheless, directionally this
maps for almost all use cases: workloads generally do accumulate cold anonymous
pages over time, and those pages tend to compress well.

Beyond that, zswap also dramatically reduces SSD wear by acting as a
write-reduction filter. It absorbs high-frequency page-out/page-in transients
in RAM, compressing data before it ever touches the disk. Only truly cold data
that survives the cache gets written there. In the Instagram case I mentioned
above, the reason disk writes are reduced by 25% is because the in-memory cache
absorbs the hot write churn that would otherwise have reached the SSD.

Modern SSDs are also capable of typically handling hundreds of terabytes of
writes. Consumer SSDs typically offer 150-600 TB
[TBW](https://www.kingston.com/en/blog/servers-and-data-centers/understanding-ssd-endurance-tbw-dwpd).
In 2026, this whole conversation is largely moot anyway unless you are using
very cheap eMMC storage, and even then zram may not be your best bet.

That said, if swap I/O is genuinely a hard requirement for particular
workloads, zswap's per-cgroup writeback disabled mode (see the above
incompressible data section) lets you completely prevent disk swap I/O for
specific cgroups without giving up zswap's integration with the rest of the
memory management subsystem. You can even do some mixing and matching:
latency-sensitive services can use zswap with writeback disabled, while other
services use the full zswap-then-disk tiering. This is considerably more
flexible than the one-size-fits-all zram approach.

### Performance under memory pressure

Both zswap and zram have similar overheads under normal operation. Where they
diverge sharply is in their failure modes under memory pressure, and
understanding those failure modes is the key to understanding which to use.

With zswap, pressure is handled continuously and proactively. As the pool
fills, the dynamic shrinker (`zswap_shrinker_count`) wakes up and evicts cold
pages to disk ahead of time, tracking disk swap-in rates and compression ratios
to avoid thrashing. In practice, this means the pool limit is rarely hit at
all. On production servers at Meta, it almost never fires -- the dynamic
shrinker keeps things in check long before that. When the limit *is* hit, there
is a performance cliff where pages start bypassing the cache and going directly
to disk. That's not great, but it is a *gradual* degradation: the system slows
down rather than falling off a cliff.

With zram, there is no equivalent process. Nothing is watching the device fill
up and taking action. When it hits capacity, it simply stops accepting pages.
If there is a lower-priority disk swap device, the kernel spills to that, with
all the LRU inversion problems described above. If there is no other device,
the system either hangs while the kernel desperately tries to reclaim anything
it can, or the OOM killer fires. In neither case does the system degrade
gracefully.

The situation can actually be worse still -- in some cases the OOM killer may
not fire at all. In March 2026, Matt Fleming at Cloudflare
[reported](https://lore.kernel.org/r/20260303115358.1323188-1-matt@readmodwrite.com)
20 to 30 minute brownouts on production machines with 377 GiB of RAM and a 377
GiB zram device, with the OOM killer never once triggering. The cause is a
direct consequence of zram's block device architecture:
`should_reclaim_retry()` estimates reclaimable memory by checking how many swap
slots are free. With disk-backed swap, a free slot genuinely means a page can
be written there without consuming more RAM. With zram, a 377 GiB device at 10%
usage reports ~340 GiB of free slots -- but filling them requires physical RAM
the system doesn't have. The estimate is off by orders of magnitude,
`should_reclaim_retry()` keeps returning true, and the kernel spins in direct
reclaim indefinitely. And even when the OOM killer does eventually fire, it is
not the clean escape valve many expect.

You might think: if the system is swapping heavily to disk, responsiveness is
already ruined. I'd rather have the system OOM kill a process than slowly
thrash the user to death. But there is a dangerous nuance here that is often
overlooked -- the kernel OOM killer is not even close to instantaneous.

As I went over in my [SREcon talk](https://www.youtube.com/watch/beefUhRH5lU),
relying on the kernel's built-in OOM killer to save responsiveness is often a
losing battle. The kernel doesn't actually know when it is out of memory in any
direct sense: being "out of memory" means not just that memory is full, but
that there is nothing left to reclaim -- and the only way to determine that is
to attempt the full reclaim cycle and have it fail.

Before the OOM killer is ever invoked, the kernel enters a cycle of aggressive
reclaim:

- It scans LRU lists looking for clean pages to drop.
- It attempts to flush dirty pages to disk.
- It cycles through various memory types trying to free anything.
- It negotiates shrinking with drivers.

We have frequently seen that this process can take seconds or even minutes
for simple production workloads. During this time, your application is
suspended, and the system appears to hang. By the time the OOM killer actually
fires, the user has likely already experienced significant unresponsiveness,
and the system may be locked up to the point that the user can do very little
about it.

The kernel OOM killer is also very imprecise. It uses a heuristic "score" to
decide who to kill -- and if "score" sounds like a weasel word, that's because
it is. It's the kernel admitting it doesn't know who the right victim is either,
and hoping you'll fill the gap with `oom_score_adj`. The practical result is
that it often just kills the largest process, rather than the one that is
actually leaking memory. Consider a system where Chrome holds 80% of RAM and a
background daemon starts leaking: the OOM killer targets Chrome, killing it
stabilises the system, and the daemon is never identified. Next time it leaks,
Chrome dies again. The daemon, for its part, continues to leak.

## zram on Fedora

Why are distributions like Fedora defaulting to zram-only setups on desktops
with fast SSDs? And why not just use zswap?

The answer is that zswap was never actually on the table. Fedora's goal for a
while now has been to [eliminate disk swap
entirely](https://fedoraproject.org/wiki/Changes/SwapOnZRAM), and since zswap
is architecturally a cache *in front of* disk swap, it's simply not a
candidate.

Their reasons for eliminating disk swap aren't entirely about memory
management, and are largely also being driven by other system properties. For
example, when swap evicts pages to disk, private keys, passwords, session
tokens, and browser state end up on a persistent partition. zram sidesteps this
entirely: it lives in RAM, and a reboot wipes it, so there's no risk of
anything getting to disk. Swap encryption can help here too, but it adds
configuration complexity and still requires trusting the key management story,
and ultimately Fedora's goal is to eliminate the surface area, not layer
mitigations on top of it.

Fedora pairs zram with systemd-oomd, which monitors
[PSI](https://facebookmicrosites.github.io/psi/docs/overview) to proactively
kill processes based on policy ahead of time. They also sidestep LRU inversion
by having only one swap device (on zram), and so with no disk swap at all,
there is nothing to invert against.

This setup makes some amount of sense given the constraints they are operating
under, and with the mitigations using `systemd-oomd` that they have in place.
With their setup, a desktop user under heavy memory pressure is probably
already seeing low responsiveness, and a userspace OOM daemon terminating the
problematic process cleanly is often better than waiting for the system to
thrash through disk swap for minutes.

But, and this is important, this only works with a userspace OOM daemon running
and configured, and no disk swap device whatsoever. Without systemd-oomd, you
get the hard limit without the clean kill, and the system will hang just as
badly or worse.

So suffice to say that this is almost certainly not the optimal setup purely
for memory management, and zswap's tighter mm integration and LRU tiering offer
real advantages that zram doesn't match. But memory efficiency wasn't the only
thing Fedora was optimising for, and several of their constraints had nothing
to do with memory management at all. Within those constraints, the decision is
coherent: optimality is always relative to what you're trying to achieve (and
that point goes to you too, dear reader -- you know better than me what you are
trying to do). That said, I would be surprised if over the coming years there
is not some movement towards zswap there too once zswap gains the upcoming
disk-free mode, especially given that kernel developers are increasingly moving
away from supporting zram (more on that below).

## If I use zram, how should I size the device?

In the naive case, with zram, you have to guess the device size upfront. If you
guess too small, you waste potential. If you go too large you risk OOM killing,
or cause unnecessary minor faults.

So how does Fedora size it? Well, they [size it up to 100% of your
RAM](https://fedoraproject.org/wiki/Changes/Scale_ZRAM_to_full_memory_size).
Job's a goodun.

...okay, maybe that does require a little more explanation. :-)

Fedora takes an aggressive approach here. They size the zram device to 100% of
your physical RAM, capped at 8GB. You may be wondering how that makes any sense
at all -- how can one have a swap device that's potentially the entire size of
one's RAM? And surely to read a page from zram, I have to decompress it into
main RAM, right? If zram is full, where does it even put the decompressed
page? What is this madness?!

Fedora solves this with a bit of educated gambling. First, zram is thin
provisioned. Until pages are actually faulted, there's no memory use. So a zram
device sized to 100% with nothing in it occupies no space except for the space
used for bookkeeping.

In addition to that, they are betting that your data compresses well -- say,
3:1. So then, a 100% sized zram device will only physically occupy one third of
RAM, leaving 66% free for the OS and decompression buffers.

Then they use systemd-oomd to watch memory pressure. If it sees zram physically
filling up RAM, it kills something based on policy before you hit the deadlock
wall where there wouldn't be enough space to decompress.

## How to decide which to use

If you are in doubt, I strongly recommend you use zswap with disk-backed swap.
It is much more tightly integrated with the rest of the memory management
subsystem than zram, has much better heuristics around reclaim and eviction,
handles incompressible data much better, and degrades gracefully under
pressure. It also handles hibernation transparently. Disk based swap still has
[significant upsides in many
cases](https://chrisdown.name/2018/01/02/in-defence-of-swap.html), even if you
have a lot of RAM.

The cases where zram makes sense are more nuanced. In embedded systems, zram is
extremely simple and self-contained. When there is no disk at all, it is the
obvious choice, and in those environments the predictability of a hard limit is
often a feature rather than a bug. Another case is when you are deliberately
going entirely disk-free by design, like in Fedora's case.

Android is the most prominent example of the diskless approach: billions of
devices run zram with no disk swap at all, paired with a userspace kill daemon
([lmkd](https://android.googlesource.com/platform/system/memory/lmkd/)). That combination completely sidesteps LRU inversion, because there is
no disk swap tier to invert against. But Android's zram works because it has
been extensively tuned for phone hardware and phone workloads -- and as
described above, even things as basic as readahead defaults work against you
out of the box, and those are just the knobs that are visible. Those
assumptions don't travel, and neither does Android's tuning.

Servers are another place where zram becomes an especially hard sell. Aside
from the way in which zram (doesn't) degrade, zram's memory usage is basically
opaque to the kernel and is not charged to any cgroup. The kernel has no
visibility into how much memory zram is consuming on behalf of a given cgroup,
which can break resource isolation and pressure signals between services. This
gap alone has been a hard blocker for zram adoption at a number of
organisations, including Meta, that run containerised or isolated workloads.

Even the embedded and diskless cases are narrowing. Many of us working in this
area share similar views on where things are heading. Christoph, who maintains
the block layer, has been direct:

> No way. Stop adding hacks to the block layer just because you're abusing a
> block driver for compressed swap. Please everyone direct their energy to
> pluggable zswap backends and backing-store-less zswap now instead of making
> the zram mess even worse.

<div class="citation"><a href="https://lore.kernel.org/r/aabrv_xrsKPx9jZf@infradead.org">Christoph Hellwig</a>, block layer maintainer</div>

Johannes, one of the memory management maintainers, agreed:

> Compression is a *memory* consumer. A big one. And with swap it sits in the
> reclaim path. So now you have to solve intricate MM problems with the block
> layer in between. [...] We should try to make zswap the single compressed
> swap implementation. It would simplify things dramatically for kernel
> developers working on MM and the swap subsystem. It would make things better
> for users too.

<div class="citation"><a href="https://lore.kernel.org/r/aacTW_FEp6c1coDf@cmpxchg.org">Johannes Weiner</a>, MM maintainer</div>

The "pluggable zswap backends and backing-store-less zswap" Christoph mentions
refers to active work to allow zswap to operate without any disk swap device at
all -- which would close the remaining use case for zram even in diskless
setups. For what it's worth, zram is already 2.6× the lines of code of zswap.
The direction of travel is fairly clear.

In practice, across the services we've deployed zswap on at scale, it has
consistently reduced OOMs, cut disk write pressure, and done so without any
manual intervention. zram is a completely manual part of the memory management subsystem -- you
take on the responsibility of managing it correctly, or you bear the
consequences -- whereas zswap is managed by the kernel itself, with all the
live feedback, reclaim integration, and automatic tiering that entails. For the
vast majority of Linux systems, you really want the kernel doing that work with
zswap.

## Migrating from zram to zswap

If you're currently on a zram-only setup (such as Fedora's default) and want
to switch, order of operations matters. Before you `swapoff` the zram device,
ensure disk swap is already active. If zram is your only swap and it contains
live pages, `swapoff` needs somewhere to put them -- without another device, it
will either fail or attempt to bring everything back into RAM at once.

If you don't already have a disk swap device, create and activate a swap file
first:

    fallocate -l 4G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile

Add `/swapfile swap swap defaults 0 0` to `/etc/fstab` to persist it. Then
enable zswap if it isn't already (see the sidenote earlier in this post), and
disable zram live:

    swapoff /dev/zram0

The kernel migrates any live pages to disk swap for you. To stop zram coming
back on the next boot, on Fedora remove or empty
`/etc/systemd/zram-generator.conf`.

Many thanks to [Nhat](https://github.com/nhatsmrt),
[Javier](https://hondu.co/), [Sam](https://samwho.dev/),
[Johannes](https://github.com/hnaz), and
[Andreas](https://github.com/andreasbackx) for their feedback on this post.
