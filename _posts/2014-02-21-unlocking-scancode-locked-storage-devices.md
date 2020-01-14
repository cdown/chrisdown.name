---
layout: post
title: Unlocking storage devices locked using a password made of scancodes
---

Today marks the third time now that I have encountered problems unlocking solid
state drives locked by Dell staff laptops. The problem here lies in the way
that the BIOS interprets the data that constitutes your hard drive password.
Many BIOSes (I am ignorant of what UEFI does here, it may take a more
high-level approach) do not store your password in a character encoded format,
but instead as a sequence of [keyboard scancodes][scancodes].

This sometimes also has the consequence that passwords become case insensitive,
since scancodes are per-key (interestingly HP holds [a patent][patent] to store
case-related information for BIOS passwords, but I don't know if this also
relates to passwords it applies to hard disks, or even if they use the patent
right now).

You can convert your passwords to scancodes by using something like the
following (this only translates part of ASCII, and assumes a US keyboard
layout, but you get the idea):

{% highlight bash %}
<<< "The password" tr '[:upper:]' '[:lower:]' |
    tr '1234567890qwertyuiopasdfghjklzxcvbnm' '\2-\13\20-\31\36-\46\54-\62'
{% endhighlight %}

Note that if you are using a USB keyboard you [may be using a totally different
set of scancodes][usb], and will need to translate accordingly to that instead
(although some BIOSes map these to the more traditional scancodes, so maybe
not).

After you've determined the right scancodes, you can feed the output to
hdparm's `--security-unlock` or similar.

[patent]: http://www.google.com/patents/US7619544
[usb]: http://www.win.tue.nl/~aeb/linux/kbd/scancodes-14.html
[scancodes]: https://web.archive.org/web/20180526012114/http://www.barcodeman.com/altek/mule/scandoc.php
