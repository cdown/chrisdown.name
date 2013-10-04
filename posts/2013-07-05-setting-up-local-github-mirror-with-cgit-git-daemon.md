---
layout: post
title: Setting up a local GitHub mirror with cgit, gh-mirror, and git daemon
excerpt: Discover how to easily set up a local GitHub mirror.
---

I just finished setting up [a local GitHub mirror][local-git] so that I can
have a local copy of my GitHub repositories on this server at all times. I
figured since I have them here, I might as well also make them available to the
public on this server. This post covers setting up the mirroring (using
[gh-mirror][gh-mirror]), a web interface (using [cgit][cgit] through
[nginx][nginx]), and a clone interface (using [git-daemon][git-daemon]).

## Setting up cgit

Replace "chrisdown.name" with the server you will be running git-daemon on.

    apt-get install fcgiwrap spawn-fcgi git build-essential

    git clone git://git.zx2c4.com/cgit /usr/src/cgit

    cd /usr/src/cgit
    git submodule update --init

    cat > cgit.conf << 'EOF'
    prefix = /srv/http/cgit
    CGIT_SCRIPT_PATH = $(prefix)
    CGIT_DATA_PATH = $(prefix)
    EOF

    make install

    cat > /etc/cgitrc << 'EOF'
    root-desc=Mirror of https://github.com/cdown
    virtual-root=/
    logo=/cgit.png
    css=/cgit.css
    scan-path=/srv/git
    remove-suffix=1
    clone-prefix=git://chrisdown.name
    EOF

If everything went well, executing /srv/http/cgit/cgit.cgi should output some
HTML.

## Setting up nginx

Replace "git.chrisdown.name" with your domain.

    apt-get install nginx

    cat > /etc/nginx/sites-available/git.chrisdown.name << 'EOF'
    server {
        server_name git.chrisdown.name;
        root /srv/http/cgit;

        location / {
            try_files $uri @cgit;
        }

        location @cgit {
            index cgit.cgi;
            fastcgi_param SCRIPT_FILENAME $document_root/cgit.cgi;
            fastcgi_pass unix:/var/run/fcgiwrap.socket;
            fastcgi_param HTTP_HOST $server_name;
            fastcgi_param PATH_INFO $uri;
            fastcgi_param QUERY_INFO $uri;
            include "fastcgi_params";

        }
    }
    EOF

    ln -s /etc/nginx/sites-{available,enabled}/git.chrisdown.name

    service nginx reload

You should now get a cgit page at git.chrisdown.name that proudly displays "no
repositories found" (assuming you have no repositories in /srv/git already).

## Clone repositories

I wrote a script called [gh-mirror][gh-mirror] that takes care of most of the
work for you.

This will mirror from GitHub every 5 minutes. Replace "cdown" with your
username.

    useradd -m -d /srv/git -r -s "$(type -p git-shell)" git

    wget -O /usr/local/bin/gh-mirror https://raw.github.com/cdown/gh-mirror/master/gh-mirror
    chmod a+x /usr/local/bin/gh-mirror

    cat > /etc/cron.d/github-mirror << 'EOF'
    PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
    */5 * * * * git cd && gh-mirror cdown
    EOF

In the next 5 minutes, you should see your public repositories on cgit.

You can also optionally initialise the last modified time to the time of the
last commit for each repository so that they don't all display the time at
which you first cloned for repos that you no longer commit to -- here's a
little script I wrote. The source shows that if it fails to find
info/web/last-modified, then head/refs/\[default branch\], then it looks at
packed-refs. As such, we update the mtime of packed-refs to match the time of
the last commit.

    #!/bin/bash
    for dir in /srv/git/*.git; do
        commit_time="$(GIT_DIR="$dir" git --no-pager log -1 --format='%ai')"
        touch -d "$commit_time" "$dir/packed-refs"
    done

## git-daemon

You'll want to have an init script to run git-daemon. I wrote this one up, I
don't know if it's totally compliant with the Debian packaging guidelines, but
I tried to follow it as closely as I could.

    useradd -m -d /srv/git -r -s "$(type -p git-shell)" git-ro

    cat > /etc/init.d/git-daemon << 'EOF'
    #!/bin/bash

    ### BEGIN INIT INFO
    # Provides:        git-daemon
    # Required-Start:  $network
    # Required-Stop:   $network
    # Default-Start:   2 3 4 5
    # Default-Stop:
    # Short-Description: Git daemon
    ### END INIT INFO

    PATH=/sbin:/bin:/usr/sbin:/usr/bin

    . /lib/lsb/init-functions

    pid_file=/run/git-daemon.pid
    daemon=(
        "$(type -p git)" -- daemon \
            --{user,group}=git-ro \
            --reuseaddr \
            --pid-file="$pid_file" \
            {--base-path=,}/srv/git/
    )

    case "$1" in
        start)
            log_daemon_msg "Starting Git daemon" "git-daemon"
            start-stop-daemon --start --background --quiet --oknodo \
                --pidfile "$pid_file" \
                --exec "${daemon[@]}"
            log_end_msg "$?"
            ;;
        stop)
            log_daemon_msg "Stopping Git daemon" "git-daemon"
            start-stop-daemon --stop --quiet --oknodo --pidfile "$pid_file"
            log_end_msg "$?"
            rm -f "$pid_file"
            ;;
        restart|reload|force-reload)
            "$0" stop && "$0" start
            ;;
        status)
            if { kill -0 "$(<"$pid_file")" ; } >/dev/null 2>&1; then
                echo "git-daemon is running"
            else
                echo "git-daemon is not running"
            fi
            ;;
        *)
            echo "Usage: $0 {start|stop|restart|status}"
            exit 2
            ;;
    esac
    EOF

    chmod a+x /etc/init.d/git-daemon
    insserv git-daemon
    service git-daemon start

You should now be able to clone:

    $ git clone git://chrisdown.name/osmo.git
    Cloning into 'osmo'...
    remote: Counting objects: 660, done.
    remote: Compressing objects: 100% (336/336), done.
    remote: Total 660 (delta 279), reused 660 (delta 279)
    Receiving objects: 100% (660/660), 161.11 KiB | 0 bytes/s, done.
    Resolving deltas: 100% (279/279), done.
    Checking connectivity... done

[gh-mirror]:  https://github.com/cdown/gh-mirror
[cgit]:       http://git.zx2c4.com/cgit/
[local-git]:  {{ site.links.internal-git }}
[git-daemon]: http://git-scm.com/book/en/Git-on-the-Server-Git-Daemon
[nginx]:      http://nginx.org
