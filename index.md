---
layout: default
title: "Chris Down"
description:
    "Linux sysadmin, SRE, and developer living in London, England, currently
    helping Facebook scale to more than 2 billion users."
---


Hey there! I'm an SRE, software developer, and system administrator, currently
working as a [Production Engineer][]/SRE at [Facebook][]. I work as part of the
Linux Kernel team, responsible for kernel-related developments that improve the
overall reliability and performance of Facebook's user-facing products. In
general, my drive is in concieving, designing, and improving systems that make
Facebook and the wider industry better.

Most of my active work revolves around making operating systems more efficient
at scale, developing things like [the Linux kernel](https://lore.kernel.org/patchwork/project/lkml/list/?series=&submitter=25468&state=*&q=&archive=&delegate=),
[cgroups](https://www.youtube.com/watch?v=ikZ8_mRotT4),
[systemd](https://github.com/systemd/systemd), and a number of other emerging
technologies.

Outside of that, I dabble in
[photography](https://www.flickr.com/photos/chrisdown/albums/72157711447135721)
and [sim racing](/racing.html).

[Facebook]: https://www.facebook.com
[Production Engineer]: https://www.quora.com/What-is-it-like-to-be-a-Production-Engineer-at-Facebook/answer/Larry-Schrof

## Recent blog posts

{% for post in site.posts limit:5 %}- [{{ post.title }}]({{ post.url }})
{% endfor %}

More posts are available on the [archive page](/archive.html).

## Software

I am a contributor to and maintainer of a number of projects, including:

- [cgroup v2](https://www.youtube.com/watch?v=ikZ8_mRotT4) — modern resource control and accounting
- [hypothesis](https://github.com/DRMacIver/hypothesis) — an advanced Quickcheck style testing library for Python
- [Linux](https://lore.kernel.org/patchwork/project/lkml/list/?series=&submitter=25468&state=*&q=&archive=&delegate=) — a free and open-source OS kernel
- [mpv](https://github.com/mpv-player/mpv) — videos on the command line
- [oomd](https://github.com/facebookincubator/oomd) — next-generation OOM killer
- [osquery](https://github.com/facebook/osquery) — an OS instrumentation, monitoring, and analysis framework
- [pacaur](https://github.com/rmarquis/pacaur) — an AUR helper that minimises user interaction
- [pass](https://www.passwordstore.org/) — the standard Unix password manager
- [systemd](https://github.com/systemd/systemd) — a system and service manager for Linux
- [taglib-rust](https://github.com/ebassi/taglib-rust) — Rust FFI bindings for taglib
- [the Pro Git book](https://git-scm.com/book/en/v2) — a guide to Git and its internals

I also maintain the following personal projects:

- [aur](https://github.com/cdown/aur) — interface to the
  [Arch User Repository][]
- [clipmenu](https://github.com/cdown/clipmenu) — a clipboard manager with a
  dmenu frontend
- [gh-mirror](https://github.com/cdown/gh-mirror) — mirror all public
  repositories for a user to your local machine
- [mac-cel](https://github.com/cdown/mac-cel) — remove mouse acceleration on
  OSX
- [nota](https://github.com/cdown/nota) — super simple daily logs with
  your $EDITOR + git
- [mack](https://github.com/cdown/mack) — an opinionated, fast music organiser
- [mpdmenu](https://github.com/cdown/mpdmenu) — control [mpd][] from dmenu
- [pinyin](https://github.com/cdown/pinyin) — manipulate [Hanyu Pinyin][]
- [srt](https://github.com/cdown/srt) — a library to deal with [SRT files][]
- [travis-automerge](https://github.com/cdown/travis-automerge) — automatically
  merge successful builds from [Travis CI][]
- [tzupdate](https://github.com/cdown/tzupdate) — update /etc/localtime
  automatically using geolocation
- [xinput-toggle](https://github.com/cdown/xinput-toggle) — tool to manipulate
  arbitrary xinput devices
- [yturl](https://github.com/cdown/yturl) — watch YouTube videos on the command
  line

You can find other projects on my [GitHub][], although if they're not on this
list, I'm probably not actively developing or maintaining them.

## Things on this site

- [Assorted technology-related notes](/archive.html)
- [Project quality dashboard](/builds)
- [Sim racing data/notes](/racing.html)
- [My PGP public key](https://keybase.io/cdown/key.asc)
- [My SSH public key](/ssh)
- [My old TF2 configs](/tf2)
- [RYM profile export](/rym.html)
- [Old game miscellania](/oldgames.html)

## Profiles elsewhere

- [Facebook][]
- [GitHub][]
- [Instagram](https://instagram.com/_u/chrisldown)
- [Keybase](https://keybase.io/cdown)
- [last.fm][]
- [LinkedIn](https://www.linkedin.com/in/chrisldown)
- [Reddit][]
- [Twitter][]
- [Unix and Linux Stack Exchange]({{ site.links.ulse }})

## Talks

- [Memory Management at
  Scale](/2019/07/18/linux-memory-management-at-scale.html) —
  [SREcon](https://www.usenix.org/conference/srecon19asia/presentation/down)
- [cgroupv2: Linux's new unified resource
  hierarchy](https://www.youtube.com/watch?v=ikZ8_mRotT4) —
  [FOSDEM](https://archive.fosdem.org/2017/schedule/event/cgroupv2/)/DevOpsDays/[ASG](https://cfp.all-systems-go.io/en/ASG2017/public/events/96)
- [Lessons learned running SSL at
  scale](https://www.youtube.com/watch?v=9Ya8H-9Hrp4) —
  [FOSDEM](https://archive.fosdem.org/2016/schedule/event/sslmanagement/)
- The Web Foundation model — [University College
  London](https://www.ucl.ac.uk/) lecture
- [Bash pitfalls and code
  smells](http://slides.com/chrisdown/avoiding-bash-pitfalls-and-code-smells/fullscreen)
  — LVL.UP Kuala Lumpur
- [Pragmatic minimalism as a software design
  tool](http://slides.com/chrisdown/pragmaticminimalism/fullscreen) — LVL.UP
  Kuala Lumpur

[SRT files]: https://en.wikipedia.org/wiki/SubRip#SubRip_text_file_format
[mpd]: http://mpd.wikia.com/
[Hanyu Pinyin]: https://en.wikipedia.org/wiki/Pinyin
[Arch User Repository]: https://aur.archlinux.org/
[GitHub]: https://github.com/cdown
[Travis CI]: https://travis-ci.org
[Facebook]: https://facebook.com/christopherdown
[Twitter]: https://twitter.com/unixchris
[last.fm]: http://last.fm/user/unixchris
[Reddit]: https://www.reddit.com/user/chrisdown/

<!-- Structured data for Google -->

<div itemscope="" itemtype="http://schema.org/Person">
<meta itemprop="gender" content="Male">
<meta itemprop="jobTitle" content="Production Engineer at Facebook">
<meta itemprop="email" content="chris@chrisdown.name">
<meta itemprop="url" content="https://chrisdown.name">
<meta itemprop="image" content="https://chrisdown.name/images/headshot.jpg">
<meta itemprop="worksFor" content="Facebook">
<meta itemprop="name" content="Chris Down">
<meta itemprop="description" content="Chris Down is a software developer and system administrator, currently working as a Production Engineer/SRE at Facebook. He works as part of the Linux Kernel team, responsible for kernel-related developments that improve the overall scalability, performance, and reliability of Facebook’s user-facing products.">
</div>
