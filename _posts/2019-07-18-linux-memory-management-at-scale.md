---
layout: post
title: "Linux memory management at scale"
---

As part of the my work on the
[cgroup2](https://facebookmicrosites.github.io/cgroup2/) project, I spend a lot
of time talking with engineers about controlling resources across Linux
systems. One thing that has become clearer and clearer to me through these
conversations is that many engineers -- and even senior SREs -- have a number
of common misconceptions about Linux memory management, and this may be causing
the services and systems they support to not be able to run as reliably or
efficiently as they could be.

As such, I wrote a talk which goes into some of these misconceptions, going
into why things are more nuanced than they might seem when it comes to memory.
I also go over how to compose more reliable and scalable systems using this new
knowledge, talking about how we are managing systems within Facebook, and how
you can apply this knowledge to improve your own systems.

I had the privilege to present this talk at SREcon, and hope you'll find it
useful. Please feel free to e-mail me with any questions or comments.

<small>(Unfortunately the audio is left-channel only (and this can only be fixed
by USENIX, since it's hosted on their channel). If you have `ffmpeg`, you can
mitigate this by downloading the video with youtube-dl, then processing the
video with `ffmpeg -i talk.webm -map_channel 0.1.0 -c:v copy talk_fixedaudio.webm`.)</small>

{% youtube HpoK5-Uuxuk %}

## Key timestamps

I recommend watching the whole talk, since each section helps set up the next, but here are some key takeaways:

- 2:18: [Resource control is important, you need it both for reliability and efficiency](https://youtu.be/HpoK5-Uuxuk?t=138)
- 6:34: [If you just limit one resource alone, it may actually make things worse](https://youtu.be/HpoK5-Uuxuk?t=395)
- 7:28: [Resource control is much more complicated than it seems](https://youtu.be/HpoK5-Uuxuk?t=448)
- 12:56: [Being "reclaimable" isn't a guarantee, caches and buffers don't act like free memory, even though many people think they do](https://youtu.be/HpoK5-Uuxuk?t=776)
- 14:54: [We measure RSS and pretend it's meaningful because it's easy to measure, not because it measures anything useful](https://youtu.be/HpoK5-Uuxuk?t=894)
- 16:12: [Swap matters, even on machines with huge amounts of memory](https://youtu.be/HpoK5-Uuxuk?t=972)
- 18:59: [The OOM killer is often not your friend in an OOM situation, and probably doesn't work in the way you expect](https://youtu.be/HpoK5-Uuxuk?t=1139)
- 22:10: [Different types of memory reclaim and why they matter](https://youtu.be/HpoK5-Uuxuk?t=1330)
- 25:05: [How to know if a system is running out of memory (you can't just look at MemAvailable or MemFree + Buffers + Cached)](https://youtu.be/HpoK5-Uuxuk?t=1505)
- 29:30: [How we detect emerging OOMs before the OOM killer](https://youtu.be/HpoK5-Uuxuk?t=1770)
- 30:49: [Determining a usable metric for I/O resource isolation](https://youtu.be/HpoK5-Uuxuk?t=1849)
- 34:42: [Limiting things generally doesn't work well, so let's create protections instead](https://youtu.be/HpoK5-Uuxuk?t=2082)
- 37:21: [Putting all of these primitives together to create an efficient, high availability system](https://youtu.be/HpoK5-Uuxuk?t=2241)
- 46:09: [Results from Facebook production](https://youtu.be/HpoK5-Uuxuk?t=2769)
- 48:03: [Using some of these new concepts to help improve Android](https://youtu.be/HpoK5-Uuxuk?t=2883)
- 48:53: [How to practically make use of the advice in this talk yourself](https://youtu.be/HpoK5-Uuxuk?t=2933)
