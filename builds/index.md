---
layout: default
title: Build status dashboard

builds:
  - name: cargo-which-nightly
  - name: dotfiles
  - name: exifrename
  - name: filestruct
  - name: funcfmt
    extra:
      - miri
  - name: geoip-http
  - name: icopng
  - name: mack
  - name: srt
  - name: tzupdate
  - name: zcfan
---

# Build status dashboard

<table>
  <thead>
    <tr>
      <th>Repository</th>
      <th>CI</th>
    </tr>
  </thead>
  <tbody>
    {% for repo in page.builds %}
    <tr>
      <th><a href="https://github.com/cdown/{{ repo.name }}">{{ repo.name }}</a></th>
      <td class="status-image">
        <a href="https://github.com/cdown/{{ repo.name }}/actions?query=branch%3Amaster">
          <img class="nonstandard" src="https://img.shields.io/github/actions/workflow/status/cdown/{{ repo.name }}/ci.yml?branch=master&label=ci" alt="CI status for {{ repo.name }}" />
        </a>
        {% for extra in repo.extra %}
        <a href="https://github.com/cdown/{{ repo.name }}/actions?query=branch%3Amaster">
          <img class="nonstandard" src="https://img.shields.io/github/actions/workflow/status/cdown/{{ repo.name }}/{{ extra }}.yml?branch=master&label={{ extra }}" alt="{{ extra }} status for {{ repo.name }}" />
        </a>
        {% endfor %}
      </td>
    </tr>
    {% endfor %}
  </tbody>
</table>
