---
layout: post
title: How to remove a custom video mode in VirtualBox
---

There are quite a few posts around about how to set a custom video mode in
VirtualBox, but I didn't find any about how to remove it. Without removing it,
the "auto-resize guest display" option doesn't appear to work (in my case, the
guest always uses the custom video mode instead of the current display size).

First, I went looking for the properties that set the resolution. I found the
following on my host:

    $ VBoxManage guestproperty enumerate ns001.cdown.local | grep 2048
    Name: /VirtualBox/GuestAdd/Vbgl/Video/0, value: 2048x1280x0,0x0,1, timestamp: 1424291930786192000, flags: 
    Name: /VirtualBox/GuestAdd/Vbgl/Video/SavedMode, value: 2048x1280x0, timestamp: 1424291930786592000, flags:

I looked at a host without a custom resolution to see what this usually looks
like:

    $ VBoxManage guestproperty enumerate chef.cdown.local | grep Video
    Name: /VirtualBox/GuestAdd/Vbgl/Video/SavedMode, value: 640x480x32, timestamp: 1424177936866662000, flags

This led me to believe that `.../Video/[id]` is where custom modes are
stored, since it was not present on a host without any video mode hints.

Then I went to delete the key, only to find that `VBoxManage guestproperty` has
no `delete` option:

    $ VBoxManage guestproperty
    Usage:

    VBoxManage guestproperty    get <uuid|vmname>
                                <property> [--verbose]

    VBoxManage guestproperty    set <uuid|vmname>
                                <property> [<value> [--flags <flags>]]

    VBoxManage guestproperty    delete|unset <uuid|vmname>
                                <property>

    VBoxManage guestproperty    enumerate <uuid|vmname>
                                [--patterns <patterns>]

    VBoxManage guestproperty    wait <uuid|vmname> <patterns>
                                [--timeout <msec>] [--fail-on-timeout]

As it turns out, to delete a key you [just set it to a null value][doc] (go
figure):

> `set <vm> <property> [<value> [--flags <flags>]]`:
>
> This allows you to set a guest property by specifying the key and value. If
> `<value>` is omitted, the property is deleted.

As such, setting the key to a null value will now delete the custom video mode
hint, and get automatic resizing working again.

    $ VBoxManage guestproperty set ns001.cdown.local /VirtualBox/GuestAdd/Vbgl/Video/0
    $ VBoxManage guestproperty enumerate ns001.cdown.local | grep 2048
    Name: /VirtualBox/GuestAdd/Vbgl/Video/SavedMode, value: 2048x1280x0, timestamp: 1424291930786592000, flags:

[doc]: https://www.virtualbox.org/manual/ch08.html#vboxmanage-guestproperty
