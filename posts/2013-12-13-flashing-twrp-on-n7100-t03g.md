---
layout: post
title: Flashing TWRP on the N7100/t03g
excerpt: How to flash TWRP on the N7100/t03g on Arch Linux
---

I always forget how to do this and end up reading lots of conflicting "advice",
so it seems wise to put it here:

- [Download the latest TWRP image in .img format][dl]. The latest ones appear
  to be at the bottom (go figure);
- Check the md5sum matches what goo.im said when you downloaded it;
- Install heimdall, adb-git, and android-udev from the AUR;
- `adb reboot download`, or manually get it by holding power + home + volume
  down at the same time;
- `heimdall flash --RECOVERY [image]`. This step was annoying to resolve.
  Every other device I have has a partition called "recovery", not "RECOVERY".
  In the end, it wasn't too difficult to work out what it was called, just look
  at the output of `heimdall print-pit` when still in download mode.

[dl]: http://goo.im/devs/OpenRecovery/t03g
