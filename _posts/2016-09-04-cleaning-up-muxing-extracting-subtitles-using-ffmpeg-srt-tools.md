---
layout: post
title: Cleaning, muxing, and extracting subtitles using ffmpeg and the Python srt library
---

I became a huge subtitle user when I met my wife. We both like to watch a lot
of non-English/non-Chinese movies, and while I use English subtitles, she
prefers to have subtitles in Chinese most of the time since she can read it
faster than English.

Over the years of doing this I've acquired quite a lot of knowledge in this
area, and built quite a few tools to help. This post is a way of introducing
them to the world, and hopefully it will help anyone in a similar predicament
to mine.

Things you will need:

- [ffmpeg][], a set of tools to manipulate multimedia data
- [srt][], a Python library and set of tools for dealing with SRT files
  (install with `pip install srt`)

[ffmpeg]: https://ffmpeg.org/
[srt]: https://github.com/cdown/srt

## Conversion from other formats to SRT

[SRT][] is by far my favourite subtitle format. Its spec has its oddities (not
least that there is no widely accepted formal spec), but in general if you
stick to the accepted commonalities of the format between media players, you'll
find it's not only simple, but easy to modify and script around.

If you have another format, like [SSA][], for example, you'll probably find
that [ffmpeg][] does a pretty good job converting it with `ffmpeg -i foo.ssa
foo.srt`.

[SRT]: https://matroska.org/technical/specs/subtitles/srt.html
[SSA]: https://matroska.org/technical/specs/subtitles/ssa.html

## Acquiring subtitles

I won't go into too much detail on this, since you probably will have good
enough luck Googling "\[movie\] \[language\] subtitle", but here are some
recommendations:

- If you want to extract existing subtitles that are already in your video file
  (for example, to mux them with other ones), see [Extracting subtitles from a
  video file](#extracting-subtitles-from-a-video-file), below. This is often
  the best way since these have already been checked to work with the version
  of the movie you have.
- For Chinese subtitles, [Shooter][] is pretty good and frequently updated.
- Otherwise, Google "\[movie\] \[language\] subtitle".

[Shooter]: https://assrt.net

## Fixing encoding problems

All of the SRT tools take UTF-8 as input, since it's a sane, reasonable
encoding across the board. You may find that your subtitles are not encoded as
UTF-8 and require conversion.

Let's take Chinese subtitles as an example, as they often use country-preferred
encoding schemes. Chinese subtitles usually come encoded as [Big5][] or
[GB18030][].

I personally find that [enca][] is pretty good at detecting the encoding and
converting it appropriately. You can call it as `enca -c -x UTF8 -L <language
iso code> <sub>` to convert subtitles to UTF-8 based on encoding detection
heuristics, regardless of their source encoding.

[Big5]: https://en.wikipedia.org/wiki/Big5
[GB18030]: https://en.wikipedia.org/wiki/GB_18030
[enca]: https://github.com/nijel/enca

## Extracting subtitles from a video file

I'll assume you're using a [Matroska][] file, since they're so popular
nowadays, but much of this will also apply elsewhere.

Inside an MKV file are multiple streams. They contain things like the video
data, the audio data, and subtitles. You can list them with [ffprobe][]:

    % ffprobe ES.mkv |& grep Stream
        Stream #0:0: Video: h264 (High), yuv420p(tv, bt709), 1024x554, SAR 1:1 DAR 512:277, 23.98 fps, 23.98 tbr, 1k tbn, 47.95 tbc (default)
        Stream #0:1(eng): Audio: ac3, 48000 Hz, 5.1(side), fltp, 448 kb/s (default)
        Stream #0:2(eng): Audio: aac (HE-AAC), 48000 Hz, stereo, fltp
        Stream #0:3(eng): Subtitle: subrip
        Stream #0:4(spa): Subtitle: subrip
        Stream #0:5(fre): Subtitle: subrip

Looking at the three streams marked "Subtitle", you can see that we have
English, Spanish, and French subtitles available in this MKV.

Say you want to extract the Spanish subtitle to an SRT file. When converting,
ffmpeg will pick the first suitable stream that it finds -- by default, then,
you will get the English subtitle. To avoid this, you can use `-map` to select
the Spanish subtitle for output.

In this case we know that the Spanish subtitle is stream 0:4, so we run this
command:

    % ffmpeg -i ES.mkv -map 0:4 ES-spanish.srt

We can see that the right subtitle has been selected:

    % cat ES-spanish.srt
    1
    00:01:34,579 --> 00:01:37,099
    <i>Tren a Montauk en la vía B.</i>

    2
    00:01:37,182 --> 00:01:41,522
    <i>Pensamientos al azar</i>
    <i>para el Día de San Valentín, 2004.</i>

We will use this subtitle for most of the subsequent examples.

[Matroska]: https://en.wikipedia.org/wiki/Matroska
[ffprobe]: https://ffmpeg.org/ffprobe.html

## Stripping HTML-like entities from subtitles

As you can see in the subtitle above, sometimes subtitles contain HTML
entities, like &lt;b&gt;, &lt;color&gt;, etc. These are not part of the SRT
spec, they remain to be interpreted by the media player. Since not all media
players support this sometimes they are just shown raw, which looks quite bad.

The srt project contains a tool to deal with this called [strip-html][]:

    % cat ES-spanish.srt
    1
    00:01:34,579 --> 00:01:37,099
    <i>Tren a Montauk en la vía B.</i>

    2
    00:01:37,182 --> 00:01:41,522
    <i>Pensamientos al azar</i>
    <i>para el Día de San Valentín, 2004.</i>

    % srt strip-html < ES-spanish.srt
    1
    00:01:34,579 --> 00:01:37,099
    Tren a Montauk en la vía B.

    2
    00:01:37,182 --> 00:01:41,522
    Pensamientos al azar
    para el Día de San Valentín, 2004.

[strip-html]: https://github.com/cdown/srt/blob/develop/srt_tools/srt-strip-html

## Correcting time shifts

Getting subtitles from the internet is an imperfect business. There are often a
few different packagings of a movie in different markets, some with different
intros, some from different original sources, etc. This can result in the
subtitles requiring some correction prior to use.

Your media player may contain some rudimentary controls to correct this at
runtime, which may suffice for fixed timeshifts, but for linear timeshifts and
cases where you need two sync two subtitles exactly prior to muxing, modifying
the SRT file directly is a good idea.

The srt project contains two tools to deal with this:

- [fixed-timeshift][], which shifts all subtitles by a fixed amount. For
  example, you want to shift all subtitles back 2.5 seconds to sync properly
  with your video.

      % srt fixed-timeshift --seconds -34.579 < ES-spanish.srt
      1
      00:01:00,000 --> 00:01:02,520
      <i>Tren a Montauk en la vía B.</i>

      2
      00:01:02,603 --> 00:01:06,943
      <i>Pensamientos al azar</i>
      <i>para el Día de San Valentín, 2004.</i>

- [linear-timeshift][], which takes two existing time points in the input, and
  scales all subtitles so that those time points are shifted to the correct
  values. For example, if you had three subtitles with times 1, 2, and 3, you
  set the existing times as 1 and 3, and you set the new times as 1 and 5, the
  new times for those subtitles would be 1, 3, and 5.

  On the command line, "f" means "from", "t" means "to", and the numbers are
  just the unique ID for each pair of times.

      % srt linear-timeshift --f1 00:01:30,000 --t1 00:00:00:00 --f2 00:01:40,000 --t2 00:01:00,000 < ES-spanish.srt
      1
      00:00:27,474 --> 00:00:42,594
      <i>Tren a Montauk en la vía B.</i>

      2
      00:00:43,092 --> 00:01:09,132
      <i>Pensamientos al azar</i>
      <i>para el Día de San Valentín, 2004.</i>

[fixed-timeshift]: https://github.com/cdown/srt-tools/blob/develop/fixed-timeshift
[linear-timeshift]: https://github.com/cdown/srt-tools/blob/develop/linear-timeshift

## Muxing subtitles together

The srt project contains a tool, [mux][], that takes multiple streams of SRTs
and muxes them into one. It also attempts to clamp multiple subtitles to use
the same start/end times if they are similar (by default, if they are within
600ms of each other), in order to stop subtitles jumping around the screen when
displayed.

Say we wanted to create Spanish/French dual language subs for this movie
(having already retrieved a suitable French subtitle in `ES-french.srt`).

    % cat ES-french.srt
    1
    00:01:34,579 --> 00:01:37,099
    <i>Le train pour Montauk</i>
    <i>sur la voie "B."</i>

    2
    00:01:37,182 --> 00:01:41,522
    <i>Idée diverses</i>
    <i>pour la Saint-Valentin, 2004.</i>

In that case, we'd run something like this:

    % srt mux --input ES-spanish.srt --input ES-french.srt 
    1
    00:01:34,579 --> 00:01:37,099
    <i>Tren a Montauk en la vía B.</i>

    2
    00:01:34,579 --> 00:01:37,099
    <i>Le train pour Montauk</i>
    <i>sur la voie "B."</i>

    3
    00:01:37,182 --> 00:01:41,522
    <i>Pensamientos al azar</i>
    <i>para el Día de San Valentín, 2004.</i>

    4
    00:01:37,182 --> 00:01:41,522
    <i>Idée diverses</i>
    <i>pour la Saint-Valentin, 2004.</i>

[mux]: https://github.com/cdown/srt/blob/develop/srt_tools/srt-mux


## Removing other languages from dual-language subtitles

This is easier for some languages than others. For example, it's easy to detect
and isolate lines containing CJK characters from lines containing (say)
English, since their range of characters tends not to intersect.

It's more difficult (and more error prone) to try to detect languages using
more advanced heuristics, but there are a few ways that you can do it using
`srt`.

`srt` has a program called [lines-matching][], to which you can pass an
arbitrary Python function that returns True if the line is to be kept, and
False otherwise. This means you can easily build your own heuristics for
language based detection, or anything else you want to isolate.

As an example, this is how you would isolate to Chinese lines using
[hanzidentifier][] (must be installed):

    % srt lines-matching -m hanzidentifier -f hanzidentifier.has_chinese

You can pass `-m` multiple times for multiple imports. `-f` is a function that
takes one argument, `line`. In this case, `hanzidentifier.has_chinese` already
takes one argument, so we don't need to do anything complicated. 

As a more general solution, there is also [langdetect][], but since this is
heuristic, you may find it gets it wrong some of the time. For example
(langdetect must be installed):

    % srt lines-matching -m langdetect -f 'lambda line: langdetect.detect(line) == "fr"'

Notice that we have to use double quotes instead of single quotes inside the
syntax block, since we're already quoting the expression itself with single
quotes.

Using the muxed Spanish and French output we generated earlier as input, this
outputs the following:

    % srt lines-matching -m langdetect -f 'lambda line: langdetect.detect(line) == "fr"' < ES-spanish-french-muxed.srt
    Skipped subtitle at index 1: No content
    Skipped subtitle at index 3: No content
    1
    00:01:34,579 --> 00:01:37,099
    <i>Le train pour Montauk</i>

    2
    00:01:37,182 --> 00:01:41,522
    <i>Idée diverses</i>
    <i>pour la Saint-Valentin, 2004.</i>

Notice that one line &mdash; `<i>sur la voie "B."</i>` &mdash; is completely
gone. Language detection is not an absolute science, and sometimes langdetect
gets it completely wrong, particularly on short sentences without much context
and with language-ambiguous words. For example, in this case, it's very unsure
what the language is because the content is quite short. Notice that its
certainties vary wildly between runs, sometimes even completely omitting French:

    >>> langdetect.detect_langs('<i>sur la voie "B."</i>')
    [ca:0.5714300788248391, it:0.2857133303787093, ro:0.14285632981661017]
    >>> langdetect.detect_langs('<i>sur la voie "B."</i>')
    [ca:0.7142825704732017, fr:0.28571320094169683]
    >>> langdetect.detect_langs('<i>sur la voie "B."</i>')
    [ca:0.571427410717758, fr:0.4285707742943302]
    >>> langdetect.detect_langs('<i>sur la voie "B."</i>')
    [ca:0.7142823512721495, fr:0.14285771416102766, ro:0.14285723363575129]

One thing you can do if you want to match per-subtitle rather than per-line
(which only makes sense if your different languages are actually in different
SRT blocks) is use `-s`/`--per-subtitle`, which may help to give better context
to langdetect. This fixes the problem above:

    >>> langdetect.detect_langs('<i>Le train pour Montauk</i>\n<i>sur la voie "B."</i>')
    [fr:0.8571379079913274, ca:0.14285786337770048]

[lines-matching]: https://github.com/cdown/srt/blob/develop/srt_tools/srt-lines-matching
[hanzidentifier]: https://github.com/tsroten/hanzidentifier
