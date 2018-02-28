InstantClick.on('change', function() {
  var el = document.getElementById('footer-email')
  var address = ['chris', 'chrisdown.name'].join('@');
  el.href = 'mailto:' + address;
  el.innerHTML = address;
});
