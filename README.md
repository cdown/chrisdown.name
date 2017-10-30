This is the source code for the website that is displayed at
[chrisdown.name][]. The source is processed using [Jekyll][].

[chrisdown.name]: https://chrisdown.name
[Jekyll]: http://jekyllrb.com

## Installing dependencies

There are both Python and Ruby dependencies. Using [bundler][]'s `bundle
install` should give you everything you need on the Ruby side, whereas `pip
install -r requirements.txt` should give you all of the Python dependencies.

[bundler]: http://bundler.io/

## Deployment

Deployment to S3 and CloudFront invalidation can be done by running `rake
deploy`.

## Stripped fonts

I use a small subset of [Font Awesome][] to provide link icons in the header.
These are stripped using [Fontello][] to only the icons used to minimise
transmission and load time.

I also use two other fonts from [Google Fonts][]: [Open Sans][] and [Droid Sans
Mono][]. These are currently loaded from Google's CDN by the client, and are
not stored in the repository. I eventually plan to strip these to a subset of
their total characters, too.

[Font Awesome]: http://fortawesome.github.io/Font-Awesome/
[Fontello]: http://fontello.com
[Google Fonts]: https://www.google.com/fonts
[Open Sans]: http://www.google.com/fonts/specimen/Open+Sans
[Droid Sans Mono]: http://www.google.com/fonts/specimen/Droid+Sans+Mono

## Testing

[![Build status][travis-image]][travis-builds]

Right now, testing just includes looking for broken links (external or
internal) on the site. In future I'd like to also perform some usability tests,
especially for screen readers.

[travis-builds]: https://travis-ci.org/cdown/chrisdown.name
[travis-image]: https://travis-ci.org/cdown/chrisdown.name.png?branch=master

## License

Since this repository contains part code and part content, the contents is
split between two licenses, as appropriate for each medium. The code portion is
[ISC licensed][isc], but the content is licensed under a [Creative Commons
Attribution 4.0][cc] license. There are other included files in this project
that are copyrighted by entities other than myself that use other licenses,
too. See the LICENSE file for full details.

[isc]: http://en.wikipedia.org/wiki/ISC_license
[cc]: http://creativecommons.org/licenses/by/4.0/
