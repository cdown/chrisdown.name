!function(c,d,o,w,n){c.GoogleAnalyticsObject=o;c[o]||(c[o]=function(){
(c[o].q=c[o].q||[]).push(arguments)});c[o].l=+new Date;w=d.createElement('script');
n=d.scripts[0];w.src='//www.google-analytics.com/analytics.js';
n.parentNode.insertBefore(w,n)}(window,document,'ga');

InstantClick.on('change', function() {
    ga('create', 'UA-58706842-1', 'auto');
    ga('require', 'displayfeatures');
    ga('send', 'pageview', location.pathname + location.search);
});
