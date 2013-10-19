This is the [Jekyll][jekyll] site that runs https://chrisdown.name.

## Icon font

I use icons from [Font Awesome][fontawesome] in the headers of pages. The
default font is huge, so I strip them down with
[Fontello][fontello] first. The CSS differs from the Font Awesome
CSS when doing that, so I copy the code that affects all "icon-" prefixed
selectors. There are also a ton of selectors for various effects based on the
icon- prefix as well, but I don't use those, so they're not copied. This
results in a pretty small and fast loading CSS file, that then loads the tiny
WOFF file containing the icon font.

[jekyll]: http://jekyllrb.com/
[fontawesome]: http://fortawesome.github.io/Font-Awesome/
[fontello]: http://fontello.com/
