---
layout: post
title: CloudFlare, gzip encoding, and ETags
excerpt: A discussion of the limitations of CloudFlare's ETag propagation.
---

According to an e-mail from Marty Strong from CloudFlare support, apparently
even weak etags are not supported when sending data using gzip encoding:

> Currently ETAGs are being stripped here due to the nature of how CloudFlare
> works. We do have a feature request for ETAGs to be handled differently that
> is being looked into by our engineering team.
>
> The reason here would be because requests may be altered when they are
> reverse proxied by CloudFlare, e.g. when any performance features are
> executed.
>
> The Gzipped content would be decompressed by us before these alterations and
> Gzipped again afterwards.

I agree that *strong* etags should not be used except for when bit-for-bit
equivalence is guaranteed, which it obviously isn't in this case, but stripping
weak etags seems a bit over the top when you're only using CloudFlare to
provide CDN features. Even if CloudFlare does change page details (which, from
a quick look using diff, it generally doesn't in our case) or change the
bit-for-bit equivalence of the gzipped bytes, it would still be semantically
equivalent enough to use weak etags in our case.
