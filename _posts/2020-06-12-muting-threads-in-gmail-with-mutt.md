---
layout: post
title: "mutt support for Gmail's \"mute\" feature"
description: "Gmail has a neat feature called \"Mute\", which prevents any further replies to a muted thread from entering the inbox. I've now created a tool, gmute, to help with this."
---

tl;dr:

1. `pip install gmute` ([repo](https://github.com/cdown/gmute))
2. Configure `~/.config/gmute` as per [the
   documentation](https://github.com/cdown/gmute/blob/master/README.rst)
3. Add `macro index M '<enter-command>set pipe_sep="\n_PIPE_SEP_\n"<enter><pipe-message>gmute<enter><sync-mailbox>'` to your mutt
   configuration.
4. Press M on a message in a thread you want to mute, and enjoy!

---

Gmail has a neat feature called "mute", which prevents any further replies to a
muted thread from entering the inbox. This is very useful if you're on a lot of
mailing lists, where there may be some lengthy and rapid discussion that you're
not interested in reading or contributing to. Despite having some filters
already in place for files, authors, ccs, and signed-off-bys that I care about,
Linux kernel lists are still pretty noisy, even if scoped down.

Gmail treats "muted" as if it was a label. Usually this means that you'll be
able to access it through IMAP as if it was a folder, and move things into that
folder. However, if you query for this folder, you'll find unlike other labels,
it doesn't exist:

    % curl -s imaps://imap.gmail.com --user user:pass | grep -ci mute
    0

There are some previous posts asking about how to achieve this in mutt, but as
far as I can see, all have gone
[unanswered](https://groups.google.com/g/comp.mail.mutt/c/xmDG9w2rJsU), so I
set to Google's documentation to work out how to handle this. There are also
some unofficial patches which artificially replicate the mute functionality,
but I'd rather use it directly (and I'm not really interested in maintaining my
own quilt of patches on top of mutt HEAD).

Looking for information on label modification via IMAP brings us to [this
article](https://developers.google.com/gmail/imap/imap-extensions#access_to_gmail_labels_x-gm-labels),
which goes over the existence of an `X-GM-LABELS` IMAP attribute for these
kinds of labels.

Grabbing a Message-ID from the mail headers and trying to apply it seems to
work great:

    % curl -s imaps://imap.gmail.com/Inbox --user user:pass --request 'UID SEARCH HEADER Message-ID <some@mid>'
    * SEARCH 72597
    % curl -v -s imaps://imap.gmail.com/Inbox --user user:pass --request 'STORE 72597 +X-GM-LABELS (Muted)'
    [...]
    < A003 OK [READ-WRITE] Inbox selected. (Success)
    > A004 STORE 72597 +X-GM-LABELS (\Muted)
    < A004 OK Success

...however, the "Muted" label doesn't seem to actually get applied in the Gmail
UI. Hmm. It seems muting only part of the thread confuses Gmail somewhat. Even
more confusingly, Gmail does threading in its own way, not necessarily only
based on In-Reply-To headers. You can query one "thread" from Gmails
perspective by looking at the `X-GM-THRID` attribute, in much the same way as
we used `X-GM-LABELS` before.

Clearly this is a lot more complex than it seemed at first :-) For that reason
I made [gmute](https://github.com/cdown/gmute) which is mail client agnostic --
you just provide it a mail (e.g. from mutt's `pipe-message` command), and it
does the rest.

I know that I'm not the only one who wanted the mute feature in mutt, so
hopefully this helps some other people out, too. Let me know what you think --
feedback and comments welcome. :-)
