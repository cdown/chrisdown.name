---
layout: post
title: Archiving deleted mails in Dovecot without using a namespace
description: Discussion about using the dovecot_deleted_to_trash plugin for archival purposes.
---

When I first started using Dovecot, I looked high and low for a way to archive
mails, and came up with nothing useful except for [lazy\_expunge][le]. I find
archiving all deleted mails far more preferable to manual copying for two
reasons:

1. I want to store *all* mails for posterity unless I am very sure otherwise
2. When storing mails for posterity in mutt, delete-message is far faster
   than copy-message, making even macros a painfully slow operation

lazy\_expunge has always annoyed me somewhat, because I don't have any need for
the granularity of having an entirely separate namespace for archiving, I just
want one maildir folder to shove everything into.

Today I came upon [dovecot\_deleted\_to\_trash][dtt], which does exactly what I
wanted to do when I first started using Dovecot. The configuration I use for
archiving mails looks like this:

    protocol imap {
      mail_plugins = deleted_to_trash
    }

    plugin {
      deleted_to_trash_folder = Archive
    }

Big thanks go out to [Lex Brugman][lex], who authored the plugin, and has now
saved me from certain insanity at the hands of lazy\_expunge.

[le]:  http://wiki2.dovecot.org/Plugins/Lazyexpunge
[dtt]: https://github.com/lexbrugman/dovecot_deleted_to_trash
[lex]: https://github.com/lexbrugman
