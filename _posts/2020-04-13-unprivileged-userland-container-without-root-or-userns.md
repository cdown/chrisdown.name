---
layout: post
title: 'Unprivileged userland containers without root or userns'
---

(This post goes into some details about Arch Linux, but the general principles
apply the same to other Linux distributions, too.)

My old workhorse server that I've used for various tasks over the years is
slowly starting to become a bit of a bottleneck. I bought it just after I left
high school, so I had no money, and it really shows:

{% highlight bash %}
% grep -m2 -e 'model name' -e 'bugs' /proc/cpuinfo
model name      : Intel(R) Atom(TM) CPU N2800   @ 1.86GHz
bugs            :
{% endhighlight %}

You can't have any fancy CPU bugs if you didn't have any fancy features in the
first place! Maybe if Intel has enough CPU bugs in their CPU optimisations this
year, this will start to reach performance parity with Ice Lake ;-)

I'm still pretty cost-conscious for servers, since I mostly just use them for
VPN, occasional game server hosting, and as a temporary storage area if I need
to get data somewhere else (for example, when we want to share large amounts of
pictures with my wife's family, but all photo sharing services are either
blocked by the Great Firewall or are dog slow). As such, I recently opted to
try out using a much more powerful model on a shared basis for a while. Since
most of my needs are really bursty, this seems likely to work well, and still
be cost-effective.

Probably overkill, and definitely an upgrade from the Atom ;-)

{% highlight bash %}
% grep -m1 -e 'model name' /proc/cpuinfo
model name      : AMD EPYC 7571 32-Core Processor
{% endhighlight %}

Only one problem: on shared servers, you obviously don't get root access. I'm
pretty opinionated about my environment, and at a bare minimum I'd like to use
the following:

- pacman (and in general the Arch Linux repos with modern software)
- tmux
- [mosh](https://mosh.org/), for reliable shell access while roaming
- rsync
- zsh
- [asp](https://github.com/archlinux/asp)
- git
- vim

While a small number of these were available on the server, the server runs
Debian 8, and even those are really, really old, which is a problem for me
since I often use bleeding-edge features. Just as a basic example, take this 7
year old version of vim, which is missing features I use regularly:

      server % vim --version
      VIM - Vi IMproved 7.4 (2013 Aug 10, compiled Aug  2 2019 22:46:19)

If it was just one or two applications that were missing, I'd probably just try
to compile a more recent version from source and update it occasionally.
However, this was definitely more than one or two, and even if I did want to do
that, some of the libraries on Debian 8 are so old that some things won't even
link.

I thought I'd just install an Arch Linux container using
[bubblewrap](https://github.com/containers/bubblewrap) and get around this that
way, but here's what I found:

{% highlight bash %}
server % sysctl -n kernel.unprivileged_userns_clone
0
{% endhighlight %}

Oh dear. No unprivileged user namespaces means bubblewrap is a no-go, and
renders pretty much any standard containerisation out of luck.

This got me wondering how Android folks who run a Linux distribution on an
unrooted phone with the stock OS make this work, since often they are running
old kernels without things like user namespaces. After a bit of spelunking to
find out, I found out about the existence of
[proot](https://github.com/proot-me/proot), which provides userspace emulation
for bind mounts, chroot, and other cool things. Sounds intriguing! Even better,
they even list off some projects which are using them internally and one of
them caught my eye: [junest](https://github.com/fsquillace/junest), which is
listed on their page as helping you to "use Arch Linux on any Linux distro
without root access". Sounds like exactly what I need.

Setting up junest is easy (if you don't even have git to start out with,
extract one of the release tar.gzs):

{% highlight bash %}
server % git clone git://github.com/fsquillace/junest ~/.local/share/junest
server % ~/.local/share/bin/junest setup
{% endhighlight %}

(You can add ~/.local/share/junest/bin to your `$PATH`, but I don't intend to
invoke junest manually much, instead doing it through mosh, so I leave it alone
here.)

This will download the base image and dependencies. After that, we can start
up and get a shell and upgrade the packages (you can also directly `fakeroot`
in with `proot -f`):

      server % ~/.local/share/bin/junest proot
      proot % fakeroot
      proot # pacman -Syu
      :: Synchronizing package databases...
      [...]

### proot internals

I was kind of impressed this Just Worked™ out of the box without user, mount,
or any other kind of namespaces in play. Looking a bit at how proot works,
using [ptrace](http://man7.org/linux/man-pages/man2/ptrace.2.html), it
translates requests to the host kernel before it sees them. This is cool, but
is pretty expensive per-syscall, since ptrace is quite intrusive and slow,
causing the kernel to suspend the application twice (once on entry, once on
exit) each time the application issues a system call. For that reason, I
wouldn't recommend running any syscall-heavy workloads in a prooted container.

proot also has to handle bind mount emulation, which is quite expensive.
Especially if you intend to access things deep in the filesystem hierarchy,
proot issues one `lstat` for each level of the hierarchy as part of path
canonicalisation, which can be quite taxing. I think there are a few
optimisations that can potentially be done here, and if I run into this as an
actual problem I'll spend the time to send some patches upstream (or let me
know if you do, and maybe I can take a look).

One thing I sometimes do for things I can't otherwise reasonably run is
statically compile things I need inside the junest environment, and then run
them from the bare-metal environment. That means you usually get the best of
both worlds. :-)

## Making the experience better

At this point, you can turn off if just getting junest basically working was
all you wanted to do. In my case, I found that junest is great, but there are a
couple of things I'd like to sort out.

1. mosh needs to be told how to execute mosh-server in junest to connect, which
   requires some jiggery-pokery.
2. I'd like to know if I'm in junest or not in my shell prompt.

### Making mosh work inside junest

mosh comes with three binaries: `mosh-client`, which provides the client,
`mosh-server`, which provides the server, and `mosh`, which is what you usually
invoke that sshes to the server, runs mosh-server, gets the key, and
transparently runs mosh-client without requiring copying and pasting around
keys and ports.

To basically check that mosh worked and wasn't being blocked by any firewalls
or anything to start, you can run `mosh-server` manually:

    server % .local/share/junest/bin/junest proot -- mosh-server
    MOSH CONNECT [port] [key]

Now, on your local machine, you can run the following using that information:

    laptop % MOSH_KEY=[key] mosh-client [ip] [port]
    proot %

Success! We now have a mosh instance inside the proot. But how do we script
this? Well, if we look at `man mosh`, we see there is an option that might be
able to help us here, `--server`, which specifies the mosh server path on the
remote. But if you just plug in the following, which ostensibly seems like it
might work, it just hangs:

{% highlight bash %}
laptop % mosh --server '~/.local/share/junest/bin/junest proot -- mosh-server' remote.server
{% endhighlight %}

The reason for this is because, while `mosh-client` *does* successfully get the
MOSH_KEY, it also waits for `mosh-server` to detach, and thus the child process
to exit. However, the child process launched by `--server` never detaches,
since the proot session is being held open by that detached `mosh-server`.

To solve this, I wrote a simple shell script which forks `mosh-server` into the
background, reads its output and prints it to stdout, and exits when the
MOSH_KEY has been displayed.

{% highlight bash %}
#!/bin/bash

exec 3< <(~/.local/share/junest/bin/junest p -- mosh-server)

while IFS= read -r line <&3; do
    printf '%s\n' "$line"
    if [[ $line == 'MOSH CONNECT'* ]]; then
        # Allow mosh-client to continue
        break
    fi
done
{% endhighlight %}

Essentially, this opens an FD to a backgrounded mosh-server's standard output,
reads that FD, writes the data to stdout, and once it sees the `MOSH CONNECT`
line, terminates. `mosh-server` and the junest session live on in the
background.

If we name this script `mosh-server-junest` in the user's home directory, we
can now execute mosh like this (assuming you use `zsh`).

    laptop % mosh --server './mosh-server-junest' remote.server -- zsh -l
    proot %

Nice! You can now add an alias or a function in your shell to make this easier to
run, and we're done here. :-)

You need to specify the shell because, if zsh wasn't available on the base
server (which it wasn't in my case), it also won't be in /etc/shells, so you
can't `chsh` to it and allow mosh to use it by default.

### Making virtualisation clearer

Since I might sometimes want to use the shared server outside of junest for
operations which can't be done inside, I'd like the environment I'm in to be
clear when at a prompt.

Above I disambiguated the different shells running by prepending things like
"laptop", "server", or "proot" to the prompt, but in reality the "server" and
"proot" prompts probably look exactly the same by default.

One way to fix this is to change how your prompt looks depending on whether you
are in junest. Helpfully, junest exports `JUNEST_ENV=1` to its children, which
means you can simply check if that is set and modify your prompt accordingly.

In my specific case, you can see how I do that
[here](https://github.com/cdown/dotfiles/blob/52051ff/.config/shell/rc/prompt-functions#L63-L78):

{% highlight sh %}
_virt_prompt() {
    # We assume virtualisation won't change for one shell session
    if [ "$_VIRT" ]; then
        # Skip other branches
        :
    elif [ "${JUNEST_ENV:-0}" -eq 1 ]; then
        _VIRT=junest
    else
        _VIRT=$(systemd-detect-virt 2>/dev/null)
        if [ "$_VIRT" = none ]; then
            unset _VIRT
        fi
    fi

    colour_part 6 "$_VIRT"
}
{% endhighlight %}

(`colour_part` and the rest of the plumbing that eventually calls
`_virt_prompt` are in the above link.)

Now everything should be really transparent if you call your shell alias for
the `mosh` command above:

    cdown@laptop % msh
    cdown@server junest %

At this point, I'm pretty happy with this as an environment. It's fast, doesn't
cost much, and with some tweaking you can still have the userland you want.
