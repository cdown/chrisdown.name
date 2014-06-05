---
layout: post
title: Using multiple isolated SSH keys with agent forwarding
---

I want to make better use of agent forwarding on some company servers, which
means that I need to separate my keys for personal use, and each of the groups
I work with where I want to do agent forwarding. From the ssh\_config manual
page:

> Agent forwarding should be enabled with caution. Users with the ability to
> bypass file permissions on the remote host (for the agent’s Unix-domain
> socket) can access the local agent through the forwarded connection. An
> attacker cannot obtain key material from the agent, however they can perform
> operations on the keys that enable them to authenticate using the identities
> loaded into the agent.

It seems that ForwardAgent allows key operations on any key present in the
agent, not just the one that was used to connect, which I guess makes sense in
some situations. For this reason, we need to run multiple SSH agents as well as
using multiple keys.

I currently launch my SSH agents through my shell profile, since that's how I
log in to all of my machines. You can see the configuration before the changes
[here][before-changes].

Now all that's required are two things:

- Automated starting of the various SSH agents, and adding their respective
  keys
- Some way to force the SSH client to use a connection to a specific agent
  before connecting (unfortunately, this seems not to be easily possible inside
  the ssh configuration)

Automated initialisation can be done by putting all of the keys inside one
directory (I use ~/.ssh/private), looping over the files, and launching an
instance for each. You can see the changes made to do that
[here][loop-over-keys].

While that's fairly trivial, you still need a way to know the agent's
connection details. We can do this by putting them in files in another
directory (I use ~/.ssh/agents), and then having some way of switching between
them. There are two main ways of doing this that I can think of: write an
ssh-context function that you can run beforehand that sets the appropriate
environment variables based on the relevant file in ~/.ssh/agents, or wrap
around ssh itself. I prefer the former, since it's more explicit, and it's more
difficult to accidentally use the wrong agent. You can see what I wrote to do
that [in this commit][context-commit], all that's required is to source
~/.ssh/agents/name.

Obviously, you still need to be mindful of who has root access to the servers
you're forwarding to, but now the agent's ability to access other services is
limited to what they would already have been able to access anyway.

[before-changes]: https://github.com/cdown/dotfiles/blob/b2520a7eb20b2a3465b290c42e165b36839633ba/.config/shell/profile/ssh_agent
[loop-over-keys]: https://github.com/cdown/dotfiles/commit/07358716eed2f0508a30ca36d7ff4d32ba17aa51
[context-commit]: https://github.com/cdown/dotfiles/commit/373dacad229d9efc72853a55548e7f97391e6ece
