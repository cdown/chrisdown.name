---
layout: post
title: VirtualBox modules not loading in Arch Linux after upgrade to Linux 4.4.3
---

I just saw this on two of my machines after upgrading to 4.4.3. Symptoms
include:

    % systemctl --state=failed
      UNIT                         LOAD   ACTIVE SUB    DESCRIPTION
    * systemd-modules-load.service loaded failed failed Load Kernel Modules

and (replace "vboxvideo" with "vboxsf" or "vboxguest" as needed)

    % modprobe vboxvideo
    modprobe: ERROR: could not insert 'vboxvideo': Exec format error

Some posts on the Arch forums suggest downgrading the kernel back down to
4.4.1. While that *might* work for a time, you'll be running a partial upgrade
that could break at any time when others upgrade their modules for 4.4.3.

Instead, you should rebuild [virtualbox-guest-modules][] &mdash; or more
specifically its parent package, [virtualbox-modules][] &mdash; from [ABS][].
Here's how to do it.

[virtualbox-guest-modules]: https://www.archlinux.org/packages/community/x86_64/virtualbox-guest-modules/
[virtualbox-modules]: https://www.archlinux.org/packages/community/x86_64/virtualbox-modules/
[ABS]: https://www.archlinux.org/packages/community/x86_64/virtualbox-modules/

1. Enter your root password at the emergency mode prompt to enter a root shell
2. Get a network connection. Since the system didn't start up properly,
   systemctl's process management functionality just results in permission
   errors ("error getting authority"). You can call dhcpcd directly to get an
   IP address with `dhcpcd <interface>`.
3. Install the `abs` package if you don't already have it.
4. Run `abs community/virtualbox-modules` as root to sync the package source
   from the upstream ABS tree.
5. Change to your normal user with `sudo -i -u <user>`.
6. Copy the package ABS downloaded to a new directory (to keep ABS clean) by
   doing `mkdir ~/abs && cp -a /var/abs/community/virtualbox-modules ~/abs/` or
   similar.
7. Install deps for the package, build it, and then install the package. This
   can be done with `makepkg -si` inside the new `~/abs/virtualbox-modules`
   directory. Side note: `makepkg` used to have a `--pkg` option to indicate
   you only wanted a subset of packages from a split package, but it seems to
   have gone missing... oh well.
8. Reboot. Everything should be golden now!
