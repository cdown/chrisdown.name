---
layout: default
title: "Old game miscellanea"
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

# Oblivion

## Useful resources

- [Load order advice](https://wiki.nexusmods.com/index.php/Load_order_recommendations)
- [Mod install ordering](https://web.archive.org/web/20190113233526/http://wiki.theassimilationlab.com/tescosi/A_General_Order_for_Installing_Mods_(Oblivion))
- [OBMM](https://www.nexusmods.com/oblivion/mods/2097) ("full manual")
- [OBSE](https://obse.silverlock.org/)
- [BOSS](https://boss-developers.github.io/)

## Mods

- [EngineBugFixes](https://www.nexusmods.com/oblivion/mods/47085)
- [Light of Oblivion](https://www.nexusmods.com/oblivion/mods/46131) (use the Bravil mesh)
- [RTNM](https://www.nexusmods.com/oblivion/mods/38204) (download part 1, 2, and shivering isles "fixed")
- [Unofficial Oblivion DLC Patch](https://www.nexusmods.com/oblivion/mods/9969)
- [Unofficial Oblivion Patch](https://www.nexusmods.com/oblivion/mods/5296)
- [Unofficial Shivering Isles Patch](https://www.nexusmods.com/oblivion/mods/10739)
- [Hear No Evil](https://www.nexusmods.com/oblivion/mods/25462)

## Order

After each one, check Oblivion starts up. Also, it's quite confusing that Oblivion.esm isn't checked in the load order, but it works anyway, so...

OBMM also seems to use the same thread for UI and disk IO, so don't be surprised if it hangs.

Import process in OBMM:

1. "Create" at the bottom
2. "Add archive" or "add folder"
3. Name it anything reasonable
4. Create OMOD
5. Once it's done, double click the OMOD on the right, it will turn from green to blue

1. OBSE
    1. Copy obse_1_2_416.dll, obse_editor_1_2.dll, and obse_steam_loader.dll to your Oblivion directory.
    2. Also copy obse_loader.exe just for OBMM -- Steam won't use it but some OMODs won't recognise OBSE otherwise
    3. Ensure you have enabled the Steam community in-game, or OBSE will fail to load. Go to Steam > Settings > In-Game and check the box marked "Enable Steam Overlay".
2. OBMM
    1. Copy everything to Oblivion directory 
    2. Check Oblivion runs (but it won't work through "launch" button in OBMM itself, since it wants to load using obse_loader.exe)
3. Unofficial Oblivion Patch
4. Unofficial Oblivion DLC Patch (UOPCastleCeilingLightMount.NIF conflicts with UOP for some reason, just accept it)
5. Unofficial Shivering Isles Patch (tons of conflicts with UOP, accept them all)
6. EngineBugFixes (don't worry, nothing will show up because it has no ESPs)
7. Light of Oblivion, Bravil
8. RTNM
    1. Part 1
    2. Part 2
    3. Shivering Isles
9. Hear No Evil
10. Archive invalidation (BSA redirection)

Don't use the Oblivion launcher "data files" section to enable stuff any more, since it will mess up the load order.

## Reordering

Use BOSS.
