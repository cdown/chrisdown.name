---
layout: post
title: Best practises when designating exit codes in command line programs
---

There is one thing which I frequently see in command line applications,
especially those written in languages which have the concept of uncaught
exceptions causing the program to terminate (although not exclusively) --
people code in a way that makes their exit codes suck.

In Python, for example, the following sort of thing is a common sight in
command line programs:

    if args["--yes"] and args["--no"]:
        raise ArgumentError("Nonsense options: can't have both --yes and --no")

It doesn't make sense to raise an exception in this manner. Exceptions are only
really useful when you're expecting that in, at least in some fringe situation,
you're planning on catching them. If you're just planning to raise them to the
user, use sys.exit() with a sensible exit code (and if it's useful for them to
have the traceback, give it to them separately).

This has a lot of benefits:

- You can specify a meaningful exit code instead of just returning 1;
- I can use your program in a larger script and actually detect what happened
  in more detail than "it worked" or "it failed";
- In most cases for errors like this ("can't use two conflicting options",
  "option requires an argument", etc), the traceback is not useful, and you
  should just get to the point.

Many BSDs have attempted to actually standardise some set of exit failure
conditions and their appropriate exit codes. To this effect, on many Unices
sysexits.h actually defines some more "standard" exit codes, which you should
probably prefer. In Python, you can [access these via the os module][osexit]:

    $ python << 'EOF'
    > import os
    > import sys
    >
    > sys.exit(os.EX_CONFIG)
    > EOF
    $ echo "$?"
    78

This method won't work on systems that don't support sysexits.h, though (like
Windows, for example), and (as usual) not all Unices agree on what the standard
should look like, so this can be tricky. My advice would be to look at the
generally accepted constants (for example, what is suggested by
[FreeBSD][fbsdsysexits]), and then do something like the following when using
them:

    _EX_CONFIG = getattr(os, "EX_CONFIG", 78)

This can be a bit of a nightmare, though. The most important thing is that you
make sure the exit codes your program returns are well documented, even if you
don't use the constants from sysexits.h.

In summary:

- Don't raise exceptions to the user, use sys.exit;
- Use meaningful exit codes to signal different failures;
- Document your exit codes well;
- (Optionally) use the constants defined in sysexit.h, with a fallback.

[osexit]: http://docs.python.org/3/library/os#os.EX_OK
[fbsdsysexits]: http://www.freebsd.org/cgi/man.cgi?query=sysexits
