---
layout: post
title: Writing Python AST linters for Arcanist/Phabricator
---

We use [Phabricator][] for almost everything concievable code-wise at Facebook.
Recently, I wanted to add a linter to one of our core repositories, but I
didn't find particularly good end-to-end documentation for doing so. As such,
I'm intending this to be a fairly simple, but comprehensive guide to writing a
Phabricator linter that deals with the Python AST.

[Phabricator]: http://phabricator.org/

## Defining the problem

### What do we want to catch?

First of all, we have to define what we want to catch. For the purposes of this
tutorial, we're going to make a linter that catches "print" statements being
used in production code dirs.

### How do we want to catch it?

First, we have to work out how we want to find print statements. If you looked
at Facebook's linters a few years ago, you would have found a lot of regex
rules that were being used to find lint violations. Using regexes to find
syntax-based lint violations is a gruelling and impossible task, and something
that didn't foster a particularly positive view of linters inside the company.
When it comes to syntax, don't reinvent the wheel: use an AST parser that
really has a deep understanding of your library. It's (a little) more work, but
it pays off by multitudes over time.

## Creating the AST parser

The [Python ast module][] in the stdlib is quite simple and pleasant to work
with. If you've never used it before, I think you'll be pleasantly surprised.

First things first, we need to parse the AST. Phabricator linters are invoked
at the file level, so your parser needs to be cool working with that
expectation.



[Python ast module]: https://docs.python.org/2/library/ast.html

## Key Arcanist lint-related classes

[ArcanistLinter][] is the base class that other linter classes inherit from.
Other than that, the main one to look at is [ArcanistExternalLinter][], which
operates by running an external program, and parsing its output to get lint
results.

I'll be showing you how to work with both.

[ArcanistLinter]: https://secure.phabricator.com/book/arcanist/class/ArcanistLinter/
[ArcanistExternalLinter]: https://secure.phabricator.com/book/arcanist/class/ArcanistExternalLinter/

## Key methods to define

### ArcanistLinter

ArcanistLinter provides several key methods that can be used to configure the
linter. Some of these methods are declared abstract, so even if you don't use
them, you need to implement them in your child class.

In ArcanistLinter, the only abstract method is `getLinterName`, which returns
the name of the linter. In Arcanist linter parlance, the linter "name" is
prepended to the errno for a particular lint error, which allows you to
identify both the errno for this particular lint error (in case you have
multiple possible lint errors in one linter), and the linter raising the lint
error itself. For example, if your linter lints Python code, and you have the
lint error `MAGIC_NUMBER`, which you've defined to have errno 1, you'd likely
return the string `Python` from `getLinterName`, and get the unique error ID
`Python1`.

`getLintSeverityMap` allows you to provide an hash table of lint error numbers
to their respective severities, which we will cover in more detail in the [lint
severities section][].

`getLintNameMap` permits providing a map of lint error numbers to human
readable lint error descriptions. For example, if your lint error is the above
mentioned `Python1`, where "1" represents `MAGIC_NUMBER`, you might map
`MAGIC_NUMBER` to the string "Magic number should be a named constant".

`lintPath` is where linter execution starts -- this is where you put your code
to execute the linter and raise any appropriate lint errors. I'll go into that
in more detail [below][].

As mentioned, many of these methods are not declared abstract, and this is for
a good reason: many of these methods are either optional, or are only called by
convienience methods when raising the lint error, which you are not required to
use (but you probably should!).

[lint severities section]: #lint-severities
[below]: #raising-lint-errors

### ArcanistExternalLinter

ArcanistExternalLinter is a subclass of ArcanistLinter that is more geared
towards interfacing with external linters. To this effect, it includes a few
more methods that are focused on dealing with this.

One very key difference is that you're expected to use `parseLinterOutput`
instead of `lintPath`. You return the path to the linter binary from
`getDefaultBinary`, optionally return any required arguments from
`getMandatoryFlags`, and ArcanistExternalLinter will do the rest, calling the
binary automatically for you and passing the resulting data to
`parseLinterOutput`.

One downside of the implementation of `parseLinterOutput` is that it expects an
array of lint messages to be returned. This means you're not expected to use
any of the `raiseLintAtFoo` convienience methods. We'll talk about these
convienience methods [shortly][].

[shortly]: #lint-raising-convienience-methods

## Lint raising convienience methods

There are three main lint raising convienience methods:

- `raiseLintAtPath`, applying to the whole file rather than a specific line in
  it;
- `raiseLintAtOffset`, which raises a lint error at a specific character offset
  from the start of the file (this is easy to use with, for example,
  `PREG_OFFSET_CAPTURE` if you are not using the AST);
- `raiseLintAtLine`, which raises a lint error at a specific line and column,
  which is quite easy to use with the python `ast` module since nodes contain
  information about these attributes.

## Lint severities

There are five lint severities, three of which I will go over here (`autofix`
and `disabled` should be fairly self-explanatory).

- `ERROR`-level lint messages are always raised if you modified a file that
  triggers one, regardless of whether you modified the line that it is
  complaining about or not. This is quite useful to stop conditions that must
  not occur in your codebase;
- `WARNING`-level lint messages are only raised if they appear on a line that
  you have modified;
- `ADVICE`-level lint messages are just like warnings, but they don't even
  require confirmation to continue on `arc diff`.

# Writing the AST parser

## How the visitor works
 
# Unit tests

# arc liberate

# The different lint raise types

