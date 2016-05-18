---
layout: post
title: Arch Linux on the T460s — first thoughts
---

![My T460s](/images/blog/t460s-first-thoughts/t460s.jpg)

I've been running Arch on my T460s for the past couple of days now. Here are
some thoughts about the experience, some specific to Arch, some more general.

## The good

- The hardware generally just works. The Synaptics X driver
  (`xf86-input-synaptics`) is required if you don't want totally bizarre
  trackpad behaviour like this:

{% youtube VPUbIuN-Gf0 %}

- I haven't noticed any problems with any lacking hardware support so far.
  Allegedly the fingerprint reader is not supported by [fprint][] yet, but I
  don't have much use for it, so no biggie.  Even the touchscreen works out the
  box (with evdev)!
- This machine is really light, almost as light as the X1 Carbon. The extra
  grams seem worth it for the potential hardware upgrades.

## The bad

- This screen is not great. Even after cranking it up to the max
  (`echo 852 > /sys/class/backlight/intel_backlight/brightness`),
  it's nowhere near as bright as I would have hoped, and the colours seem
  shifted towards red.
- As far as I can tell, the media keys don't do anything at all in Linux.
  Right now I'm just binding the keysyms manually, but hopefully there will be
  a WMI module to fix this in a more reasonable way soon.

## The ugly

- I get kernel panics when connecting an external monitor over mini DisplayPort
  sometimes. Apparently this is fixed in kernel 4.6 (I'm still on 4.5.4, but
  may try compiling it later today and seeing if it helps).
- Suspending to disk or to RAM is really iffy. Half the time I come back and
  the system decides it didn't go into S3/S4 at all, and instead wants to
  reboot. :-(

[fprint]: https://www.freedesktop.org/wiki/Software/fprint/
