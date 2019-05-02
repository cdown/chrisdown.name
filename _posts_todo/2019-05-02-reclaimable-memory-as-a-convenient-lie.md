---
layout: post
title: "Reclaimable memory as a convenient lie"
---

- Cache/buffers/etc are often considered trivially evictable, but it's not
  always true
    - flush rate to backing storage for dirtied pages
    - hot cache/bufs which simply must remain in memory to maintain performance
        - refaulting
        - https://fb.workplace.com/groups/linux.fbk/permalink/2418106804888815/?comment_id=2418574291508733&comment_tracking=%7B%22tn%22%3A%22R%22%7D
        - musical chairs/ponzi scheme
        - Applications can mlock page cache pages, and prevent them from being evicted, but those pages will get moved off the inactive file and active file lists over time
    - mlocked cache pages
    - dividing workloads into RSS being critical and cache being non-critical is not usually reasonable
        - both in that rss sometimes isn't critical, and cache sometimes is...
        - point towards swap note about increasing memory density
- Slab reclaimable/unreclaimable
    - the question is "when?"
    - cgroup rmdir case -- this memory is reclaimable *sometimes*
    - "reclaimable" bit is human curated, and sometimes it's just bullshit.
        - even when it's not, it's often more nuanced.
- Predicting availability of memory for future needs is mostly a fools errand
    - You can make some kinds of estimations, MemAvailable, for example
        - Go a bit into MemAvailable background and limitations
    - however in reality, how much one can really take back from the system is unknowable until it's done
    - even then, it's possible to reclaim too much, and end up with increased memory, i/o, or cpu (due to scan) pressure
- Actual prediction of workload memory size
    - Brief bit about PSI/Senpai w/ link to Johannes' note
