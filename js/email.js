---
layout: none
---

document.addEventListener("DOMContentLoaded", function() {
    var el = document.getElementById("email");
    var address = [ "{{ site.personal.email.account }}", "{{ site.url | split: '/' | last }}" ].join("@");
    el.href = "mailto:" + address
    el.innerHTML = address
});
