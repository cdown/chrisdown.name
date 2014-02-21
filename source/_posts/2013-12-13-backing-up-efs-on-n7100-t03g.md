---
layout: post
title: Backing up EFS and modem on the N7100/t03g
description: How to back up EFS and modem on the N7100/t03g
---

- Reboot into recovery (you can do this with superuser while Android is
  running, but the filesystem will be dirty, so I don't recommend it);
- The EFS partition on my Note 2 is at /dev/block/mmcblk0p3, and the modem is
  at /dev/block/mmcblk0p10, so do something like the following (annoyingly, it
  seems that trying to just redirect the output of adb shell to the local
  machine results in a corrupted file, so we need to copy locally on the phone
  and then pull it):

<!-- -->

    adb shell dd if=/dev/block/mmcblk0p3 of=/sdcard/efs.img
    adb shell dd if=/dev/block/mmcblk0p10 of=/sdcard/modem.img
    adb pull /sdcard/efs.img
    adb pull /sdcard/modem.img

- Make a copy of this image that we can test with (say, `efs.img.verify`);
- Verify the EFS image is correct (it should look something like what you see
  below):

<!-- -->

    $ cp efs.img{,.verify}
    $ file efs.img.verify
    efs.img.verify: Linux rev 1.0 ext4 filesystem data (extents) (large files)
    $ sudo mount efs.img.verify /mnt/efs
    $ ls -la /mnt/efs
    total 5188
    drwxrwx--x  8  1001 chris    4096 Jan  1  2012 .
    drwxr-xr-x 12 root  root     4096 Dec 13 03:09 ..
    -rw-rw-r--  1  1001 sudo      152 Dec 11  2012 00000000.authtokcont
    drwxrwxr-x  2  1001 chris    4096 Dec 11  2012 bluetooth
    drwxrwxr-x  3  1019 chris    4096 Jan  1  2012 drm
    drwxrwxr-x  2 chris chris    4096 Mar  5  2013 FactoryApp
    drwxrwxr-x  5 root  root     4096 Jan  1  2012 .files
    -rw-------  1 chris chris      12 Dec 11  2012 gyro_cal_data
    -rw-r--r--  1  1001 sudo     1100 Jan  1  2012 h2k.dat
    drwxrwxr-x  2  1001 chris    4096 Jan  1  2012 imei
    -rwx------  1  1001 sudo  1048576 Jun 18 16:13 .nv_core.bak
    -rwx------  1  1001 sudo       32 Jun 18 16:13 .nv_core.bak.md5
    -rwx------  1  1001 sudo  2097152 Jun 18 16:13 .nv_data.bak
    -rwx------  1  1001 sudo       32 Jun 18 16:13 .nv_data.bak.md5
    -rwx------  1  1001 sudo  2097152 Dec 13 01:59 nv_data.bin
    -rwx------  1  1001 sudo       32 Dec 13 01:59 nv_data.bin.md5
    -rw-------  1  1001 sudo     1218 Jun 18 16:13 nv.log
    -rw-------  1  1001 sudo        1 Dec 11  2012 .nv_state
    drwxrwxr-x  2  1001 chris    4096 Jan  1  2012 wifi
    -rw-r--r--  1  1001 sudo      220 Dec 11  2012 wv.keys

- Back up the unmounted image (if you followed the instructions above, it's
  just called `efs.img`). I suggest you `gzip -9` it, it will reduce in size
  dramatically;
- Verify the modem image by looking at `strings` -- you'll see a ton of
  embedded strings that quite obviously reference modem functionality.

To restore them, just do the inverse, writing to the same block devices.
