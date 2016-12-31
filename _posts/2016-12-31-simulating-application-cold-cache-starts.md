---
layout: post
title: Simulating service cold cache starts with eBPF/strace + oflag=nocache
---

Occasionally I run into problems with cold cache startups for services.
Debugging these issues can be kind of complicated since these issues can be
sporadic, since page cache lifetime and the general environment (for example,
racy things like if a file was already put into cache by another process during
startup) can change a lot between startups.

The traditional technique to deal with this was to drop all your caches (with
`echo 3 > /proc/sys/vm/drop_caches`), which is... suboptimal at best. I don't
know about you, but I don't want my entire environment to slow to a crawl on
I/O just because I want to run this one experiment.

dd has a nice oflag available since 8.11 called "nocache". This option expunges
the pages present for the specified file from the page cache. For example:

    dd of=file oflag=nocache conv=notrunc,fdatasync count=0

You can also drop just part of a file from the cache:

    dd if=file iflag=nocache skip=10 count=10 of=/dev/null

Now all that remains is to get the files to drop caches on, which is trivially
achieved by processing output from [BCC's
opensnoop](https://github.com/iovisor/bcc/blob/master/tools/opensnoop.py) (note
that opensnoop's PID filtering is currently TID based rather than TGID based):

    % bash -c 'ls ~cdown > /dev/null' & pid=$!; { kill -STOP "$pid"; sleep 5; kill -CONT "$pid"; } &
    % opensnoop -p "$pid" | awk '{ print $NF }' | sort -u | tee todrop
    ^C
    /etc/ld.so.cache
    /etc/nsswitch.conf
    /etc/passwd
    /usr/lib/gconv/gconv-modules
    /usr/lib/libc.so.6
    /usr/lib/libcap.so.2
    /usr/lib/libdl.so.2
    /usr/lib/libncursesw.so.6
    /usr/lib/libnsl.so.1
    /usr/lib/libnss_compat.so.2
    /usr/lib/libnss_files.so.2
    /usr/lib/libnss_nis.so.2
    /usr/lib/libreadline.so.7
    /usr/lib/locale/locale-archive

You can also do this with strace + perl, but be aware that if your
application's startup flow is latency dependent, system call tracing using
ptrace is really, really slow and so may bias your results (whereas eBPF uses
the `k{,ret}probe` interface and is generally so fast as to be unnoticeable):

    % strace -f -e open -o startfiles bash -c 'ls ~cdown > /dev/null'
    % perl -F\" -ane '(-f $F[1]) and print "$F[1]\n";' startfiles | sort -u | tee todrop
    /etc/ld.so.cache
    /etc/nsswitch.conf
    /etc/passwd
    /usr/lib/gconv/gconv-modules
    /usr/lib/libc.so.6
    /usr/lib/libcap.so.2
    /usr/lib/libdl.so.2
    /usr/lib/libncursesw.so.6
    /usr/lib/libnsl.so.1
    /usr/lib/libnss_compat.so.2
    /usr/lib/libnss_files.so.2
    /usr/lib/libnss_nis.so.2
    /usr/lib/libreadline.so.7
    /usr/lib/locale/locale-archive

Now you can easily drop those files using `xargs` or `parallel`:

    % parallel dd of={} oflag=nocache conv=notrunc,fdatasync count=0 < todrop

After this you can run your application and watch its cold page cache start
behaviour with your normal debugging tools (I mostly use I/O and network
related [eBPF tools from the IO Visor
project](https://github.com/iovisor/bcc/blob/master/README.md) when debugging
startup latency issues).

If you want to verify how much of one of the files is being cached as any
point, you can use [fincore](http://pages.cs.wisc.edu/~plonka/fincore/):

    % fincore -summary /usr/lib/locale/locale-archive
    page size: 4096 bytes
    /usr/lib/locale/locale-archive: 151 incore pages: 0 1 2 3 [...]
    151 pages, 604.0 kbytes in core for 1 file; 151.00 pages, 604.0 kbytes per file.
    % dd of=/usr/lib/locale/locale-archive oflag=nocache conv=notrunc,fdatasync count=0
    0+0 records in
    0+0 records out
    0 bytes copied, 3.5556e-05 s, 0.0 kB/s
    % fincore -summary /usr/lib/locale/locale-archive
    page size: 4096 bytes
    /usr/lib/locale/locale-archive: no incore pages.
    0 pages, 0.0  bytes in core for 1 file; 0.00 pages, 0.0  bytes per file.
