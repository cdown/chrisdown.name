---
layout: post
title: Finding out why a package was held back with apt
description:
    "The default error message is not very helpful, but you can get debug
    output."
---

I recently encountered some issues on a QA server where a package was being
held back, accompanied by this extremely unilluminating error message:

    # apt-get dist-upgrade
    Reading package lists... Done
    Building dependency tree
    Reading state information... Done
    Calculating upgrade... Done
    The following packages have been kept back:
      xxx

Thankfully in `man apt.conf` there is a useful note:

> Debug::pkgProblemResolver enables output about the decisions made by
> dist-upgrade, upgrade, install, remove, purge.

This is actually extremely useful and produced great output (you would hope
that this is noted in bright flashing lights somewhere rather than just being a
tiny footnote in `man apt.conf`, but eh, whatever).

    # apt-get -o Debug::pkgProblemResolver=yes dist-upgrade
    Reading package lists... Done
    Building dependency tree
    Reading state information... Done
    Calculating upgrade... Starting
    Starting 2
    Investigating (0) xxx [ amd64 ] < 20140204021317 -> 20140210014106 > ( misc )
    Broken xxx:amd64 Depends on yyy [ amd64 ] < none > ( none )
     Try to Re-Instate (1) xxx:amd64
    Done
    Done
    The following packages have been kept back:
      xxx
    0 upgraded, 0 newly installed, 0 to remove and 1 not upgraded.
