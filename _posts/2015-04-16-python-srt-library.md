---
layout: post
title: A new, simple Python SRT library
---

For the past few months I've been working on a new, simple SRT library. I
previously used [pysrt][], but its reinvention of the wheel in implementing new
types and representing subtitle metadata make it too difficult to use for
complex processing.

I don't think that such a simple format should be represented through such
complex abstractions, which is why I created [srt][].

srt has been out for a few months now as a work in progress, but as we get
closer to 1.0, I'm beginning to use it more and more in my daily life. This
kind of daily use with all sorts of subtitles from all sorts of places has
generally left it fairly battle hardened, and left me more confident that it
will be able to suit your needs when dealing with SRTs found in the wild.

There is (mostly inline) documentation available on [ReadTheDocs][], including
a [quickstart][]. If you have any suggestions for improvement, feel free to let
me know using my contact details, which you can find at the bottom of the page.

I also have a few tools that I personally use in a separate repo called
[srt-tools][]. These tools might help you to understand the API even further
through practical examples, and you might find them useful when dealing with
SRT files, too. I think you'll find that dealing with the library's API is
quite pleasant, and doesn't get in your way.

Happy subtitling.

[srt]: https://github.com/cdown/srt
[pysrt]: https://github.com/byroot/pysrt
[quickstart]: http://srt.readthedocs.org/en/latest/quickstart.html
[ReadTheDocs]: http://srt.readthedocs.org/en/latest/
[srt-tools]: https://github.com/cdown/srt-tools
