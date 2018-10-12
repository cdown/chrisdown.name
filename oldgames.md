---
layout: default
title: "Old game miscellania"
---

I play a lot of "old" games that need some poking to get them to work properly.
This is a place to record what's needed.

Most of these are either with my 750M (gaming laptop) or GTX 1070 (gaming
desktop).

# Splinter Cell

## Dynamic lighting method autodetection bug

Splinter Cell autodetects that the 750M supports projected textures for dynamic
lighting (eg. spotlights/flashlights), but this is an old Radeon-only
technology, the autodetection is just naive. This results in dynamic
shadows/lights not being rendered at all. The fix is to explicitly tell SC to
use shadow buffers instead, which is supported on Nvidia cards. Set this in the
`D3DDrv.D3DRenderDevice` section in `system/SplinterCell.ini`:

    ForceShadowMode=0

Possible values are:

- 0: Shadow projector (Radeon)
- 1: Shadow buffer (non-Radeon)
- default: autodetect (I haven't dug into how this detection actually works)

## Bonus levels

Someone kindly provided the bonus levels not in the Steam version
[here](https://steamcommunity.com/sharedfiles/filedetails/?id=464988984). Be
warned: they are unpolished and not very interesting.

## FOV changes

I don't recommend doing any changes to DesiredFOV/DefaultFOV (and thus default
4:3 res), as it causes overlaid interactions to become misaligned (eg.
keypads).

## Graphics tweaks

High in game settings doesn't set some of these, especially 32-bit textures
look a lot better.

In SplinterCell.ini this can be replaced verbatim:

```
[D3DDrv.D3DRenderDevice]
Translucency=True
VolumetricLighting=True
ShinySurfaces=True
HighDetailActors=True
UsePrecaching=True
UseMipmapping=True
UseTrilinear=True
UseMultitexture=True
UsePageFlipping=True
UseFullscreen=False
UseGammaCorrection=True
DetailTextures=True
UseTripleBuffering=False
UsePrecache=True
Use32BitTextures=True
HardwareSkinning=False
AdapterNumber=-1
ReduceMouseLag=False
ForceShadowMode=0
EmulateGF2Mode=0
FullScreenVideo=True
UseVsync=False
```

In SplinterCellUser.ini, these settings aren't set by "High":

```
ShadowLevel=2
LightMapsLevel=2
TextureLevel=2
ShadowResolution=2
AntiAliasing=2
EffectsQuality=3
```

# Splinter Cell: Pandora Tomorrow

## Shadow/reflection fix

[This page](http://www.jiri-dvorak.cz/scellpt/) contains a fix for the vertex
shader garbage.

## Mouse acceleration

The mouse acceleration in this game verges on making it unusable (why?!). In
`offline\system\ESetting.ini`, change all `useAimTuning` lines from `v=1` to
`v=0`. You need to create a new save to register the change.

# Splinter Cell: Chaos Theory

## Shadow/reflection fix

Software TnL emulation is needed, which can be provided by the ancient
[3D-Analyze](https://www.tommti-systems.de/start.html).

Select "Gun Metal Demo fix". There's also conveniently an option to save a
batch file which will launch with these settings.

## Mouse acceleration

In `System\SplinterCell3Settings.ini`, change all `biasCut` values to `v=0.0`.
Once again, you need to have a fresh load to register the change. Sigh...
