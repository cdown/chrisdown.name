---
layout: post
title: "Programming/gaming with the Kinesis Advantage 2"
description: "Advice on programming, gaming, and more with the Advantage 2"
---

Top among the things I'm most glad that I rescued from the office before access was barred for COVID has to be my Advantage 2.

![Kinesis Advantage 2](/images/blog/ka2/ka2.jpg)

It's a weird looking thing, with a design which will grant you strange looks, even from those who we know are the true weirdos -- the mechanical keyboard collectors (I kid, I kid!). However, despite its alien aesthetics and anachronistic bulky form, I've really come to love it over the last six years of using it.

As someone who's used an Advantage 2 for a long time, in this article I want to go over some of the tips and tricks for using it effectively, and adjustments you might want to make for programming and gaming. I'll lay it out as if talking to someone who newly got an Advantage 2, so we'll start with upgrading the firmware first, but you can skip past that without issue.

## Prelude: updating the firmware

The Advantage 2 is highly programmable and customisable, and many of those features have been added with more recent firmware. If you just got a new Advantage 2, it's entirely possible that you will have out of date firmware. As of writing this, the latest version is 1.0.521, which you can find [here](https://kinesis-ergo.com/support/advantage2/#firmware-updates).

This then begs the question -- how do you even find out what version of the firmware you're running? To find out, you can run `cat >/dev/null`, or open a text editor, and press Program + Esc. You'll then get something like the following put into the text area:

    % cat >/dev/null
    Model> Advantage2
    Firmware> 1.0.516.us (4MB), 07/22/2019
    Active layout file> qwerty.txt
    Thumb keys mode> none
    Macro play speed> off=0, slow=1, normal=3, fast=9> 3
    Status report play speed> off=0, slow=1, normal=3, fast=4> 3
    Keyclick status> off
    Toggle tone status> off
    Stored macros> 0

Program + Esc prints the current device status, and we can see that the device is out of date. In order to upgrade, the Advantage 2 provides flash memory which you can put a firmware update file into.

In order to do this, first press Program + Shift + Esc to enable power user mode. The LEDs will now flash. After that, press Program + F1 to make the flash accessible as a USB device. You should see it appear on the connected device:

    % dmesg -W
    [Mon Nov 16 18:01:13 2020] usb-storage 1-2.2.1:1.0: USB Mass Storage device detected
    [Mon Nov 16 18:01:14 2020] scsi 1:0:0:0: Direct-Access     ATMEL    AT45DBX Data Fla 1.00 PQ: 0 ANSI: 3
    [Mon Nov 16 18:01:14 2020] sd 1:0:0:0: [sdb] 8192 512-byte logical blocks: (4.19 MB/4.00 MiB)

You can see here that the device is a 4MB one, so download the 4MB update, not the 2MB update. Extract it, and copy it to `firmware/update.upd`:

    % 7z x Advantage2_1.0.521_4MB_us.zip
    % sudo mount -o "uid=$(id -u)" /dev/sdb /mnt/usb
    % cp Advantage2_1.0.521_4MB_us.upd /mnt/usb/firmware/update.upd
    % sudo umount /mnt/usb

You can now press Program + F1 to unmount the virtual drive again, followed by Program + Shift + U to do the update. Don't touch anything for 60 seconds, just to be safe, then press the "keypad" key and check if the LED comes on to check if the keyboard is back in operation.

All going well, you should now be able to press Program + Esc again in your dumping ground of choice, and see that everything was upgraded:

    % cat >/dev/null
    Model> Advantage2
    Firmware> 1.0.521.us (4MB), 06/25/2020
    Active layout file> qwerty.txt
    Thumb keys mode> none
    Macro play speed> off=0, slow=1, normal=3, fast=9> 3
    Status report play speed> off=0, slow=1, normal=3, fast=4> 3
    Keyclick status> on
    Toggle tone status> on
    Stored macros> 0
    Keys remapped> 7

## Getting rid of the annoying sounds

After doing that, you'll probably notice that there is now an annoying clicking sound, if you hadn't already noticed it before the update. As a bonus, there's even a really annoying beep! What value. You can disable those with Program + F8 and Program + Shift + F8 respectively.

## Scroll lock shutdown

For reasons I don't quite understand<sup>†</sup>, Scroll Lock on my model sends an `XF86PowerOff` keysym, which is hilarious when I press Scroll Lock by accident and my computer turns off. If this happens to you as well -- please tell me about it, because nobody else seems to have this issue and I think I'm going insane -- and then you can rebind Scroll Lock by doing Program + F12, press Scroll Lock, press Scroll Lock again, and then pressing Program to rebind the key. Now Scroll Lock should actually operate... Scroll Lock. Go figure.

<small><sup>†</sup> [Dan Kessler](http://www.dankessler.me/) sent me an e-mail (thanks!) noting this is documented [on Kinesis' website](https://kinesis-ergo.com/support/advantage2/) (but apparently not in the actual manual...): "The keypad = key becomes a Mac keypad = key and Scroll lock initiates the shutdowndialogue (sic) (caution: on a PC this leads to an immediate shutdown!)" </small>

## For tiling window manager users: Mac mode

The Advantage 2 has a few quick rebindings which can be useful. The bindings are as follows, from [here](https://kinesis-ergo.com/support/advantage/):

- To enter Windows Mode, press and hold the equals key and tap the letter “w” (=w). The top four thumb keys while in Windows mode, from left to right, are: Ctrl, Alt, Windows, Ctrl.
- To enter Mac Mode, press and hold the equals key and tap the letter “m” (=m). The top four thumb keys while in Mac mode, from left to right are: Command, Option, Ctrl, Command.
- To enter PC Mode, press and hold the equals key and tap the letter “p” (=p). The top four thumb keys while in PC mode, from left to right are: Ctrl, Alt, Alt, Ctrl.

"Option" here means Alt, and "Command" means "Super" (or the "Windows key"), just in Apple's reworded terminology.

Mac mode, despite its name, is what I found most useful for my tiling window manager setup with dwm. Most programs do not bind anything with the Super key, so that's a good one to use for window management. As such I have dwm configured to use Super as the modifier for most commands related to window and launcher management: moving, closing, launching applications, etc.

I also use Alt as the modifier in individual applications where there are separate tabs. For example, in Irssi, I use Alt + <Letter> to navigate by named channels -- Alt + v to navigate to ##vim on Freenode for example.

Mac mode sets these up reasonably by default, in a similar way to how you'd use them on a regular keyboard. I found it the most intuitive if you have to switch back and forth between "normal" layout keyboards and the Advantage 2, since you'd usually access those keys with your left thumb anyway.

## Caps -> control

You'll probably notice that this leaves us without a control key easily accessible by the left hand, which is kind of important especially for things like games. You can either rebind Caps to Control using the rebinding method shown earlier, or use a method in your operating system. I prefer the latter, because then I can apply it to other keyboards I have as well, which otherwise might not have rebinding support.

For example, on X11, you can use something like the following:

    % cat /etc/X11/xorg.conf.d/00-keyboard.conf
    Section "InputClass"
        Identifier "system-keyboard"
        MatchIsKeyboard "on"
        Option "XkbOptions" "ctrl:nocaps"
    EndSection

...and on Windows, you can use the following as a registry file (requires reboot):

    Windows Registry Editor Version 5.00

    [HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Keyboard Layout]
    "Scancode Map"=hex:00,00,00,00,00,00,00,00,02,00,00,00,1d,00,3a,00,00,00,00,00

This helpfully will apply this to all keyboards, not just the Advantage 2.

## Gaming

You should already be able to have a reasonably good time with what I've mentioned thus far, but there's one fairly major thing that's somewhat necessary for gaming: the space bar. In many games you can rebind it (for example, if it's "jump" or "climb" or similar), and if you're just starting out with the Advantage 2, you might find it intuitive just to remap Space to Backspace and vice-versa -- but as someone who used the Advantage for a long time at work and has only now transitioned to gaming with it, I found globally changing Backspace to Space and vice-versa just too jarring for my muscle memory.

If you can rebind it in all games you care about, I'd do that first. However, there are games like Watch Dogs 2 which allow you to rebind _most_ of the cases where Space is used, but not all (in WD2's case, it's for the hacking sequences where option 4 is always mapped to Space, and cannot be changed).

As such, I have a little [AutoHotkey](https://www.autohotkey.com/) script which runs when I'm in Watch Dogs 2 which maps Space to Backspace:

{% highlight ahk %}
GroupAdd, Games, ahk_exe WatchDogs2.exe

#If WinActive("ahk_group Games")
Space::Backspace
Backspace::Space
#If
{% endhighlight %}

For each game you want to add, you can just add another line to the group. If the executable name isn't stable or is not unique, you can also add an `ahk_class` match to the group, finding the right value using Window Spy which comes with AutoHotkey:

![Window Spy](/images/blog/ka2/windowspy.png)
