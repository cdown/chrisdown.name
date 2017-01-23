document.addEventListener('DOMContentLoaded', function() {
  var images = document.getElementsByTagName('img');
  var image_list = Array.prototype.slice.call(images);
  image_list.forEach(function(img, _, _) {
    if (img.className.indexOf('nonstandard') >= 0) {
      return;
    }

    var a = document.createElement('a');
    a.href = img.src;
    img.parentNode.replaceChild(a, img);
    a.appendChild(img);
  });
});
