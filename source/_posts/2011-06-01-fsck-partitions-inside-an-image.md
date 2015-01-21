---
layout: post
title: Running fsck on filesystems inside a partitioned image
---

The offset of the partition on the raw image needs to be found. You can use
fdisk, parted, or a variety of other tools for this.

    # parted seagate-2011-06-02.img
    GNU Parted 2.4
    Using /media/exthd2/seagate-2011-06-02.img
    Welcome to GNU Parted! Type 'help' to view a list of commands.
    (parted) unit
    Unit?  [compact]? B
    (parted) print
    Model:  (file)
    Disk /media/exthd2/seagate-2011-06-02.img: 500107862016B
    Sector size (logical/physical): 512B/512B
    Partition Table: msdos

    Number  Start     End            Size           Type     File system  Flags
     1      1048576B  500107862015B  500106813440B  primary  ext2

    (parted) q

1048576 bytes (1 MiB) is our offset. Now, let’s set up the loop device that we
will fsck.

    # losetup -o 1048576 /dev/loop0 /media/exthd2/seagate-2011-06-02.img

Now you can fsck the loopback device.

    # fsck [...] /dev/loop0

[ddrescue]: http://www.gnu.org/software/ddrescue/ddrescue.html
