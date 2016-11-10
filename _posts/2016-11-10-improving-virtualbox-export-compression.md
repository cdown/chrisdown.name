---
layout: post
title: Improving VirtualBox VMDK disk size
---

## Zeroing out free space

Unix is easy, just `cat /dev/zero > foo; rm foo`, where "foo" is any file on the
filesystem you want to zero out free space on.

On Windows, you can use
[sdelete](https://technet.microsoft.com/en-us/sysinternals/bb897443.aspx) with
the `-c` argument.

## Compaction

This shoudn't matter from a compression perspective, but it does make the image
smaller on disk:

    vboxmanage modifyhd machine-disk1.vmdk --compact

## Compression

When exporting images from VirtualBox, whether from the command line using
`vboxmanage export` or from the GUI, you don't get any control over the
compression of the disk image. Trying to compress the OVA further by itself
won't yield very good results because the compression used hinders further
compression (more on that later).

Here's how an OVA file looks internally:

    % tar tf machine.ova
    machine.ovf
    machine-disk1.vmdk

The VMDK image is compressed interally using
[DEFLATE](https://en.wikipedia.org/wiki/DEFLATE), see [the document on the VMDK
disk
format](https://www.vmware.com/support/developer/vddk/vmdk_50_technote.pdf) for
more information on how this is implemented. As mentioned earlier, this
compression hinders further compression, so to improve it, we need to actually
*decompress* the image first, counterintuitively.

Here's an example of how DEFLATE vs non-DEFLATE performs when succeeded by
(say), [zstd](http://facebook.github.io/zstd/) with the [complete works of
Shakespeare](http://www.gutenberg.org/ebooks/100):

    % gzip -k -9 shakespeare.txt
    % zstd -q -19 shakespeare.txt.gz
    % zstd -q -19 shakespeare.txt
    % du *
    5460 shakespeare.txt
    1976 shakespeare.txt.gz
    1976 shakespeare.txt.gz.zst
    1548 shakespeare.txt.zst

Notice that DEFLATE renders further compression basically useless. This is why
we need to decompress first.

To decompress this VMDK image, you can use `vboxmanage clonehd`, like so
(`clonehd` does not use compression by default):

    % tar xf machine.ova
    % vboxmanage clonehd machine-disk1{,-decompressed}.vmdk --format VMDK

You can now see the difference in disk size:

    % du -h machine-disk1*.vmdk
    16G machine-disk1.vmdk
    26G machine-disk1-decompressed.vmdk

You can now compress with zstd, achieving a far higher level of compression (in
my case, at ~40% compression ratio instead of ~60%.

    % zstd -q -19 machine-disk1-decompressed.vmdk
    % du -h machine-disk1*.vmdk
    16G machine-disk1.vmdk
    26G machine-disk1-decompressed.vmdk
    12G machine-disk1-decompressed.vmdk.zst
