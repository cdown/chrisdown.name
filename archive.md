---
layout: default
title: Articles
description: Recent articles by Chris Down on Linux and other technologies.
---

# Articles

{% assign posts = site.posts %}

<table class="articles">
<tbody>
{% for post in posts %}
{% unless post.hidden %}
<tr>
<td><a href="{{ post.url }}">{{ post.title }}</a></td>
<td class="nowrap date">{{ post.date | date: "%Y-%m-%d" }}</td>
</tr>
{% endunless %}
{% endfor %}
</tbody>
</table>
