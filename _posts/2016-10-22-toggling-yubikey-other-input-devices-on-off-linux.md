---
layout: post
title: Toggling Yubikey (and other input devices) on/off on a timeout
---

Link: <https://github.com/cdown/xinput-toggle>

I wrote a tool last night to toggle attached Yubikeys on/off for Linux (well,
X11) users. Previously it hadn't been a problem on my T460s, but I'm now
temporarily using an X1 Carbon and the place I have to put the Yubikey is super
awkward and ends up getting touched all the time. This tool ended up becoming a
utility for generic xinput device on/off toggling and manipulation since most
of the code applies to any device, not just Yubikeys.

The main benefit over using xinput directly is the timeout feature (available
with -t), which will only enable the Yubikey for a specified period of time.
This means you can keep your Yubikey off, only switching it on when you really
need it.

It has no dependencies except for what you probably already have: the xinput
command line utility, and bash 4.0+. It can also send notifications when it
takes actions on the device if you have notify-send installed.

My suggested usage is to disable the Yubikey in your X startup files, and then
have a binding in your window manager/desktop environment to enable it for 10
seconds, and then disable it again. That way it will only turn be able to send
input when you explicitly let it.

For my config, that means adding the following to .xinitrc to disable the
Yubikey at first:

    xinput-toggle -r yubikey -d

You then can add a binding in your window manager (or make a shell alias) to
run the following to enable it for 10 seconds on press (-n is optional, it
sends a notification on enable/disable with notify-send):


    xinput-toggle -r yubikey -n -e -t 10

This is already packaged in Arch Linux's AUR as
[xinput-toggle](https://aur.archlinux.org/packages/xinput-toggle/). Let me know
if you find any bugs or have any feature requests. :-)
