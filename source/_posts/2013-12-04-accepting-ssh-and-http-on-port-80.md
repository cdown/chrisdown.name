---
layout: post
title: Accepting SSH and HTTP on port 80
description: "How to accept both SSH and HTTP connections on port 80"
---

I sometimes need to access the SSH server for this server from hotels, or other
locations with restrictive outgoing firewalls (here's looking at you, U of A).
I use nginx to serve HTTP(S) content on this website, which doesn't support the
CONNECT method, so that wasn't an option.

It's fairly trivial to do this with sslh (don't be fooled by the name, it can
also deal with HTTP):

    apt-get install sslh
    cat > /etc/default/sslh << 'EOF'
    RUN=yes
    DAEMON=/usr/sbin/sslh
    DAEMON_OPTS="--user sslh --listen 0.0.0.0:80 --ssh 127.0.0.1:22 --http 127.0.0.1:8080 --pidfile /var/run/sslh/sslh.pid"
    EOF

Now go into your nginx configs and change any instances of port 80 to port
8080, and check the config using `nginx -t`. If all is well, you can reload
nginx and start sslh:

    service nginx reload
    service sslh start

Now you should be able to access both SSH and HTTP on port 80:

    gopher$ curl chrisdown.name
    <html>
    <head><title>301 Moved Permanently</title></head>
    <body bgcolor="white">
    <center><h1>301 Moved Permanently</h1></center>
    <hr><center>nginx/1.4.4</center>
    </body>
    </html>
    gopher$ ssh -p80 chrisdown.name
    guthrie$
