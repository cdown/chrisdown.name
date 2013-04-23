---
layout: none
---

document.addEventListener("DOMContentLoaded", function() {
    "use strict";
    var el, address;

    el = document.getElementById("email");
    address = [ "{{ site.personal.email.account }}", "{{ site.url | split: '/' | last }}" ].join("@");

    el.href = "mailto:" + address
    el.innerHTML = address
});
