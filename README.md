This is the source code for the website that is displayed at
[chrisdown.name][]. The source is processed using [Jekyll][].

[chrisdown.name]: https://chrisdown.name
[Jekyll]: http://jekyllrb.com

## Dependency resolution

Using [bundler][]'s `bundle install` should give you everything you need.

[bundler]: http://bundler.io/

## Deployment

You can build the output files with `jekyll build`, and they will appear in
"deploy". There is a rake task for this that is also linked to a deploy task,
which you might want to adjust to match your own server and path details.

## License

Since this repository contains part code and part content, the contents is
split between two licenses, as appropriate for each medium. The code portion is
[ISC licensed][isc], but the content is licensed under a [Creative Commons
Attribution 4.0][cc] license. There are other included files in this project
that are copyrighted by entities other than myself that use other licenses,
too. See the LICENSE file for full details.

[isc]: http://en.wikipedia.org/wiki/ISC_license
[cc]: http://creativecommons.org/licenses/by/4.0/
