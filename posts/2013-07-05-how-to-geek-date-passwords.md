---
layout: post
title: How-To Geek recommends using a timestamp for your passwords
---

As if How-To Geek had any credibility left, it seems they have begun to
recommend the following methods of generating a random password (quoting from
[the article][article]):

> This method uses SHA to hash the date, runs through base64, and then outputs
> the top 32 characters.
>
>     date +%s | sha256sum | base64 | head -c 32 ; echo
>
> And here’s the easiest way to make a password from the command line, which
> works in Linux, Windows with Cygwin, and probably Mac OS X \[...\]
>
>     date | md5sum

No. Stop. What the fuck is wrong with you.

[article]: http://www.howtogeek.com/howto/30184/10-ways-to-generate-a-random-password-from-the-command-line/
