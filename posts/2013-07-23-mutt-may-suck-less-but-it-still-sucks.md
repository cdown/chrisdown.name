---
layout: post
title: Mutt may suck less, but it still sucks
description: A discussion of the less savoury parts of the mutt mail client.
---

I've used [mutt][mutt] to manage my mail for a good few years now, and in
general I have been very satisfied with it. It allows me to easily use vim to
edit mails, gives me extreme extensibility and freedom to set it up however I
like with send-hooks and the like, and it displays mail in an extremely good
way.  But Mutt, whilst being the best mail client by far in my eyes, has a lot
of problems that suck particularly hard:

- All IO is blocking. Using an IMAP server? Enjoy your random freezes.
- Searching is slow, even with caches. The fact that you have to use a separate
  search engine ([notmuch][notmuch], for example) just to have tolerable search
  times on large mailboxes is an absolute joke.
- Opening large mailboxes is slow, even with caches.
- Ctrl-g. Stop it.
- Coloring mails would be way easier if searches were additive.

Maybe I will try [sup][sup] one of these days and see if it is any better in
these aspects without compromising on customisability.

[mutt]: http://www.mutt.org/
[notmuch]: http://notmuchmail.org/
[sup]: http://supmua.org/
