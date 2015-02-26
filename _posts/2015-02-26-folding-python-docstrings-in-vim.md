---
layout: post
title: Folding Python docstrings in vim
---

I've been looking for some way to fold Python docstrings ever since I started
using inline documentation for [Sphinx][]. While inline documentation has a lot
of advantages, it does mean that a lot less of the code can fit on one screen
at a time.

I first started out with using `foldmethod=expr` and messing around with
`foldexpr` to determine if it was inside a docstring or not and fold
appropriately, but this very quickly became quite complicated.

Eventually I settled on adding a syntax folding rule after the Python syntax
file has been loaded by using an [after directory][]. This allows me to
autofold docstrings in a much saner way than writing a large `foldexpr`. Prior
to this I didn't realise how easy it was to write vim syntax extensions, it
turned out to be much less messy than I thought.

To do this, first make sure folding is enabled and your `foldmethod` is set to
`syntax` in your config. You can do this just for Python by doing something
like the following:

    autocmd FileType python setlocal foldenable foldmethod=syntax

Then, add the following line to `~/.vim/after/syntax/python.vim`:

    syn region String start=/\('''\|"""\)/ end=/\('''\|"""\)/ fold

You can also optionally set the fold to show the first line of the docstring
(assuming you always add a newline after your docstring starts):

    set foldtext=getline(v:foldstart+1)

You should now have gone from something like this:

![Vim screenshot without docstrings folded](/images/blog/fold-docstrings/before.png)

To something like this:

![Vim screenshot with docstrings folded](/images/blog/fold-docstrings/after.png)

[Sphinx]: http://sphinx-doc.org
[after directory]: http://vimdoc.sourceforge.net/htmldoc/options.html#'runtimepath'
