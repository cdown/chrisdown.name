---
layout: post
title: Moving to TeamCity from Jenkins
description: A comparison of my experiences with TeamCity to Jenkins after our migration.
---

At [RMG][rmg], we're starting to migrate from using [Jenkins][jenkins] to
[TeamCity][teamcity]. My experiences using Jenkins for small projects have been
good in the past (although I have switched pretty much everything on GitHub to
use [Travis][travis] now), but these have mostly been projects where only me
and another few people are working on the codebase. My experience at RMG has
shown me that Jenkins can actually be a real pain in the ass when you have a
moderately large team working on a humungous code base.

The biggest difference for me straight out of the box is that the user
experience on TeamCity is much better. I think this entire experience can be
summed up fairly well just by looking at their index pages (with the same
tests:
[TeamCity](http://farm4.staticflickr.com/3710/9725615004_604b6e51c8_o.jpg) and
[Jenkins](http://farm3.staticflickr.com/2889/9722386993_fee81b154a_o.jpg)).

Jenkins makes me feel attached to test suites, and not my commits. This is a
quite severe UX problem. The last 5 builds passed, so you get a nice sunny
icon. Good, but that doesn't tell me anything at all, since we don't
release/test branches in a linear fashion (like you usually would on a smaller
project).

Jenkins' UI doesn't get to the point. I don't care about executor status, when
things last succeeded or failed (since our branches are not in a linear order),
all I want to do is either look at a build, or (more likely) schedule one to
run on a certain branch. TeamCity makes this easy, click the "..." button on
the test suite you want to run (although I wish it wasn't so easy to click
"Run" by accident when doing this). Jenkins, however, doesn't.

[Kenneth Reitz][reitz] once said the following (in [Python for Humans][pfh]):

> If you have to refer to the documentation every time you use a module, find
> or build a new module.

Any time I want to do anything remotely complex in Jenkins, I have to consult
the documentation. So far in TeamCity, I have just winged it based on interface
alone, and it's gone pretty well.

Another thing which irritates me is Jenkins' poor branch handling -- Jenkins
handles inter-branch merges very badly. Merged a branch that contains commits
by others? Expect them to get an e-mail about the state of your branch.
TeamCity has a lot of options for notifications, and doesn't make assumptions
about who owns a branch. You tell it what to notify you for, with extreme
granularity (if you want it). This works a lot better for me.

When I'm doing a release, I want to be able to easily jump the queue to run all
the tests. In Jenkins, you have to rudely kick other people off (which often
results in angry e-mails to the dev list because you stopped the builds for a
branch...). In TeamCity, you can just ask it to jump the queue without
affecting anyone else.

There are supposedly more advanced features in Jenkins that don't exist in
TeamCity (yet), but I don't think we use them. I'll quit happily take
simplicity and ease of use over advanced functionality that I have yet to have
use for.

I am possibly in the "fluffy cloud" stage of adopting a new technology right
now, so maybe I'm being too nice in some regards. I'll probably revisit this
subject after we've used TeamCity for a while.

[jenkins]: http://jenkins-ci.org/
[teamcity]: http://www.jetbrains.com/teamcity/
[travis]: https://travis-ci.org/
[reitz]: http://kennethreitz.org/projects/
[pfh]: http://python-for-humans.heroku.com/
[rmg]: {{ site.links.rmg }}
