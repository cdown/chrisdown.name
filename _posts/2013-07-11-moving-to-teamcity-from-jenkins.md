---
layout: post
title: Moving to TeamCity from Jenkins
---

At work, we're slowly migrating from [Jenkins][] to [TeamCity][] in the hope of
ending some of our recurring problems with continuous integration. My use of
Jenkins prior to this job has been almost strictly on a personal basis,
although I pretty much only use [Travis][] nowadays.

The biggest difference upon initial inspection is that TeamCity is far more
focused on validating individual commits rather than certain types of tests.
Jenkins' front page presents information that is simply not useful in a
non-linear development environment, where people are often working in vastly
different directions. How many of the previous tests passed/failed is not
really salient information in this kind of situation.

Running specific tests for individual commits on TeamCity is far more trivial
in terms of interface complexity than Jenkins. TeamCity just involves clicking
the "..." button in the corner on any test type (although I wish it wasn't so
easy to click "Run" by accident).

I generally find TeamCity a lot more intuitive than Jenkins out of the box.
There's a point at which you feel that if you have to scour the documentation
to do anything remotely complex in an application, you're dealing with a bad
interface.

One disappointing thing in both is that inter-branch merges improperly trigger
e-mails to unrelated committers. I suppose it is fairly difficult to
determine who to notify about failure in situations like these, though. It
seems like TeamCity pulls up the first parent of the merge commit and sends the
e-mail to them, when in reality it's usually the merge author that should be
getting that information. Maybe I'm just ignorant of where to find a setting to
change that behaviour.

Being able to jump the queue is useful when releasing. It requires a plugin to
do in a sane way in Jenkins, unless you're willing to kick everyone else out of
the queue. TeamCity can do it by default, and it's obvious how to do so when
scheduling the tests.

There are supposedly more advanced features in Jenkins that don't exist in
TeamCity (yet), but I don't think we use them.

[Jenkins]: https://jenkins.io
[TeamCity]: http://www.jetbrains.com/teamcity/
[Travis]: https://travis-ci.org/
