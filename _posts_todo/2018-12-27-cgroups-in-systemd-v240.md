---
layout: post
title: "What's new with cgroups in systemd v240"
---

Merry Christmas! This year has been really hectic and I've had nowhere near as
much time to write here as I would like. Nonetheless, since we just wrapped up
systemd v240, I thought I'd make a small post going over some of the new and
exciting stuff I and others have worked on in cgroups code on for this release,
for those who find the
[NEWS](https://github.com/systemd/systemd/blob/master/NEWS) file a bit too dry,
or are interested in more of the details behind the changes.

I'm mostly only including user-visible fixes or features here.

## Controllers are now disabled in subtrees more reliably when unneeded

See [this
diff](https://github.com/systemd/systemd/compare/0d2d6fbf15c842b6f6579232ae5b11e491eccf0e...4f6f62e468db358a25abf51668c881105b35dc24)
for the code in question.

### Why does this matter?

cgroup controllers naturally end up with some overheads due to the extra
accounting they provide, and granularity of control they allow. While usually
this is minimal, for the CPU controller in particular it can become expensive,
and in most cases this is made more severe the more layers down the cgroup
hierarchy that the controller is enabled.

As such, it's important that we proactively try to remove controllers as soon
as they are not being used by the system.

### Summary

Since the beginning of systemd, it has usually not been possible to proactively
disable controllers in subtrees when they become unused. The reason for this is
because enabling a controller always has to happen from the root of the
hierarchy to the eventual destination, but disabling must always happen from
the leaves to the root, as parents must always propagate controllers to their
children to be used.

This happens because of this code in `unit_realize_cgroup_now` (simplified for
clarity):

{% highlight c %}
static int unit_realize_cgroup_now(Unit *u, ManagerState state) {
    if (UNIT_ISSET(u->slice)) {
        if (unit_realize_cgroup_now(UNIT_DEREF(u->slice), state) < 0) {
            return r;
        }
    }

    /* Actually set up the cgroup */
}
{% endhighlight %}

This code results in `unit_realize_cgroup_now` recursively calling itself for
each parent, making sure that we apply this function to the root of the
hierarchy (which won't have `u->slice` set, so continues without recursion),
and then apply it from the root, to the intermediates, to the current cgroup in
question.

This works great for enabling controllers, but not so well for disabling.
Disabling a controller is more or less guaranteed to fail, as we will try to do
it from parent to child, but it must be disabled in the child first.

These two commits fix this by explicitly making systemd consult the surrounding
cgroups, and applying separate methodologies depending on the actions that it
needs to take.

## Controllers can now be explicitly be disabled using DisableControllers=

## The CPU controller is now not mandatory for CPU accounting

# cgroup_no_v1=all now implies systemd.unified_cgroup_hierarchy=1

# cgroup v2 device controller

https://github.com/systemd/systemd/pull/10062

# User sessions now actually have resource control properly applied

# MemoryMin/IODeviceLatencyTargetSec

# DeviceAllow= improvements

8e8b5d2e6d91180a57844b09cdbdcbc1fa466bfa

# Simplification of member mask

5af8805872809e6de4cc4d9495cb1a904772ab4e

