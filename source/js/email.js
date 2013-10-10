---
---

document.addEventListener("DOMContentLoaded", function() {
    "use strict";
    var els, address;

    els = document.getElementsByClassName("email");
    address = [ "{{ site.personal.email.account }}", "{{ site.url | split: '/' | last }}" ].join("@");

    Array.prototype.forEach.call(els, function(el) {
        el.href = "mailto:" + address;
        var classes = el.className.split(/\s+/);
        if (classes.indexOf("no-replace-text") === -1) {
            el.innerHTML = address;
        }
    });
});
