---
layout: post
title: '"1195725856" and other mysterious numbers'
redirect_from:
  - 2020/01/13/1195725856-other-mysterious-numbers.html
  - "1195725856"
---

Last week was the final week for this half's performance review at Facebook,
where we write summaries of work and impact we and our peers had over the last
half year. Naturally, that can only mean one thing: the entire company trends
towards peak levels of procrastination, doing literally anything and everything
to avoid the unspeakable horror of having to write a few paragraphs of text.

My personal distraction of choice a few days before the deadline was looking at
lines like this, spamming from some hosts serving NFS traffic:

    RPC: fragment too large: 1195725856
    RPC: fragment too large: 1212498244

Let's take a look at the kernel code responsible for generating this warning.
Grepping for "fragment too large" shows it comes from [`svc_tcp_recv_record` in
net/sunrpc/svcsock.c](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/net/sunrpc/svcsock.c?h=v5.4#n943):

{% highlight c %}
if (svc_sock_reclen(svsk) + svsk->sk_datalen >
                            serv->sv_max_mesg) {
    net_notice_ratelimited(
        "RPC: fragment too large: %d\n",
        svc_sock_reclen(svsk));
    goto err_delete;
}
{% endhighlight %}

So we're erroring out because we got passed some message which is beyond
`sv_max_mesg`, cool. But where does this come from? Looking at
`svc_sock_reclen` shows the following:

{% highlight c %}
static inline u32 svc_sock_reclen(struct svc_sock *svsk)
{
    return ntohl(svsk->sk_reclen) & RPC_FRAGMENT_SIZE_MASK;
}
{% endhighlight %}

`ntohl` converts a uint from network byte ordering to the host's byte ordering.
The bitwise `AND` with `RPC_FRAGMENT_SIZE_MASK` results in only some of the
data being retained, and looking at the definition show us how many bits that
is:

{% highlight c %}
#define RPC_LAST_STREAM_FRAGMENT (1U << 31)
#define RPC_FRAGMENT_SIZE_MASK   (~RPC_LAST_STREAM_FRAGMENT)
{% endhighlight %}

Okay, so we will only keep the first 31 bits and zero out the high bit, since
`~` is bitwise `NOT`.

That means that these numbers come from the first four bytes of the fragment,
omitting the final highest bit, which is reserved to record whether the
fragment is the last one for this record (see
[`svc_sock_final_rec`](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/include/linux/sunrpc/svcsock.h?h=v5.4#n47)).
The fact that the error happens so early in fragment parsing in particular got
me thinking that the fragment may not be protocol-confirming in the first
place, since it's not like we got very far in processing at all, not even past
the first four bytes. So what *are* these first four bytes, then? Looking at
the numbers in hex shows something interesting:

{% highlight python %}
% python
>>> hex(1195725856)
'0x47455420'
>>> hex(1212498244)
'0x48454144'
{% endhighlight %}

These are all really tightly clustered, generally from 0x40 to 0x50, which
implies there might actually be some semantic meaning per-byte. And since these
are `char`-sized, here's a guess about what might be encoded in them...

{% highlight python %}
>>> '\x47\x45\x54\x20'
'GET '
>>> '\x48\x45\x41\x44'
'HEAD'
{% endhighlight %}

Oh dear. Somebody is sending HTTP requests to NFS RPC, but at least we are
outright rejecting the fragments instead of actually allocating/dirtying a
gigabyte of memory.

Next up was finding out who's actually sending these requests. `rpcinfo -p`
shows NFS is listening on the default port, 2049, so we can set up a trap with
tcpdump like so:

    tcpdump -i any -w trap.pcap dst port 2049
    # ...wait for logs to appear again, then ^C...
    tcpdump -qX -r trap.pcap | less +/HEAD

From here, it was pretty easy to catch the origin of these requests by tracing
back to the origin host and service using the captured pcap data. After that
one can coordinate with the team responsible to work out what's actually going
on here, and avoid these errant packets being sent out in the first place. As a
bonus, you also get to learn more about parts of infrastructure you might
otherwise not interact with, which is always cool. :-)

Funnily enough, if you Google for these numbers you can find tons of threads
with people encountering them in the wild. Maybe we should start printing ASCII
in future in some of the error paths hit when all character values are between
0x0 and 0x7F, I'm sure it would help a lot of people realise what's going on
much more quickly. Maybe I'll send a patch upstream to do that in
`svc_tcp_recv_record` and a few other places in the kernel that directly parse
the first few data bytes from packets as an integer, let's see.

Here's a trivial program that can generate a bunch of other integers for HTTP
that might be of interest:

{% highlight c %}
#include <assert.h>
#include <byteswap.h>
#include <inttypes.h>
#include <limits.h>
#include <stdio.h>
#include <string.h>

static int system_is_little_endian(void) {
    static const int tmp = 1;
    return *(const char *)&tmp == 1;
}

#define print_reinterpreted_inner(type, fmt, bs_func, hdr)      \
    do {                                                        \
        if (strlen(hdr) >= sizeof(type)) {                      \
            type *_hdr_conv = (type *)hdr;                      \
            type _le, _be;                                      \
            if (system_is_little_endian()) {                    \
                _le = *_hdr_conv;                               \
                _be = bs_func(*_hdr_conv);                      \
            } else {                                            \
                _le = bs_func(*_hdr_conv);                      \
                _be = *_hdr_conv;                               \
            }                                                   \
            printf("%.*s,%zu,%" fmt ",%" fmt "\n",              \
                   (int)strlen(hdr) - 2, hdr, sizeof(type),     \
                   _le, _be);                                   \
        }                                                       \
    } while (0)

#define print_reinterpreted(bits, hdr)                          \
    print_reinterpreted_inner(uint##bits##_t, PRIu##bits,       \
                              bswap_##bits, hdr)

int main(void) {
    const char *methods[] = {"GET",   "HEAD",   "POST",
                             "PUT",   "DELETE", "OPTIONS",
                             "TRACE", "PATCH",  "CONNECT"};
    size_t i;

    printf("data,bytes,little-endian,big-endian\n");

    for (i = 0; i < sizeof(methods) / sizeof(methods[0]); i++) {
        int ret;
        char hdr[16];
        unsigned const char *check =
            (unsigned const char *)methods[i];

        /* No high bit, so no need to check signed integers */
        assert(!(check[0] & (1U << (CHAR_BIT - 1))));

        ret = snprintf(hdr, sizeof(hdr), "%s /", methods[i]);
        assert(ret > 0 && ret < (int)sizeof(hdr));

        print_reinterpreted(64, hdr);
        print_reinterpreted(32, hdr);
        print_reinterpreted(16, hdr);
    }
}
{% endhighlight %}

And the results:

| data    | bytes | little-endian       | big-endian          |
|---------|-------|---------------------|---------------------|
| GET     | 4     | 542393671           | 1195725856          |
| GET     | 2     | 17735               | 18245               |
| HEAD    | 4     | 1145128264          | 1212498244          |
| HEAD    | 2     | 17736               | 18501               |
| POST    | 4     | 1414745936          | 1347375956          |
| POST    | 2     | 20304               | 20559               |
| PUT     | 4     | 542397776           | 1347769376          |
| PUT     | 2     | 21840               | 20565               |
| DELETE  | 8     | 3395790347279549764 | 4919422028622405679 |
| DELETE  | 4     | 1162626372          | 1145392197          |
| DELETE  | 2     | 17732               | 17477               |
| OPTIONS | 8     | 2329291534720323663 | 5715160600973038368 |
| OPTIONS | 4     | 1230262351          | 1330664521          |
| OPTIONS | 2     | 20559               | 20304               |
| TRACE   | 4     | 1128354388          | 1414676803          |
| TRACE   | 2     | 21076               | 21586               |
| PATCH   | 4     | 1129595216          | 1346458691          |
| PATCH   | 2     | 16720               | 20545               |
| CONNECT | 8     | 2329560872202948419 | 4850181421777769504 |
| CONNECT | 4     | 1313754947          | 1129270862          |
| CONNECT | 2     | 20291               | 17231               |

As expected, if you Google for most of these numbers, you can find an endless
supply of questions mentioning them in error messages (some previously
unidentified examples which I replied to:
[1](https://github.com/inconshreveable/ngrok/issues/545),
[2](https://stackoverflow.com/a/59730358/945780),
[3](https://github.com/ehang-io/nps/issues/315)).

Hopefully this post will help people find their *real* problem -- using the
wrong protocol -- more quickly in future. In particular, if your affected
application crashed due to ENOMEM/"Out of memory", please especially consider
submitting a patch to clamp the size to some reasonable maximum :-)
