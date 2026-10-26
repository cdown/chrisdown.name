(function () {
    document.querySelectorAll('.video-load').forEach(function (control) {
        control.addEventListener('click', function (event) {
            if (event.button > 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
                return;
            }
            event.preventDefault();
            var iframe = document.createElement('iframe');
            iframe.src = control.dataset.videoSrc;
            iframe.title = control.dataset.videoTitle;
            iframe.allow = 'autoplay; fullscreen; picture-in-picture';
            iframe.allowFullscreen = true;
            iframe.referrerPolicy = 'strict-origin-when-cross-origin';
            control.replaceWith(iframe);
            iframe.focus();
        });
        control.addEventListener('keydown', function (event) {
            if (event.key === ' ') {
                event.preventDefault();
                control.click();
            }
        });
        control.setAttribute('role', 'button');
    });
}());
