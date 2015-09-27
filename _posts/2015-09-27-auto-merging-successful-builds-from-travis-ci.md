---
layout: post
title: Auto-merging successful builds from Travis CI
---

When I write new code for open source projects, my general workflow is this:

1. Branch a new branch, `f/thingy` (where "f" means "feature"), from `develop`
2. Add some commits with some new code to `f/thingy`, push them to GitHub,
   where the changes are picked up by [Travis CI][]
3. Sit around and wait for the Travis build to complete
4. Assuming the build was successful, merge `f/thingy` into `develop` and push
   it

Steps 3 and 4 are annoying, especially because Travis varies a lot in the time
that it will take to spin up a worker to run the tests, even with the new
container infrastructure. It wastes time that one could just be working on
other things, not worrying about having to wait to merge. Wouldn't it be
awesome if Travis just merged in automatically on build success?

[Travis CI]: https://travis-ci.org

## The GitHub side

GitHub has support for personal access tokens. We can generate one to allow
Travis to push to our repository.

First go to GitHub's [personal access tokens page][]. Here, you can generate a
new personal access token to allow Travis to push.

![Personal access tokens page](/images/blog/travis-automerge/generate-button.png)

You can set access controls for this token in the next page. In our case, we
only need to allow public repository access.

![Token access controls](/images/blog/travis-automerge/token-settings.png)

Once you've clicked "generate token", you'll be taken to a page where you can
copy the token for use. Put it somewhere locally, you'll need it later.

![The generated token](/images/blog/travis-automerge/generated-token.png)

[personal access tokens page]: https://github.com/settings/tokens

## The Travis side

First, you need to set up the [travis gem][]. You can install it with `gem
install travis`.

You can now encrypt the GitHub access token you generated earlier to the public
key for the repository:

    travis encrypt -r user/repo 'GITHUB_SECRET_TOKEN=<your token>'

This will give you a long key to add to your `.travis.yml`. You can add it
there now.

You also need to have a script to do the actual deployment. You can use the
script I wrote [here][] for that by adding the following lines to your
`.travis.yml`, taking care to modify accordingly:

{% highlight yaml %}
after_success:
  - "curl -o /tmp/travis-automerge https://raw.githubusercontent.com/cdown/travis-automerge/master/travis-automerge"
  - "chmod a+x /tmp/travis-automerge"
  - "BRANCHES_TO_MERGE_REGEX='^f/' BRANCH_TO_MERGE_INTO=develop GITHUB_REPO=cdown/srt /tmp/travis-automerge"
{% endhighlight %}

- `BRANCH_TO_MERGE_REGEX` is a regex that the current branch should match if a
  merge will take place. In my case, I limit it to feature branches (marked
  with `f/`), as there might be other branches I want to stick around without
  merging.
- `BRANCH_TO_MERGE_INTO` is the branch to merge into as part of deployment. I
  use two branches; `master`, which contains the latest stable code, and
  `deploy`, which contains the development code. In my case, I merge into
  `deploy` on successful build.
- `GITHUB_REPO` is the repo path that is being pushed to. For example,
  `cdown/srt` in this case.
- The script also needs `GITHUB_SECRET_TOKEN`, but that will be provided by the
  secret we generated above.

All things going well, now you should have auto-merge on successful builds! You
can see an example of this working in the [srt repo][] if you get stuck.

[travis gem]: https://rubygems.org/gems/travis
[here]: https://github.com/cdown/travis-automerge/blob/master/travis-automerge
[srt repo]: https://github.com/cdown/srt/blob/develop/.travis.yml
