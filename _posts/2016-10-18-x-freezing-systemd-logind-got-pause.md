---
layout: post
title: 'X freezing as "systemd-logind: got pause for [...]"'
---

From a month or so ago I started getting sporadic freezes on my T460s. These
freezes tended to occasionally manifest when pressing Mod4, or other modifier
or media keys.

When these freezes would occur, the following would be printed in the Xorg
logs:

    (II) AIGLX: Suspending AIGLX clients for VT switch
    (II) systemd-logind: got pause for 13:64
    (II) systemd-logind: got pause for 13:75
    (II) systemd-logind: got pause for 13:81
    [...]

So for some reason systemd-logind had been told to block input.

After this happened a few times I noticed something strange -- sometimes when
this would freeze, we would see interleaved resumes for some devices:


    (II) AIGLX: Suspending AIGLX clients for VT switch
    (II) systemd-logind: got pause for 13:64
    (II) systemd-logind: got pause for 13:75
    (II) systemd-logind: got resume for 13:64
    (II) systemd-logind: got pause for 13:64
    (II) systemd-logind: got resume for 13:75
    (II) systemd-logind: got pause for 13:75
    (II) systemd-logind: got pause for 13:81
    [...]

This hinted to me that this issue might be a race condition in some process
that talks to systemd-logind. Well, systemd-logind communicates over dbus, so
that seemed a good place to start, and what do you know:

    % pgrep -ax dbus-daemon -U "$USERNAME" | grep -- --session
    984 /usr/bin/dbus-daemon --session --address=systemd: --nofork --nopidfile --systemd-activation
    1025 /usr/bin/dbus-daemon --fork --print-pid 4 --print-address 6 --session

How bizarre -- two instances of the dbus session daemon are started. This
shouldn't happen, dbus is supposed to be started by systemd's user session.

We can see that the first dbus-daemon instance (pid 984) is launched by
systemd, as evidenced by the passing of `--address=systemd:`. This is also the
one listed if we check what systemctl says (see "Main PID"):

    % systemctl --user status dbus
    ● dbus.service - D-Bus User Message Bus
       Loaded: loaded (/usr/lib/systemd/user/dbus.service; static; vendor preset: enabled)
       Active: active (running) since Tue 2016-10-18 15:21:21 BST; 52min ago
         Docs: man:dbus-daemon(1)
     Main PID: 984 (dbus-daemon)
       CGroup: /user.slice/user-1000.slice/user@1000.service/dbus.service
               ├─ 984 /usr/bin/dbus-daemon --session --address=systemd: --nofork --nopidfile --systemd-activation
               ├─1165 /usr/lib/xfce4/xfconf/xfconfd
               └─1302 /usr/lib/GConf/gconfd-2

So where does the other one come from? After checking my [dotfiles][], I
noticed this:

    % git grep dbus
    .xinitrc:exec dbus-launch --exit-with-session dwm > "/tmp/dwm-$USER.log" 2>&1

Back in the days before systemd user sessions, one had to launch a dbus session
by yourself. One popular way to do this was with dbus-launch, which is used
here, but this was not updated once dbus.service became enabled by default in
systemd user profiles.

The fix here is simple, then &mdash; launch your window manager directly
instead of wrapping its execution with dbus-launch. In this case:

    % git show e674
    commit e6746a843b3fa7c545483566fcb49fa3be858bf2
    Author: Chris Down <chris@chrisdown.name>
    Date:   Tue Oct 18 15:16:36 2016 +0100

        Do not launch dwm with dbus-launch

        dbus should be launched in the systemd user session, not through
        dbus-launch. This (yet to be confirmed) causes the freezes I'm seeing
        that look like this:

            [   124.236] (II) AIGLX: Suspending AIGLX clients for VT switch
            [   124.263] (II) systemd-logind: got pause for 13:64
            [   124.263] (II) systemd-logind: got pause for 13:75
            [   124.263] (II) systemd-logind: got pause for 13:81
            [   124.263] (II) systemd-logind: got pause for 13:69
            [   124.263] (II) systemd-logind: got pause for 13:65
            [   124.263] (II) systemd-logind: got pause for 13:68
            [   124.263] (II) systemd-logind: got pause for 226:0
            [   124.263] (II) systemd-logind: got pause for 13:76
            [   124.263] (II) systemd-logind: got pause for 13:67
            [   124.263] (II) systemd-logind: got pause for 13:77

    diff --git a/.xinitrc b/.xinitrc
    index 25e9da4..3a60d51 100644
    --- a/.xinitrc
    +++ b/.xinitrc
    @@ -72,4 +72,4 @@ for scontrol in Master PCM; do
         amixer -q sset "$scontrol" 100%
     done

    -exec dbus-launch --exit-with-session dwm > "/tmp/dwm-$USER.log" 2>&1
    +exec dwm > "/tmp/dwm-$USER.log" 2>&1

The fix is simple, but this was annoying to debug, so I'm putting this out
there to hopefully save others some time. :-)

[dotfiles]: https://github.com/cdown/dotfiles
