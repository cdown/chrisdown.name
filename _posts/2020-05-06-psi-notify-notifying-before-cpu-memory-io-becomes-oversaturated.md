---
layout: post
title: 'psi-notify: Alerting before CPU/memory/IO becomes oversaturated'
---

Link:
[https://github.com/cdown/psi-notify](https://github.com/cdown/psi-notify)

**tl;dr:** psi-notify can alert you when resources on your machine are becoming
oversaturated, and allow you to take action *before* your system slows to a
crawl.

---

I think we've all had situations where the desktop environment has become so
slow as to be unusable, usually because some application has started eating up
system resources quickly. Fellow Chrome users, I'm especially looking at you.
:-)

My wife is certainly someone in that position. Often she gets into scenarios
where unwieldy applications like Chrome would unexpectedly eat memory over
time, eventually ending with her desktop suddenly slowing to a crawl. Usually
the only way out of this situation is to manually trigger an OOM kill with Alt +
SysRq + F, and even then that's not foolproof, since the OOM killer [may not
pick the right target to kill](https://youtu.be/beefUhRH5lU?t=1139). Even if it
*does* pick the right target to kill, system responsiveness after the fact can
still be impacted since the thrashing has pushed many pages into swap.

Logging [PSI metrics](https://facebookmicrosites.github.io/psi/) on her machine
leading up to these incidents, it was pretty obvious that there was always an
opportunity to alert her ahead of time that the situation was becoming a
problem, and allow her to manually select which applications to kill, since it
might not always just be the one using the most memory or with the highest
memory usage in a desktop scenario. Since prioritisation of "what to kill" is
so dynamic on the desktop, it's very hard to write a one-size-fits-all policy
about what to do in these scenarios, so these notifications allow you to avoid
that problem entirely.

To that extent, psi-notify will warn you using whatever desktop notifier you
have running (eg. GNOME notifications, dunst, xfce4-notifyd) when resources are
starting to become contended, so that you can do something about that. A
facetious demo is shown below:

![](https://raw.githubusercontent.com/cdown/psi-notify/master/demo.gif)

## Comparison with oomd

oomd and psi-notify are two compatible and complementary projects, they're not
in opposition to each other. oomd also uses PSI metrics, but it requires a
policy about "what to kill" in high-pressure scenarios. For example, on a web
server we obviously don't want to kill the web server if we can avoid that, so
we should prioritise other applications. On the desktop though, it's hard to
say: should we kill Chrome, or some IDE, or maybe something playing a movie?
It's extremely difficult (although perhaps possible) to produce a single
configuration that will do the right thing in even the majority of cases, so we
opt to alert early instead and have the user make the decision about what's
high priority in their user session. I suspect most distributions when
integrating oomd for the desktop will end up having to make it less aggressive
than would be ideal, so they can still interoperate.

At least in my case, if I want oomd to be aggressive, it's still hard to
produce a good policy for, say, one's working day, where at one time my
terminal is the most critical thing, at another my browser is, and at another
it's my mail client. At other times maybe I'm ok with the slowdown and am
willing to ride it out without killing anything.

## Project improvements

Feature requests and bug reports are welcome. I've been using it for the last
week and already found it useful in keeping death-by-Chrome at bay. :-)

Thanks also to [Johannes](https://github.com/hnaz) for his help going over
unprivileged poll() support as part of this work!
