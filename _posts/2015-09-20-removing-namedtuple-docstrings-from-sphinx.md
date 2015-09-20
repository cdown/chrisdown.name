---
layout: post
title: Removing namedtuple docstrings for Sphinx
---

[namedtuples][] are awesome. Unfortunately, if you find yourself with a large
one, and you use [Sphinx][] for documentation, you're going to find yourself
with a gigantic part of your documentation looking like this:

![Without skip](/images/blog/namedtuple-docstrings/before.png)

See those "Alias for field number" comments? In most cases, this information is
pretty much useless since the information is already in the class signature
anyway, and it just clutters the documentation (in this case it's not actually
in the class signature, but this namedtuple doesn't make sense to be used in a
tuple-like fashion, so it's useless anyway).

I went out to find some option for [autoclass][] that would allow me to disable
the docstrings for particular members, but I didn't find anything.

I eventually found [autodoc-process-docstring][], a Sphinx event that you can
attach a handler to. Essentially, it hands you the list of lines that comprise
the docstring, and you modify the list in place. Sphinx will then use whatever
the list looks like after the function has ran as the docstring.

In our case, we want to remove all attributes that just document that they are
an alias for a field number. Doing so is as simple as adding this function to
`conf.py`:

{% highlight python %}
def no_namedtuple_attrib_docstring(app, what, name,
                                   obj, options, lines):
    if any('Alias for field number' in line for line in lines):
        # This is a namedtuple with a useless docstring,
        # in-place purge all of the lines.
        del lines[:]
{% endhighlight %}

Now, we need to tell Sphinx to run this function as part of its docstring
processing. To do so, we attach this function as a callback to the event
`autodoc-process-docstring`:

{% highlight python %}
def setup(app):
    app.connect(
        'autodoc-process-docstring',
        no_namedtuple_attrib_docstring,
    )
{% endhighlight %}

Now, the documentation looks like this:

![With skip](/images/blog/namedtuple-docstrings/after.png)

[Sphinx]: http://sphinx-doc.org
[after directory]: http://vimdoc.sourceforge.net/htmldoc/options.html#%27runtimepath%27
[autoclass]: http://sphinx-doc.org/ext/autodoc.html#directive-autoclass
[autodoc-process-docstring]: http://sphinx-doc.org/ext/autodoc.html#event-autodoc-process-docstring
[namedtuples]: https://docs.python.org/2/library/collections.html#namedtuple-factory-function-for-tuples-with-named-fields
