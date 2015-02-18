---
layout: post
title: Wireless not working in Ubuntu 10.04 on the Lenovo Ideapad S12
---

Module autodetection on the S12 is generally pretty good with Ubuntu, except
the brand ACPI module seems to get misselected, which causes problems with the
wireless being disabled each boot.

Don’t worry if `rmmod` says the modules aren't loaded, they will only be
blacklisted if they are already loaded.

First, unload acer_wmi and blacklist it:

    rmmod acer_wmi && echo "blacklist acer_wmi" >> /etc/modprobe.d/blacklist.conf

If that doesn't fix the wireless, you can also try blacklisting alternate
drivers in favour of the STA driver:

    rmmod b43 && echo "blacklist b43" >> /etc/modprobe.d/blacklist.conf
    rmmod ssb && echo "blacklist ssb" >> /etc/modprobe.d/blacklist.conf
