---
layout: post
title: CyanogenMod 10.1.3 RC1 Google Services battery life
---

Ever since I updated to 10.1.3 RC2 from the old 10.1 nightlies on my N7100, I
have had huge battery usage for Google Services.

It seems this is a known issue in RC1. Supposedly it's fixed in new builds, but
there's no newer RC for my phone, sadly. In the meantime, looking at the
partial wakelocks showed that SystemUpdateService was constantly keeping the
phone awake. For now, disabling SystemUpdateService has fixed this, although I
assume this stops automatic app updates from Google Apps.
