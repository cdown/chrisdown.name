---
layout: post
title: System alerting and graphing using atop, cron, and standard Unix utilities
---

Before we even get started, let's get one thing straight &mdash; you do not
want to use this kind of solution for your company's production servers. There
are a number of things that don't scale at all well here, not least:

- The graphing portion is pre-aggregated. which scales poorly. Christine
  Yen has written a couple
  ([1](https://honeycomb.io/blog/2016/12/the-problem-with-pre-aggregated-metrics-part-1-the-pre/),
  [2](https://honeycomb.io/blog/2016/12/the-problem-with-pre-aggregated-metrics-part-2-the-aggregated/))
  of pretty great explanations of why this doesn't work so well.
- E-mail alerts suck. What sucks even more is not having them deduplicated when
  shit hits the fan. What sucks *even* more is having no sense of priority.
  E-mail alerting with no deduplication or priorities: not even once (well,
  except for in this tutorial).

So who is this tutorial for, then? Well, if you have a hobby server, or a
couple of personal servers like I do w
