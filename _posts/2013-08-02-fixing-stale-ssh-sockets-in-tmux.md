---
layout: post
title: Fixing stale SSH sockets in tmux
---

I use tmux on my devbox with ssh-agent forwarding, so that I can access our git
server transparently. Unfortunately, when reattaching to a tmux session, you'll
get the old SSH\_AUTH\_SOCK, and there's no immediate way to update this. I
wrote this function, which fixes this (run it after attaching):

{% highlight bash %}
update_auth_sock() {
    local socket_path="$(tmux show-environment | sed -n 's/^SSH_AUTH_SOCK=//p')"

    if ! [[ "$socket_path" ]]; then
        echo 'no socket path' >&2
        return 1
    else
        export SSH_AUTH_SOCK="$socket_path"
    fi
}
{% endhighlight %}

[Trent Lloyd suggests][status] an alternative method; symlinking the path
pointed to by SSH\_AUTH\_SOCK on login, and then changing it to point to the
symlink. As long as you are either only using a single key to log in and
forward to each server, or you have some way of determining the identity of the
key on the remote, this is a more easily automatable solution.

[status]: https://twitter.com/lathiat/status/466413801932603392
