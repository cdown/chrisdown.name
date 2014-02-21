---
layout: post
title: "Stop Mutt locking up with Gmail"
description: "tl;dr: Turn off imap_idle"
---

I've been experiencing random lockups with Gmail and Mutt ever since I switched
to using Google Apps for my domain. It seems the reason is that Gmail handles
IMAP idling in a really noncompliant way, which causes (due to Mutt's
synchronous IO, yuck) random lockups in the Mutt interface.

The solution is to turn off IMAP idling altogether (by unsetting imap\_idle,
which is the default in 1.5.21 unless you set it explicitly). I'm now using
these settings, which seem to work without freezes:

    set imap_keepalive = 300
    set mail_check     = 30
    set timeout        = 60
