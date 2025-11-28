---
layout: default
title: "Old game miscellany"
---

I play a lot of "old" games that need some poking to get them to work properly.
This is a place to record what's needed.

Most of these are either with my 750M (gaming laptop) or GTX 1070 (gaming
desktop).

# Deus Ex

[GMDX v10](https://www.moddb.com/mods/gmdx-v10-community-update), although vanilla is also fine if you
manually install [Kentie's launcher](https://kentie.net/article/dxguide/) which
otherwise comes bundled. There's also
[Han's](https://coding.hanfling.de/launch/), but I've never tried it.

Also get the [D3D10 renderer](https://kentie.net/article/d3d10drv/) if you're
going to use Kentie's launcher.

To launch directly on Steam and track time played:

1. In the Deus Ex install folder, open the System directory and rename
   DeusEx.exe to DeusEx.exe.orig (or whatever)
2. Copy GMDXv10.exe to DeusEx.exe
3. Add the following launch options: `INI="GMDXv10.ini" USERINI="GMDXv10User.ini"`

# Splinter Cell

## Dynamic lighting method autodetection bug

Splinter Cell autodetects that the 750M supports projected textures for dynamic
lighting (e.g. spotlights/flashlights), but this is an old Radeon-only
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
4:3 res), as it causes overlaid interactions to become misaligned (e.g.
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

[This
page](https://web.archive.org/web/20200314075505/http://www.jiri-dvorak.cz/scellpt/)
contains a fix for the vertex shader garbage.

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

# Oblivion

1. Grab the following mods and install with JSGME in order (these are also in the files S3 bucket):
    1. EBF/other dependency: [xOBSE](https://github.com/llde/xOBSE/releases)
    2. [Unofficial Oblivion Patch](https://www.nexusmods.com/oblivion/mods/5296)
    3. [Unofficial Oblivion DLC Patch](https://www.nexusmods.com/oblivion/mods/9969)
    4. [Unofficial Shivering Isles Patch](https://www.nexusmods.com/oblivion/mods/10739)
    5. [EngineBugFixes](https://www.nexusmods.com/oblivion/mods/47085)
    6. [Light of Oblivion](https://www.nexusmods.com/oblivion/mods/46131) (use the Bravil mesh)
    7. [RTNM](https://www.nexusmods.com/oblivion/mods/38204) (download part 1, 2, and shivering isles "fixed")
    8. [Hear No Evil](https://www.nexusmods.com/oblivion/mods/25462)
2. Make sure all plugins are enabled in "data files".
3. Download [LOOT](https://loot.github.io/) + JSGME in base folder
4. "Fix ambiguous load order".
5. Update master list
6. Reorder
7. In nvidia CP, force override, 8x for AA and transparent AA. Also cap at 90fps for physics.

# GTA IV

See
[here](https://web.archive.org/web/20201109125821/https://steamcommunity.com/sharedfiles/filedetails/?id=1371539795).
Also, reducing vehicle density/view distance/detail distance reduces
stuttering.

# AC Mirage

Well, not exactly old, but still requires wading through the jank...

1. Use [aspectpatcher](https://github.com/cdown/aspectpatcher) to remove black
   bars on cutscenes (`% aspectpatcher -f 16:9 -t 3840x1600 ACMirage.exe`)
2. Replace bytes `80 79 32 00 74 0C 48 8B` with `80 79 32 01 74 0C 48 8B` to
   disable chromatic abberation.
