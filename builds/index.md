---
layout: default
title: Build status dashboard

builds:
  - name: cargo-which-nightly
  - name: exifrename
  - name: filestruct
  - name: funcfmt
  - name: icopng
  - name: mack
  - name: srt
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
          <img class="nonstandard" src="https://img.shields.io/github/actions/workflow/status/cdown/{{ repo.name }}/ci.yml?branch=master" alt="CI status for {{ repo.name }}" />
        </a>
      </td>
    </tr>
    {% endfor %}
  </tbody>
</table>
