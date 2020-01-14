---
layout: default
title: Assorted notes
description: Recent blog posts by Chris Down.
---

# Assorted notes

{% assign posts = site.posts %}

<!-- TODO: make post.hidden and forloop.{first,last} play nice -->
{% for post in posts %}
{% unless post.hidden %}
{% assign currentdate = post.date | date: "%Y" %}
{% if currentdate != date %}
{% unless forloop.first %}</ul>{% endunless %}
<h2 id="y{{post.date | date: "%Y"}}">{{ currentdate }}</h2>
<ul>
{% assign date = currentdate %}
{% endif %}
<li><a href="{{ post.url }}">{{ post.title }}</a></li>
{% if forloop.last %}</ul>{% endif %}
{% endunless %}
{% endfor %}
