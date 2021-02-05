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
for games, but sadly Windows updates bring back the executable, so eh...

## Disable fullscreen optimisations

    Windows Registry Editor Version 5.00

    [HKEY_CURRENT_USER\System\GameConfigStore]
    "GameDVR_FSEBehaviorMode"=dword:00000002
    "GameDVR_HonorUserFSEBehaviorMode"=dword:00000001
    "GameDVR_FSEBehavior"=dword:00000002
    "GameDVR_DXGIHonorFSEWindowsCompatible"=dword:00000001

## Enable Hardware Accelerated GPU Scheduling

    Windows Registry Editor Version 5.00

    [HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\GraphicsDrivers]
    "HwSchMode"=dword:00000002

## Enable Variable Refresh Rate.

Display, Graphics settings, enable VRR.

## Turn on Developer Mode

This allows `mklink` and other things without an admin prompt.

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

## Disable SmartScreen

    Windows Registry Editor Version 5.00

    [HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Microsoft\Windows\System]
    "EnableSmartScreen"=dword:00000000

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

## Disable FTH

Fault Tolerant Heap is enabled on repeated crashes, but having it enabled in
games will just reduce performance. You can clear the cache with:

    Rundll32.exe fthsvc.dll,FthSysprepSpecialize

And disable it entirely with:

    Windows Registry Editor Version 5.00
    
    [HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\FTH]
    "Enabled"=dword:00000000

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

# Overclocking

Not Windows-specific, of course, but worth having some place to record these.
Generally worth doing these in order of most benefit for gaming:

## Generic validation

Some generic validation utilities to check improvements:

- [UserBenchmark](https://www.userbenchmark.com/)
- [3DMark](https://benchmarks.ul.com/3dmark)
- [PerformanceTest](https://www.passmark.com/products/performancetest/) (deeper memory test than UserBenchmark)
- [hwinfo64](https://www.hwinfo.com/download/)
  - Disable nvidia monitoring due to [this](https://www.hwinfo.com/forum/threads/hwinfo64-v6-40-4330-is-leaking-handles.6970/)

Also, a good overview [here](https://www.tomshardware.com/reviews/stress-test-cpu-pc-guide,5461.html).

## GPU

Core clock is a lot more important than memory clock, in general, although
memory clock may be able to boost to huge values (+1000 from stock).

Memory clock and core clock also affect each other: for example, I can run
stable at 0/+850 in Watch Dogs 2, or +70/0 but not +70/+850, even before
reaching thermal limits. In general, prioritise core over memory.

Use MSI Afterburner, and bump core voltage (if available, not on this 1080),
power, and temp limits to max.

### Core clock

Then, bump core clock by 15mhz increments -- that's the minimum granularity, at
least on these 3080 cards while running Heaven or Superposition benchmark,
until it crashes. Then dial it back 15mhz to the last value.

Now go run some games, I used Assassin's Creed Syndicate and Watch Dogs 2.
You'll probably have to lower it some more for real-world scenarios. In the
3080's case, I could get about +100 in Heaven, but in real world I can only do
+60.

You probably want to set up the RivaTuner OSD to see what's going on. Possible
limits:

- Power: max watts drawn by the card
- Voltage: max voltage drawn by the GPU core
- No load: the GPU is downclocking because it doesn't think anything needs
  doing

You'll also probably see that GPU core clock is very different in these games,
since the limits result in a different part of the voltage/frequency curve
being applied. You can manually tweak that in Afterburner with the icon to the
left of core clock, but in reality that's pretty fiddly and unlikely to help
much.

### Memory clock

Memory clock generally stays pretty stable under load, unlike the core clock.
This means it's usually easier to reason about. However, Nvidia cards do memory
error correction, but don't supply any statistics on when it happens. This
means you have to double check that you're actually getting more performance,
since error correction will slow things down.

I usually open Heaven or Superposition and just bump it in 100mhz increments
until artefacts or crashes occur. Then, try dialling it back until no artefacts
are occurring.

Since there's error correction, this might still not have good performance,
though. Try lowering the memory clock 50mhz at a time and recording benchmark
results to find the optimal value.

### Validation

I run the following benchmarks in sequence to get a good overview of different
game types, since they demand different clocks/limits:

- Old games: Sky Diver stress test
- Modern-ish games at low res: Fire Strike stress test
- Modern high-res: Time Spy extreme stress test

OCCT 3D test is less useful since the card throttles down hard due to
power/thermal limits.

### Results for 3080

+40mhz core, +750mhz memory

## Memory

First, make sure you enabled the XMP profile in your UEFI. XMP 1 vs 2 is
manufacturer-specific, double check the timings and frequency against what's
listed as specs.

For mine, I have two XMP profiles available:

- 4140 19-23-23-45 @ 1.40v
- 4000 18-19-19-39 @ 1.35v

Since >4000mhz is already pushing past what most games can use anyway, I opted
to use the 4000 profile with tighter timings. You can check the actual CAS
latency like this:

    In [1]: mhz = 4000

    In [2]: cas = 18

    In [3]: (1.0/( mhz/2.0 )*cas )*1000.0
    Out[3]: 9.000000000000002

    In [4]: mhz = 4140

    In [5]: cas = 19

    In [6]: (1.0/( mhz/2.0 )*cas )*1000.0
    Out[6]: 9.178743961352657

For overclocking, I'd keep the frequency set at what's in your XMP profile, and
start tuning down tCL until you cannot boot. Then go back up one and run
[TestMem5](https://drive.google.com/file/d/175jXRSu6iVZYoXq6OaRrlcwUGP9KcbOW/view?usp=sharing)
and OCCT memtest for 10 minutes. If it passes, start bumping down tRCD and tRP
by 1, until you can't boot. Now do the same with OCCT, and run for 1h to verify
stability.

tRAS I'd leave alone -- if you set the value wrongly here, the IC is going to
do stupid things (see
[here](https://www.reddit.com/r/overclocking/comments/fwx3y2/tras_performance_penalty/)).

In my case, I was able to get down to 4000 16-16-16-39 @ 1.4v. Don't worry too
much about RAM voltage, up to 1.4-1.5v it's quite tolerant.

However, in Watch Dogs: Legion, which is (as of writing this) a very RAM
frequency-bound game ([see
here](https://www.dsogaming.com/pc-performance-analyses/watch-dogs-legion-can-finally-run-with-constant-60fps-on-high-end-cpus/)),
the benchmark is pretty clear: a very small (1fps) boost in average FPS, but a
large increase in stability with default XMP values of 4140 19-23-23-45, which
in my case can be reduced further to 18-20-20-45.

After more testing with Karhu, though, I needed to not only go back to XMP 4140
19-23-23-45, but also up the voltage to 1.45v to pass 10h/10000% coverage with
CPU cache default.

## CPU

Modern CPUs have a few complications when it comes to overclocking:

- Turbo boost, where frequency may be raised during demanding tasks
- Intel "favored core" stuff: some cores may be more highly clocked by default

Per-core tweaking isn't really worth it, since the OS CPU scheduler is likely
to try to balance things out anyway, so just sync all cores in BIOS.

A good initial benchmark to aim for is to hit somewhere near the boost clock
for the CPU with all cores. In my case that's 5.3ghz (on favored cores).

A few things to start off:

- CPU core voltages can fluctuate. LLC helps with that. On a high-end board,
  you're fairly safe running with high LLC settings to compensate for voltage
  drops under load -- LLC 5 or 6. I suggest starting with 5.
- You probably want to disable Short Power Max load throttling in the BIOS,
  just for more benchmark stability (although you're unlikely to hit it in the
  real world). This reduces power if constantly demanded at max after some number
  of seconds (default is 25, I think), which also likely results in stopping
  turbo boost.
- On ASUS motherboards, you want to enable ASUS Multicore Enhancement,
  otherwise the Intel stock limits will apply.
- AVX workloads can be extremely thermally demanding, so there's an option to
  downclock when running them (AVX negative offset). I have it set on 0, but 1
  (ie. 100mhz downclock) is also fine.
- You probably also want to disable BLCK aware adaptive voltage to reduce the
  complexity of reasoning about voltage during OC, since it will reduce it.

Now, start by setting the voltage to something close to the maximum you're
willing to permit, in my case with the 10900K, it's 1.4v. If you look in CPU-Z,
you should ideally see minimal voltage drop under load from idle -- in stock on
my machine, it was about 0.1v drop, which is pretty high: the default is LLC2.
With LLC5 or 6, it's much less pronounced.

Don't worry too much about thermals in testing, although they may make the test
less effective, of course, due to thermal throttling downclocking the CPU. 100C
is really nothing for a modern 10900K during benchmarking.

There are a couple of things I'd suggest running:

- Cinebench multi-core, to validate things are faster, although if you're
  getting thermal throttling it might show it's slower when it wouldn't be in the
  real world.
- Prime95 in-place large FFTs for 20-30 mins or so. Small FFTs produces voltage
  overshoots which are not really real-world, so you might get hangs there.

Throughout these, I'd suggest monitoring the voltage under load and idle, and
also checking if there were corrected L0 WHEA errors. You can see this at the
very bottom in "sensors" in hwinfo64. Any errors mean the OC is not stable.

In my case, I was able to get to 5.1ghz all-core @ 1.4v with LLC6. In
Cinebench and Prime95 it easily reaches 100C and downclocks, but in the real
world, it works.

## Nvidia CP

I set texture filtering quality to high performance globally -- I've never seen
a difference anywhere but in FPS.

You can also disable Ansel with Nvidia Inspector, if it's causing issues.
Currently it's in the "Common" section.

## Post-validation

I'd keep hwinfo64 running in the background in sensors mode on startup, just to
double check there are no WHEA errors over time.

Also the MSI RivaTuner overlay is quite useful in-game.

## Final overclocks for 2020 build

- CPU: 5.1ghz all-core @ 1.4v with LLC6
- RAM: 4140 19-23-23-45 @ 1.45v
- GPU: +40 core/+750 mem
