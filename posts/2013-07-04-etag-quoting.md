---
layout: post
title: ETag quoting
---

One of the nice things about ETags is that while `Last-Modified` has second
granularity, ETags have an infinite resolution (well, up to the point at which
you get a 413). In some cases (like, for example in our case with dynamic
generation) being able to represent cache status with a hash of the data is
much easier than storing last modified data, because it doesn't require storing
a cache on the server (instead, you just return a 403).

At work, we've been having some issues with ETags being stripped by upstream
providers when using gzip encoding, so today I took a look at our
implementation. We're undoubtedly not the first to make this mistake, so
hopefully this will save some others.

    $ curl -sD- -o /dev/null https://binary.com | grep -i ^etag:
    ETag: 949ffdddf907f30917d6d003538e0865

While this ETag may appear to be legal, it's actually illegal according to the
terms of [RFC 2616][etag-rfc], which specifies the format as:

>     entity-tag = [ weak ] opaque-tag
>     weak       = "W/"
>     opaque-tag = quoted-string

The semantics for `quoted-string` are denoted in [RFC 2822][quoting-rfc]:

> Strings of characters that include characters other than those allowed in
> atoms may be represented in a quoted string format, where the characters are
> surrounded by quote (DQUOTE, ASCII value 34) characters.

In our case, all that's required is surrounding the checksum with quotes to
make it legal. Your case may differ, though, check the two previously mentioned
RFCs. If you use weak ETags with the "W/" prefix, you should leave "W/"
unquoted and quote the remainder of the opaque-tag.

[etag-rfc]:    http://tools.ietf.org/html/rfc2616#section-3.11
[quoting-rfc]: http://tools.ietf.org/html/rfc2822#section-3.2.5
