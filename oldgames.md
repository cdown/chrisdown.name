---
layout: default
title: "Old game miscellania"
---

I play a lot of "old" games that need some poking to get them to work properly.
This is a place to record what's needed.

Most of these are either with my 750M (gaming laptop) or GTX 1070 (gaming
desktop).

# Splinter Cell

Splinter Cell autodetects that the 750M supports projected textures for dynamic
lighting, but this is an old Radeon-only technology, the autodetection is just
naive. This results in dynamic shadows/lights not being rendered at all. The
fix is to explicitly tell SC to use shadow buffers instead, which is supported
on Nvidia cards. Set this in the `D3DDrv.D3DRenderDevice` section in
`system/SplinterCell.ini`:

    ForceShadowMode=0

Possible values are:

- 0: Shadow projector (Radeon)
- 1: Shadow buffer (non-Radeon)
- default: autodetect (I haven't dug into how this detection actually works)
