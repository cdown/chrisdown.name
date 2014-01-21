---
layout: post
title: TRIM on the Corsair Force CSSD-F120GB2
excerpt: How to get around TRIM issues on Linux with the CSSD-F120GB2.
---

I experienced a few problems with TRIM on this drive:

- ext4's "discard" option is (very) slow on inode deletes on this drive;
- Using `fstrim` results in "FITRIM ioctl failed: Input/output error", and a
  warning in the kernel message buffer that DATA SET MANAGEMENT failed (this
  [seems to be known about][cforum], although the answers from support are not
  helpful).

I initially thought that this might be a problem with the drive, but SMART
looks fine, and it seems to operate normally otherwise.

I ended up using wiper.sh in a cron job. On Arch Linux, that's bundled with the
hdparm package. After installing it, you can trim twice every month by doing
something like the following:

    PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

    0 6 1,15 * * root wiper.sh --commit --please-prematurely-wear-out-my-ssd [filesystem]

The amusingly named `--please-prematurely-wear-out-my-ssd` is required to skip
the prompt that usually appears when using `--commit`. I assume it exists to
stop people from trimming with stupid frequency.

[cforum]: http://forum.corsair.com/v3/showthread.php?t=88056
