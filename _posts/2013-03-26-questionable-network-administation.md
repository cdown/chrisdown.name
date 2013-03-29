---
layout: post
title: A lesson in questionable network administration
---

I live in an apartment complex in Cyberjaya. The rent is expensive, the local
culture almost nonexistent, and the apartment wifi is, for lack of a better
word, questionable. If there's rain, it's probably not working. If there's a
thunderstorm (which is a lot of the time...), probably all of the APs are down.
It's not exactly a model of networking expertise.

I probe my servers fairly regularly to make sure nothing is amiss. Usually I do
this from work, but this time I did it from my apartment. One of the probes I
do is a port and fingerprint scan with nmap, which usually shows up just fine.
I know exactly how it should look, and I know exactly how it should *not* look.
For example, it should most definitely *not* look like this:

    Starting Nmap 6.25 ( http://nmap.org ) at 2013-03-26 21:29 MYT
    Nmap scan report for guthrie.illco.de (95.170.82.73)
    Host is up (0.13s latency).
    Not shown: 806 closed ports, 190 filtered ports
    PORT     STATE SERVICE VERSION
    53/tcp   open  domain  MikroTik RouterOS named or OpenDNS Updater
    80/tcp   open  http    nginx 1.2.7
    |\_http-methods: No Allow or Public header in OPTIONS response (status code 405)
    |\_http-title: Index of /
    222/tcp  open  ssh     OpenSSH 6.2 (protocol 2.0)
    | ssh-hostkey: 1024 09:0f:0b:27:89:c3:c8:cb:96:d8:3f:0e:1f:7e:7d:39 (DSA)
    | 2048 15:ec:85:b6:30:64:e5:a6:5c:2c:dd:2e:5d:b9:78:ba (RSA)
    |\_256 a9:c8:47:bc:a7:9e:43:7b:6a:95:05:19:77:40:eb:20 (ECDSA)
    2222/tcp open  ssh     OpenSSH 5.8p1 Debian 7ubuntu1 (Ubuntu Linux; protocol 2.0)
    | ssh-hostkey: 1024 ab:bd:17:10:7d:89:a1:f7:a4:44:f4:c0:24:b0:2e:fc (DSA)
    | 2048 5c:1c:7d:61:9a:be:2a:74:a8:69:7e:98:66:03:3e:12 (RSA)
    |\_256 07:58:17:60:ef:a5:17:de:15:bd:9d:cf:56:92:61:90 (ECDSA)
    Network Distance: 9 hops

I was sitting mouth agape as I read this output. I only run globally accessible
services on TCP ports 222 (SSH) and 80 (HTTP). What the hell are these other
two?!

The first thing I did was try to replicate this from another server I own. I
couldn't. hennepin (another server running illco.de) gave me back exactly the
result I was expecting when running an nmap on guthrie.illco.de. At this point,
I am scratching my head. A rootkit using iptables rules that only happen to
match me, and not hennepin? iptables -L shows nothing. I see nothing
suspicious. Then, I find something a little more revealing.

    ra:l:~# ping guthrie.illco.de
    PING guthrie.illco.de (95.170.82.73) 56(84) bytes of data.
    64 bytes from guthrie.illco.de (95.170.82.73): icmp\_seq=1 ttl=54 time=206 ms
    64 bytes from guthrie.illco.de (95.170.82.73): icmp\_seq=2 ttl=54 time=199 ms
    64 bytes from guthrie.illco.de (95.170.82.73): icmp\_seq=3 ttl=54 time=199 ms
    ^C
    --- guthrie.illco.de ping statistics ---
    3 packets transmitted, 3 received, 0% packet loss, time 2002ms
    rtt min/avg/max/mdev = 199.234/201.752/206.026/3.060 ms
    ra:l:~# hping -S -p 222 guthrie.illco.de
    HPING guthrie.illco.de (wlan0 95.170.82.73): S set, 40 headers + 0 data bytes
    len=44 ip=95.170.82.73 ttl=54 DF id=0 sport=222 flags=SA seq=0 win=14600 rtt=199.4 ms
    len=44 ip=95.170.82.73 ttl=54 DF id=0 sport=222 flags=SA seq=1 win=14600 rtt=206.9 ms
    len=44 ip=95.170.82.73 ttl=54 DF id=0 sport=222 flags=SA seq=2 win=14600 rtt=200.0 ms
    len=44 ip=95.170.82.73 ttl=54 DF id=0 sport=222 flags=SA seq=3 win=14600 rtt=204.0 ms
    ^C
    --- guthrie.illco.de hping statistic ---
    4 packets tramitted, 4 packets received, 0% packet loss
    round-trip min/avg/max = 199.4/202.6/206.9 ms
    ra:l:~# hping -S -p 2222 guthrie.illco.de
    HPING guthrie.illco.de (wlan0 95.170.82.73): S set, 40 headers + 0 data bytes
    len=44 ip=95.170.82.73 ttl=63 DF id=0 sport=2222 flags=SA seq=0 win=14600 rtt=3.1 ms
    len=44 ip=95.170.82.73 ttl=63 DF id=0 sport=2222 flags=SA seq=1 win=14600 rtt=1.5 ms
    len=44 ip=95.170.82.73 ttl=63 DF id=0 sport=2222 flags=SA seq=2 win=14600 rtt=1.8 ms
    len=44 ip=95.170.82.73 ttl=63 DF id=0 sport=2222 flags=SA seq=3 win=14600 rtt=1.4 ms
    len=44 ip=95.170.82.73 ttl=63 DF id=0 sport=2222 flags=SA seq=4 win=14600 rtt=1.5 ms
    ^C
    --- guthrie.illco.de hping statistic ---
    5 packets tramitted, 5 packets received, 0% packet loss
    round-trip min/avg/max = 1.4/1.9/3.1 ms

Notice the time-to-live and return trip times. Port 222, as expected, matches the TTL and RTT that ICMP shows, whereas port 2222 does not match either. Port 2222 is somehow much *closer* to my host than guthrie is. In fact, going by TTL alone, it seems that it is only one hop away.

Since one of the open ports is a DNS port, I start to have a suspicion that this might be a conflation of both guthrie and the machine hosting the local network DNS server.

    ca:l:~$ cat /etc/resolv.conf
    nameserver 10.200.126.254
    ca:l:~$ sudo nmap -A 10.200.126.254

    Starting Nmap 6.25 ( http://nmap.org ) at 2013-03-26 21:37 MYT
    Nmap scan report for 10.200.126.254
    Host is up (0.0021s latency).
    Not shown: 992 closed ports
    PORT     STATE SERVICE        VERSION
    53/tcp   open  domain         MikroTik RouterOS named or OpenDNS Updater

    [...]

    2222/tcp open  ssh            OpenSSH 5.8p1 Debian 7ubuntu1 (Ubuntu Linux; protocol 2.0)
    | ssh-hostkey: 1024 ab:bd:17:10:7d:89:a1:f7:a4:44:f4:c0:24:b0:2e:fc (DSA)
    | 2048 5c:1c:7d:61:9a:be:2a:74:a8:69:7e:98:66:03:3e:12 (RSA)
    |_256 07:58:17:60:ef:a5:17:de:15:bd:9d:cf:56:92:61:90 (ECDSA)

    [...]

    TRACEROUTE
    HOP RTT     ADDRESS
    1   2.12 ms 10.200.126.254

    OS and Service detection performed. Please report any incorrect results at http://nmap.org/submit/ .
    Nmap done: 1 IP address (1 host up) scanned in 165.52 seconds

Exactly the same host key, TTL, port, and RTT. Bingo.

This seems to only happens on certain hosts. For example, I can reproduce it
with guthrie.illco.de, but not hennepin.illco.de, even though the problem is on
the local network. Whoever set up this network gets a 10/10 for creative
mismanagement.

In summary, if anyone knows the network admin at the apartment complex I'm
staying at (here's looking at you, WCKL guys), please make sure they know what
they are doing before they touch a network again (or at least, until they stop
running their SSH daemon on ports >=1024... I mean, come on, really?!).
