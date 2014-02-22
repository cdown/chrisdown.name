---
layout: post
title: Securely automating rsync to archive sensitive files
---

Before I begin, please note that [sync is not backup][syncisnotbackup]. If you
plan to use this sort of method for backups, you should look into using
something like [duplicity][duplicity] or [rsnapshot][rsnapshot] instead.  In
the latter case, you can implement the rsync side of what I'm suggesting here
using `--rsync-path='sudo rsync'` as part of rsync\_long\_args in your
rsnapshot config, but I don't know if such a thing is possible with duplicity.

Obviously, any "secure" implementation using rsync would require that rsync
itself was secure. Whilst it has a lot of talented eyes on it, there have been
fairly bad exploits in the past (including [CVE-2011-1097][CVE-2011-1097] and
[CVE-2007-6200][CVE-2007-6200], among others). In any case, the less stuff that
*you* do, the more secure your system is likely to be (especially since there
is probably far less scrutiny of your work than there is of rsync).

I have some large datasets on some of my servers that I often need to process
locally (ie. on my laptop). It's much better for me to have these datasets
already locally available, because it's not efficient for me to process the
data on the server, and the data sets are too large to access them live the
network without incurring significant speed penalties.

My solution to this is to automatically sync them every day to my local
machine, which is easy enough just using rsync and a cron job, but there is a
problem. Some of the files I need are system files that are owned by root, so
I need to elevate to root to get them. This poses a few problems:

- I do not allow root login over SSH on my servers;
- I need to be able to allow the ssh client to automatically login to the
  server;
- I need to allow rsync to read files as root;
- I need to do this exposing the minimum possible privileges to reduce the
  worst case security implications.

My solution to these problems is as follows:

- Create a user called "rsync" on the remote server;
- Allow them to use rsync as root, but *only* when using "--server --sender";
- Make rsync use 'sudo rsync' as its command on the remote;
- Make rsync use an SSH key exclusively for this archival

This method limits the possibility that an attacker can effectively use any
privilege she would gain from getting the SSH key (which should be securely
stored, anyway).

It's common to see two major mistakes when people implement setups like this
(other than just logging in directly as root on the remote):

- Many people set up rsync archiving with passwordless SSH keys, which would
  allow anyone with the key to log in and get the files. For me, these files
  are still sensitive, so that is an unacceptable liability;
- It's common to see people allowing the rsync user to do any rsync command
  with NOPASSWD in /etc/sudoers. This is still pretty dangerous, this allows
  someone who gains access to that account to modify arbitrary files on your
  system, which is pretty much as good as just giving them root access.

The proper way to handle these issues is to use ssh-agent, and further limit
the commands accepted by sudo to allow unprompted elevation.

## Setup

### rsync user

On the remote, create the new "rsync" user that we will use exclusively to
elevate to root when we do the sync:

    useradd -m -d /srv/rsync -r -s /bin/bash -p NP rsync

We need to use "-p NP" so that the account does not become locked, because
without it, sshd will not allow us to log in. This does not mean that the
password actually *is* "NP", but that that is what the [crypt(3)][crypt] output
is compared to. Since crypt can never return "NP", this denies direct logins
using a password to the account, whilst still allowing us to log into that
account using our SSH key.

### Generate key

On your local machine, generate a new key that will be used exclusively for
syncing (do this as the same user as you are going to be syncing as):

    mkdir -pm700 ~/.ssh/keys
    ssh-keygen -f ~/.ssh/keys/rsync_archive -C rsync-archive

Use a good passphrase that you can remember, you'll need it when adding the key
to the SSH agent. You might as well start up an agent and add it now, since
you're going to need it for the next steps:

    mkdir -m700 ~/.ssh/agents
    eval "$(ssh-agent | tee ~/.ssh/agents/rsync_archive)"

### Work out what command is going to be run on the server

We need to work out what command is going to be run on the server, so that we
can lock sudo access down to that single command. We could also do something
like "rsync --server --sender \*" in /etc/sudoers, but unless you have a reason
to do that, you might as well further limit the opportunities for exploitation
if someone got access to the rsync user.

Run your normal command, but this time, add `--rsync-path="printf '%s\n' >&2"`.
You'll see something like this printed out:

    --server
    --sender
    -lHogDtpAXrze.iLsf
    --numeric-ids
    .
    /var/lib/couchdb
    rsync: connection unexpectedly closed (0 bytes received so far) [Receiver]
    rsync error: error in rsync protocol data stream (code 12) at io.c(601) [Receiver=3.0.7]

Don't worry about the rsync errors -- they're expected, you did just give it a
fake rsync path, after all. What you really want is given on the previous
lines; this is the command that rsync is running on the remote after it
connects to the server, and this is the command that you need to allow
elevation for.

### Allow the user to become root when acting as an rsync sender

Append the following line in /etc/sudoers (preferably using visudo so that a
syntax check is performed before it is saved):

    rsync ALL=(ALL) NOPASSWD: rsync --server --sender -lHogDtpAXrze.iLsf --numeric-ids . /var/lib/couchdb

You can test this by running the same command prepended with "sudo -K"
as the rsync user. If nothing appears to happen, it's working (if it wasn't,
you would receive the password prompt from sudo).

A caveat of this method is that if rsync ever changes the command used by the
command you are running locally, this will start to fail. In practise, I have
not had this happen whilst I have been running this setup, but even if it did
happen, it's easy to fix (just redo these steps).

### Limit the rsync user to running this single command

If you are only ever going to allow the rsync user to run this one command (ie.
you only do one type of archive on the server as this user), you can force the
SSH daemon on the remote to use this command when the user logs in, instead of
the command requested by the user. This further limits the vectors for attack.

To do this, first add the public key from the keypair you generated to the
remote rsync user's ~/.ssh/authorized_keys. Then, prepend the same command you
just added to sudoers, except with "sudo" prepended, so it looks something like
this:

    command="sudo rsync --server --sender -lHogDtpAXrze.iLsf --numeric-ids . /var/lib/couchdb" [public key]

You should also consider using the no-port-forwarding, no-X11-forwarding, and
no-pty options, to further limit the opportunities for exploitation. In that
case, it would look something like this:

    no-port-forwarding,no-X11-forwarding,no-pty,command=...

If you now ssh to the rsync user on the remote machine, you should get nothing
returned. You can make it more clear that it's not still connecting by using
the various levels of ssh's -v flags (-vv should be clear enough).

### Create a cron job

We now need to create a cron job that connects to the ssh agent, and uses it to
connect to the server you are syncing. I suggest you do this as two parts
(although it can be done in one, it will look pretty messy). Assuming that you
created the agent as root earlier to preserve ownership information (you could
also run the agent as your own user and source that, instead, as long as you
are running the job as root), the following should work to sync every hour:

    cat > /usr/local/bin/sync-foo << 'EOF'
    #!/bin/sh

    . ~/.ssh/agents/rsync_archive
    rsync -avzHAX --numeric-ids --rsync-path='sudo rsync' rsync@foo:/var/lib/couchdb /sync/foo-couch
    EOF
    chmod a+x /usr/local/bin/sync-foo

    cat > /etc/cron.d/sync-foo << 'EOF'
    PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
    0 * * * * root sync-foo
    EOF

Obviously, this requires that your SSH agent has the key added and unlocked.
That's your responsibility (when you boot the server), otherwise rsync will
time out. You can immediately fail the connection on such conditions if you
disable password authentication in your sshd\_config on the remote.

You should now have a fully working setup. It goes without saying that you
should keep the passphrase to the key (and, of course, the key itself) secure.

[duplicity]: http://duplicity.nongnu.org/
[rsnapshot]: http://www.rsnapshot.org/
[syncisnotbackup]: http://lawyerist.com/file-sync-is-not-backup/
[CVE-2011-1097]: http://web.nvd.nist.gov/view/vuln/detail?vulnId=CVE-2011-1097
[CVE-2007-6200]: http://web.nvd.nist.gov/view/vuln/detail?vulnId=CVE-2007-6200
[crypt]: http://linux.die.net/man/3/crypt
