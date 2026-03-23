/* animation.js — reusable stepped animation framework for blog posts.
 * Requires anime.js. Dispatches to renderers by config.type.
 *
 * Usage in posts:
 *   {% animation %}
 *   { "type": "storage-tiers", "panels": {...}, "steps": [...] }
 *   {% endanimation %}
 */
(function () {
  /* ------------------------------------------------------------------ */
  /* CSS — injected once                                                  */
  /* ------------------------------------------------------------------ */
  var CSS = `
.animation-container { margin: 2em 0; padding: 1.5em; background: #f8f9fa; border: 1px solid #e0e0e0; border-radius: 6px; }
.anim-panels { display: flex; gap: 2.5em; }
@media (max-width: 580px) { .anim-panels { flex-direction: column; gap: 1.5em; } }
.anim-panel { flex: 1; min-width: 0; }
.anim-ptitle { font-size: .88em; font-weight: 600; text-align: center; margin: 0 0 .9em; padding-bottom: .5em; border-bottom: 1px solid #ddd; }
.anim-tier { margin-bottom: .8em; }
.anim-tlabel { font-size: .75em; color: #777; text-transform: uppercase; letter-spacing: .04em; margin-bottom: .35em; }
.anim-slots { display: flex; gap: 5px; align-items: center; flex-wrap: wrap; min-height: 42px; }
.anim-slot { width: 40px; height: 40px; border-radius: 5px; display: flex; align-items: center; justify-content: center; font-size: .85em; font-weight: 700; color: #fff; text-shadow: 0 1px 2px rgba(0,0,0,.25); flex-shrink: 0; }
.anim-empty { width: 40px; height: 40px; border-radius: 5px; border: 2px dashed #d0d0d0; box-sizing: border-box; flex-shrink: 0; }
.anim-needed { box-shadow: 0 0 0 3px #e74c3c, 0 0 10px rgba(231,76,60,.35); }
.anim-outcome { font-size: .8em; min-height: 1.2em; text-align: center; margin-top: .25em; font-weight: 500; }
.anim-legend { display: flex; gap: 1.2em; flex-wrap: wrap; margin-top: 1em; font-size: .78em; color: #666; }
.anim-litem { display: flex; align-items: center; gap: .35em; }
.anim-lswatch { width: 12px; height: 12px; border-radius: 3px; flex-shrink: 0; }
.anim-status { margin-top: 1em; padding: .7em .9em; background: #fff; border: 1px solid #e4e4e4; border-radius: 4px; font-size: .86em; line-height: 1.55; min-height: 3.5em; }
.anim-controls { margin-top: .65em; display: flex; align-items: center; gap: .5em; }
.anim-stepinfo { flex: 1; font-size: .78em; color: #999; }
.anim-btn { padding: .3em .85em; font-size: .83em; cursor: pointer; border: 1px solid #bbb; border-radius: 4px; background: #fff; }
.anim-btn:hover:not(:disabled) { background: #f0f0f0; }
.anim-btn:disabled { opacity: .38; cursor: default; }
`;

  if (!document.getElementById('animation-styles')) {
    var styleEl = document.createElement('style');
    styleEl.id = 'animation-styles';
    styleEl.textContent = CSS;
    document.head.appendChild(styleEl);
  }

  /* ------------------------------------------------------------------ */
  /* storage-tiers renderer                                               */
  /* ------------------------------------------------------------------ */
  var COLD_COLORS = ['#4a85c2', '#5b9bd5', '#73aed9', '#8bbde0'];
  var WARM_COLORS = ['#d4743c', '#c05a28', '#b04820', '#9c3818'];

  function pageColor(n, fastCap) {
    if (n > fastCap) return WARM_COLORS[Math.min(n - fastCap - 1, WARM_COLORS.length - 1)];
    return COLD_COLORS[Math.min(n - 1, COLD_COLORS.length - 1)];
  }

  function makeSlot(n, need, fastCap, fresh) {
    var el = document.createElement('div');
    el.className = 'anim-slot' + (need.indexOf(n) >= 0 ? ' anim-needed' : '');
    el.style.background = pageColor(n, fastCap);
    if (fresh) el.style.opacity = '0';
    el.textContent = n;
    return el;
  }

  function makeEmpty() {
    var el = document.createElement('div');
    el.className = 'anim-empty';
    return el;
  }

  function animateIn(els) {
    if (!window.anime || !els.length) return;
    anime({
      targets: els,
      opacity: 1,
      delay: anime.stagger(40),
      duration: 200,
      easing: 'easeOutQuad'
    });
  }

  /* Update a tier's slots in-place, reusing DOM elements for pages that were
   * already present. Returns only the newly added slot elements. */
  function updateSlots(el, pages, cap, need, fastCap) {
    var existing = {};
    Array.from(el.children).forEach(function (child) {
      if (child.classList.contains('anim-slot')) {
        existing[parseInt(child.textContent)] = child;
      }
    });

    var newSlots = [];
    var fresh    = [];

    for (var i = 0; i < cap; i++) {
      var n = pages[i];
      if (n !== undefined && existing[n]) {
        var reused = existing[n];
        reused.classList.toggle('anim-needed', need.indexOf(n) >= 0);
        newSlots.push(reused);
      } else if (n !== undefined) {
        var newEl = makeSlot(n, need, fastCap, true);
        newSlots.push(newEl);
        fresh.push(newEl);
      } else {
        newSlots.push(makeEmpty());
      }
    }

    while (el.firstChild) el.removeChild(el.firstChild);
    newSlots.forEach(function (s) { el.appendChild(s); });

    return fresh;
  }

  function renderStorageTiers(container, config) {
    var steps    = config.steps;
    var panels   = config.panels;
    var ids      = Object.keys(panels);
    var fastCap  = config.fastCap || 4;
    var outcomes = config.outcomes || {};
    var cur      = 0;

    var legend = config.legend || [
      { color: COLD_COLORS[0], label: 'Cold page (swapped out first, unlikely to be needed)' },
      { color: WARM_COLORS[0], label: 'Warm page (recently swapped, likely still needed)' }
    ];

    container.innerHTML =
      '<div class="anim-panels">' +
      ids.map(function (id) {
        return '<div class="anim-panel">' +
          '<div class="anim-ptitle">' + panels[id] + '</div>' +
          '<div class="anim-tier"><div class="anim-tlabel">Fast \u2014 compressed RAM</div>' +
          '<div class="anim-slots" data-p="' + id + '" data-t="fast"></div></div>' +
          '<div class="anim-tier"><div class="anim-tlabel">Slow \u2014 disk swap</div>' +
          '<div class="anim-slots" data-p="' + id + '" data-t="slow"></div></div>' +
          '<div class="anim-outcome" data-p="' + id + '"></div>' +
          '</div>';
      }).join('') +
      '</div>' +
      '<div class="anim-legend">' +
      legend.map(function (l) {
        return '<div class="anim-litem"><div class="anim-lswatch" style="background:' +
          l.color + '"></div><span>' + l.label + '</span></div>';
      }).join('') +
      '</div>' +
      '<div class="anim-status"></div>' +
      '<div class="anim-controls">' +
      '<span class="anim-stepinfo"></span>' +
      '<button class="anim-btn anim-prev">\u2190 Prev</button>' +
      '<button class="anim-btn anim-next">Next \u2192</button>' +
      '</div>';

    function q(sel)  { return container.querySelector(sel); }

    function render(animate) {
      var s    = steps[cur];
      var last = cur === steps.length - 1;

      ids.forEach(function (id) {
        var fastEl = q('.anim-slots[data-p="' + id + '"][data-t="fast"]');
        var slowEl = q('.anim-slots[data-p="' + id + '"][data-t="slow"]');
        var outEl  = q('.anim-outcome[data-p="' + id + '"]');

        var freshFast = updateSlots(fastEl, s[id].fast, fastCap, s.need, fastCap);
        var freshSlow = updateSlots(slowEl, s[id].slow, s[id].slow.length, s.need, fastCap);

        if (animate) animateIn(freshFast.concat(freshSlow));

        if (last && outcomes[id]) {
          var o = outcomes[id];
          outEl.innerHTML = typeof o === 'string' ? o
            : '<span style="color:' + (o.good ? '#27ae60' : '#c0392b') + '">' +
              (o.good ? '\u2713' : '\u2717') + ' ' + o.text + '</span>';
        } else {
          outEl.textContent = '';
        }
      });

      q('.anim-status').textContent = s.desc;
      q('.anim-stepinfo').textContent = 'Step ' + (cur + 1) + ' / ' + steps.length;
      q('.anim-prev').disabled = cur === 0;
      q('.anim-next').disabled = last;
    }

    q('.anim-prev').addEventListener('click', function () { if (cur > 0)                   { cur--; render(true); } });
    q('.anim-next').addEventListener('click', function () { if (cur < steps.length - 1)    { cur++; render(true); } });

    render(false);
  }

  /* ------------------------------------------------------------------ */
  /* Dispatcher — add new types here                                      */
  /* ------------------------------------------------------------------ */
  var RENDERERS = {
    'storage-tiers': renderStorageTiers
  };

  function initContainer(container) {
    var scriptEl = container.querySelector('script[type="application/json"]');
    if (!scriptEl) return;
    var config;
    try { config = JSON.parse(scriptEl.textContent); }
    catch (e) { console.error('animation.js: bad JSON in container', e); return; }

    var renderer = RENDERERS[config.type];
    if (!renderer) { console.error('animation.js: unknown type', config.type); return; }
    renderer(container, config);
  }

  function initAll() {
    document.querySelectorAll('.animation-container').forEach(initContainer);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAll);
  } else {
    initAll();
  }
}());
