---
layout: default
title: Chris' TF2 configs
description: The official site for Chris' TF2 configs.
---

# TF2 configs

I stopped playing in European TF2 leagues in mid-2012, and these configs have
barely been updated since then. Your mileage may vary. Do not e-mail me about
them, I do not provide any support at all any more.

These configs should continue working just fine into the near future, but they
may be missing optimisations that could be applied on versions of TF2 newer
than the last release.

There are a lot of thanks to be given to Arie for letting me host these at
[FakkelBrigade][] back in the day; without being able to host there in the
early days, these configs would not have been so widely disseminated.

## Download

- [ZIP archive of the final release][zip]
- [Git repo containing (partial) release history][github]

[github]: https://github.com/tf2configs/tf2configs
[zip]: https://github.com/tf2configs/tf2configs/archive/2.016.zip
[FakkelBrigade]: http://fakkelbrigade.eu

## FAQ

### How do I install the config?

Put the contents of the config that you want to use in `cfg/autoexec.cfg`.

### How do I uninstall the config?

The Source engine stores some values by itself outside of `cfg/autoexec.cfg`,
so removal is not enough. Reinstalling may not work either, since Steam Cloud
may restore the config you want to remove. Here's how to do it:

1. Remove `cfg/autoexec.cfg`
2. Add `-autoconfig` to your launch options
3. Launch the game
4. Quit the game
5. Remove `-autoconfig` from your launch options
