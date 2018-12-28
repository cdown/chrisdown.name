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

**See [this
diff](https://github.com/systemd/systemd/compare/0d2d6fbf15c842b6f6579232ae5b11e491eccf0e...4f6f62e468db358a25abf51668c881105b35dc24)
for the code in question.**

cgroup controllers naturally end up with some overheads due to the extra
accounting they provide, and granularity of control they allow. While usually
this is minimal, for the CPU controller in particular it can become expensive,
and in most cases this is made more severe the more layers down the cgroup
hierarchy that the controller is enabled.

As such, it's important that we proactively try to remove controllers as soon
as they are not being used by the system.

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
needs to take. This allows us to make sure we are always proactively cleaning
up controllers after their use, which reduces the cost of controllers.

## Controllers can now be explicitly be disabled using DisableControllers=

**This expands on my earlier work to improve systemd's proactive releasing of
controllers from subtrees. See [this
commit](https://github.com/systemd/systemd/commit/c72703e26d21cb4994f21ae50c4e18675b02ded3)
for the code in question.**

As mentioned in the last item, some controllers (like the CPU controller) have
a performance cost that is non-trivial on certain workloads. While we're always
working to improve this, there will for some controllers always be some
overheads associated with the benefits gained from the controller. Inside
Facebook, the fix applied has been to disable the CPU controller forcibly with
`cgroup_disable=cpu` on the kernel command line.

This presents a problem: to disable or reenable the controller, a reboot is
required, but this is quite cumbersome and slow to do for many thousands of
machines, especially machines where disabling/enabling a stateful service on a
machine is a matter of several minutes or more. In general, it would be great
if we could just tell systemd to disable a controller within a subtree, or
tree-wide.

In versions of systemd prior to v240, systemd provides some configuration knobs
for these in the form of `[Default]CPUAccounting`, `[Default]MemoryAccounting`,
and the like. The limitation of these is that Default*Accounting is
overrideable by individual services, of which any one could decide to reenable
a controller within the hierarchy at any point just by using a controller
feature implicitly (eg. `CPUWeight`), even if the use of that CPU feature could
just be opportunistic. Since many services are provided by the distribution, or
by upstream teams at a particular organisation, it's not a sustainable solution
to simply try to find and remove offending directives from these units. This is
made even worse by systemd's previous lack of ability to effectively release
controllers from subtrees (see the previous item).

This commit presents a more direct solution -- a DisableControllers= directive
that forcibly disallows a controller from being enabled within a subtree. Child
cgroups will not be permitted to enable the disabled controller under any
circumstances, even explicitly.

This allows more granular positioning of controllers within the cgroup
hierarchy -- pointing the CPU controller to exactly where you need it, for
example, without affecting performance significantly if someone further down
the tree also requests it on your machines.

## The CPU controller is now not mandatory for CPU accounting

**See [this
diff](https://github.com/systemd/systemd/compare/09c984c6f76be170c00982fab806f85f2631ad2f...a88c5b8ac4df713d9831d0073a07fac82e884fb3)
for the code in question in systemd, and [this
commit](https://github.com/torvalds/linux/commit/041cd640b2f3c5607171c59d8712b503659d21f7)
from TJ for the work to make some counters controller-independent.**

As mentioned in the last two items, enabling the CPU controller can come with
some cost in some situations. As such, we try to avoid enabling it if it's not
really needed.

Tejun and I worked from kernelspace and userspace sides, respectively, to allow
consuming most of the key accounting metrics in a controller-independent way.
This means that, on systems with kernel 4.15+ and systemd v240+, we can now get
CPU accounting metrics extremely cheaply, which is quite important since it
forms one of the most important metrics people use in cgroups.

As an extra bonus, this means that we can now enable CPU accounting by default
on systems with 4.15+/v240+, which I did in [this
commit](https://github.com/systemd/systemd/commit/a88c5b8ac4df713d9831d0073a07fac82e884fb3).

# cgroup_no_v1=all now implies systemd.unified_cgroup_hierarchy=1

**See [this
commit](https://github.com/systemd/systemd/commit/5f086dc7db539974535ad093abdd32d47fbb035d)
for the code in question.**



# cgroup v2 device controller

https://github.com/systemd/systemd/pull/10062

# User sessions now actually have resource control properly applied

# MemoryMin/IODeviceLatencyTargetSec

# DeviceAllow= improvements

8e8b5d2e6d91180a57844b09cdbdcbc1fa466bfa

# Simplification of member mask

5af8805872809e6de4cc4d9495cb1a904772ab4e

