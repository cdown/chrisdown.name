---
layout: post
title: Removing the source IP in Postfix
---

I don't really care who knows about my source IP when I send mails, but it
seems that a certain domain I'm sending to immediately spams e-mails that have
my Maltese apartment IP in the "Received" headers (even though it's not on any
blacklist as far as I can tell...). The receipt path before your MTA is not
really anyone's business, so if this becomes a problem, it's possible to remove
it pretty simply.

Add the following to main.cf:

    smtp_header_checks = regexp:/etc/postfix/smtp_header_checks

Then, strip "Received" headers by ignoring them, and reload the configuration:

    cat > /etc/postfix/smtp_header_checks << 'EOF'
    /^Received:/ IGNORE
    EOF

    service postfix reload
