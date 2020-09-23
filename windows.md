---
layout: default
title: "Windows setup"
---

Disclaimer: I'm ignorant of quite a bit about Windows.

## Make updates manual

One thing I frequently noticed during framedrops in games is that processes
related to Windows Update would be consuming crazy amounts of userspace CPU and
disk IO in the background. I prefer to manually update anyway, so I just made
it manual:

    Windows Registry Editor Version 5.00

    [HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate]

    [HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU]
    "NoAutoUpdate"=dword:00000001

## Disable search indexing

Even with indexer backoff I saw this saturating disk I/O during gameplay. I
don't use it, so:

    sc stop "WSearch"
    sc config "WSearch" start= disabled

Even with this the SearchUI process keeps going and causes huge offcpu spikes
for games. :-(

To stop that you really have to engage in some terrible racy hackery which will
probably get reverted by updates:

    cd %windir%\SystemApps\Microsoft.Windows.Cortana_cw5n1h2txyewy

    takeown /f SearchUI.exe
    icacls SearchUI.exe /grant administrators:F

    taskkill /f /im SearchUI.exe
    rename SearchUI.exe SearchUI.exe.001

    taskkill /f /im SearchUI.exe
    rename SearchUI.exe SearchUI.exe.001

    taskkill /f /im SearchUI.exe
    rename SearchUI.exe SearchUI.exe.001

    taskkill /f /im SearchUI.exe
    rename SearchUI.exe SearchUI.exe.001

## Caps to ctrl

    Windows Registry Editor Version 5.00

    [HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Keyboard Layout]
    "Scancode Map"=hex:00,00,00,00,00,00,00,00,02,00,00,00,1d,00,3a,00,00,00,00,00

## Disable mitigations

I only use Windows for games, so the tradeoff is reasonable here.

    Windows Registry Editor Version 5.00

    [HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management]
    ; Bitmask with two bits:
    ; 1<<0: Disable Spectre mitigation
    ; 1<<1: Disable Meltdown mitigation
    "FeatureSettingsOverride"=dword:00000003
    "FeatureSettingsOverrideMask"=dword:00000003

## Only page on non-rotational disks

I noticed that, by default, it's possible that paging files are also enabled on
slow disks. I have no idea whether Windows understands it should probably
prioritise paging files on non-rotational disks, so I just went into
Performance, Advanced, Virtual Memory, "Change", and set a system-managed
paging file on non-rotational disks and nothing on rotational ones.

## Defragment/TRIM

In Windows, for some reason, both defragmentation and TRIM are in a single
application called "Defragment and Optimise Drives" (go figure). I just set the
schedule to TRIM/defrag weekly.

## noatime equivalent

It seems NTFS doesn't have a `relatime` equivalent, so to avoid getting writes
on reads:

    fsutil behavior set disablelastaccess 1

## OBS settings

I record quite a few videos with OBS. At least in Assetto Corsa, I often
experience framedrops with default settings (although I've not yet really been
able to pin down what the cause is, since I don't see any obvious bottlenecks).
However, this is somewhat minimised with the following settings:

![](/images/blog/windows/obs1.png)
![](/images/blog/windows/obs2.png)
![](/images/blog/windows/obs3.png)
![](/images/blog/windows/obs4.png)

I also set OBS on high priority, since usually my game has uncapped FPS, so can
afford to drop a couple of frames, while NVENC/OBS can't afford to drop a whole
output frame which goes into the final video. I also set the game itself on
"above normal" and with high I/O priority, just to try to mitigate any
shenanigans from things that decide to run in the background and hog a core
during gameplay, or cause major faults to take a really long time for cold code
(for example, when someone joins the server after a really long time).

You can use [Prio](http://www.prnwatch.com/prio/) to restore the set CPU
scheduler and I/O scheduler priorities on further game launches. OBS itself
also has an option to use high priority when recording in the settings menu.

## Misc

- Power plan to "high performance". I'm not entirely certain this will actually
  do much, though, unless your CPU/GPU keep on stepping up and down during
  gameplay otherwise, but why not.
- Disable hibernation with `powercfg /hibernate off`, since otherwise you're
  left with a hibernation file on the root of your system drive.
- GeForce Experience has a "game optimiser" thing. You'll probably want to turn
  that off, since otherwise it overrides your in-game settings. This confused
  me a lot when it was turned on in an update. You might just want to avoid
  installing GeForce Experience at all.
- Disable Game Bar and Game DVR in Control Panel. This actually does seem to
  make some kind of difference in performance, presumably because it has to
  process and ringbuffer some video all the time.
- Disable audio/video recording in "Captures" settings
- [Autoruns](https://docs.microsoft.com/en-us/sysinternals/downloads/autoruns)
  is very useful for an occasional check to make sure stuff isn't starting up
  on boot unnecessarily.
