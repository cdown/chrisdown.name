---
layout: default
title: Articles
description: Recent articles by Chris Down on Linux and other technologies.
---

# Articles

You can [subscribe via RSS](/feed.xml) to follow new articles.

{% assign posts = site.posts %}

<table class="light tworight">
<tbody>
{% for post in posts %}
{% unless post.hidden %}
<tr>
<td><a href="{{ post.url }}">{{ post.title }}</a></td>
<td class="nowrap">{{ post.date | date: "%Y-%m-%d" }}</td>
</tr>
{% endunless %}
{% endfor %}
</tbody>
</table>
