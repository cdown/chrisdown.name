---
layout: post
title: Moving to TeamCity from Jenkins
---

At [RMG][rmg], we're starting to migrate from using [Jenkins][jenkins], to
[TeamCity][teamcity]. My experiences using Jenkins for small projects have been
good in the past (although I have switched pretty much everything on GitHub to
use [Travis][travis] now), but these have mostly been projects where only me
and another few people are working on the codebase. My experience at RMG has
shown me that Jenkins can actually be a real pain in the ass when you have a
moderately large team working on a humungous code base. Some specific
annoyances:

- Jenkins handles inter-branch merges very badly. Merged a branch that contains
  commits by others? Expect them to get an e-mail about the state of your
  branch. TeamCity has a lot of options for notifications, and doesn't make
  assumptions about who owns a branch. You tell it what to notify you for, with
  extreme granularity (if you want it). This works a lot better for me.
- Jenkins has no concept of a "branch". This can result in absolute chaos if
  you have a workflow that depends on lots of short lived branches.
- When I'm doing a release, I want to be able to easily jump the queue to run
  all the tests. In Jenkins, you have to rudely kick other people off (which
  often results in angry e-mails to the dev list because you stopped the builds
  for a branch...). In TeamCity, you can just ask it to jump the queue
  without affecting anyone else.
- Build chains are a part of TeamCity from the ground up, in Jenkins, it is an
  afterthought (this is extremely useful when scheduling, for example, a
  "releasable" suite).
- The Jenkins UI has a face that only a mother could love, and doesn't get to
  the point. TeamCity on the other hand is extremely clear, and gets out of
  your way (although I wish it wasn't as easy to click "run" when I actually
  want to click "..." to schedule a build of a specific branch).
- Jenkins makes me feel attached to test suites, and not my commits. This is a
  quite severe UX problem. The last 5 builds passed, so you get a nice sunny
  icon. Good, but that doesn't tell me anything at all, since we don't
  release/test branches in a linear fashion (like you usually would on a
  smaller project).
- Users can take responsibility for tests in TeamCity. I don't think you can do
  this in Jenkins.

[Kenneth Reitz][reitz] once said the following (in [Python for Humans][pfh]):

> If you have to refer to the documentation every time you use a module, find
> or build a new module.

Any time I want to do anything remotely complex in Jenkins, I have to consult
the documentation. So far in TeamCity, I have just winged it based on interface
alone, and it's gone pretty well.

There are supposedly more advanced features in Jenkins that don't exist in
TeamCity (yet), but I don't think we use them. I'll quit happily take
simplicity and ease of use over advanced functionality that I have yet to have
use for.

I am possibly in the "fluffy cloud" stage of adopting a new technology right
now, so maybe I'm being too nice in some regards. I'll undoubtedly revisit
TeamCity in the future.

[jenkins]: http://jenkins-ci.org/
[teamcity]: http://www.jetbrains.com/teamcity/
[travis]: https://travis-ci.org/
[reitz]: http://kennethreitz.org/projects/
[pfh]: http://python-for-humans.heroku.com/
[rmg]: {{ site.links.rmg }}
