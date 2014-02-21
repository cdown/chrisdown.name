---
layout: post
title: Fixing stale SSH sockets in tmux
description: When reattaching to tmux, you'll get the old SSH socket. This post shows you how to fix this.
---

I use tmux on my devbox with ssh-agent forwarding, so that I can access our git
server transparently. Unfortunately, when reattaching to a tmux session, you'll
get the old SSH\_AUTH\_SOCK, and there's no immediate way to update this. I
wrote this function, which fixes this (run it after attaching):

    update_auth_sock() {
        local socket_path="$(tmux show-environment | sed -n 's/^SSH_AUTH_SOCK=//p')"

        if ! [[ "$socket_path" ]]; then
            echo 'no socket path' >&2
            return 1
        else
            export SSH_AUTH_SOCK="$socket_path"
        fi
    }
