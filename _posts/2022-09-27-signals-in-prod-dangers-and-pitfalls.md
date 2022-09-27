---
layout: post
title: "Signals in prod: dangers and pitfalls"
---

Link: [Meta developer blog](https://developers.facebook.com/blog/post/2022/09/27/signals-in-prod-dangers-and-pitfalls/)

---

As part of my work improving our production stability at
[Meta](https://meta.com), one of the areas that I am frequently involved in is
in improving how operating system concepts and primitives are being used (or
indeed misused).

Most of the blog posts that I write on this personal website have to be
relatively sanitised: I generally can't talk about details of real incidents or
internal details, which sometimes makes selling the point somewhat harder.

Thankfully, writing on the engineering blog lifts most of those restrictions,
so here are details of a real incident which happened at Meta in the recent
past where Unix signals caused a particularly nasty service outage.

I hope you enjoy the article -- hopefully it will be of use to those of you
using or managing Linux and other Unix-like systems, and also to those who
build applications for them. :-)
