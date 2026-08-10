/**
 * LyraERP Dashboard — Drag & Drop (v5 — Server-side layout persistence)
 * Place in:  static/js/dashboard_dragdrop.js
 *
 * Layout is saved to the SERVER (per user) so it persists across
 * browsers, devices, and incognito windows.
 *
 * Requires LYRA_LAYOUT_API to be defined in the template:
 *   var LYRA_LAYOUT_API = {
 *     getUrl:  "{% url 'dashboard_layout_get' %}",
 *     saveUrl: "{% url 'dashboard_layout_save' %}",
 *     csrf:    "{{ csrf_token }}"
 *   };
 */
(function () {
  'use strict';

  var SORTABLES = [];
  var CONFIG = (typeof LYRA_ARRANGE_CONFIG !== 'undefined') ? LYRA_ARRANGE_CONFIG : {};
  var STORE_PREFIX = CONFIG.storagePrefix || '';
  var STORAGE_KEY = CONFIG.localStorageKey || 'lyra_layout';
  var SECTION_CONTAINER = CONFIG.sectionContainer || '.lyra-dash';
  var ENABLE_SECTIONS = CONFIG.enableSections !== false;
  var CARD_GROUPS = CONFIG.cardGroups || [
    { container: '#kpiGrid', child: '.kpi-card', key: 'kpi' },
    { container: '#modGrid', child: '.mod-card', key: 'mod' },
    { container: '.charts-row', child: '.panel', key: 'charts' },
    { container: '.mid-row', child: '.panel', key: 'mid' },
    { container: '.bottom-row', child: '.panel', key: 'bot' }
  ];
  var ARRANGE_LABEL = CONFIG.arrangeLabel || 'Arrange Layout';
  var DONE_LABEL = CONFIG.doneLabel || 'Done Arranging';
  var RESET_CONFIRM = CONFIG.resetConfirm || 'Reset dashboard to default layout?';

  function layoutKey(key) {
    return STORE_PREFIX + key;
  }

  /* ─────────────────────────────────────────
     API  — save/load from server
     Falls back to localStorage if API not configured
  ───────────────────────────────────────── */
  var API = (typeof LYRA_LAYOUT_API !== 'undefined') ? LYRA_LAYOUT_API : null;

  /* In-memory cache of the full layout object
     { sections: [...], kpi: [...], mod: [...], charts: [...], mid: [...], bot: [...] } */
  var _layoutCache = null;

  /* Load full layout from server once, then use cache */
  function fetchLayout(cb) {
    if (_layoutCache !== null) { cb(_layoutCache); return; }

    if (!API) {
      /* fallback: read from localStorage */
      try {
        _layoutCache = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
      } catch (e) {
        _layoutCache = {};
      }
      cb(_layoutCache);
      return;
    }

    fetch(API.getUrl, { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        _layoutCache = data.layout || {};
        cb(_layoutCache);
      })
      .catch(function () {
        _layoutCache = {};
        cb(_layoutCache);
      });
  }

  /* Debounce helper — waits 800ms after last call before saving */
  var _saveTimer = null;
  function scheduleSave() {
    if (_saveTimer) clearTimeout(_saveTimer);
    _saveTimer = setTimeout(function () { persistLayout(); }, 800);
  }

  function persistLayout() {
    if (!_layoutCache) return;

    if (!API) {
      /* fallback: write to localStorage */
      try { localStorage.setItem(STORAGE_KEY, JSON.stringify(_layoutCache)); } catch (e) {}
      return;
    }

    fetch(API.saveUrl, {
      method     : 'POST',
      credentials: 'same-origin',
      headers    : {
        'Content-Type': 'application/json',
        'X-CSRFToken' : API.csrf
      },
      body: JSON.stringify({ layout: _layoutCache })
    }).catch(function (err) {
      console.warn('[LyraDrag] Failed to save layout:', err);
    });
  }

  function setKey(key, ids) {
    if (!_layoutCache) _layoutCache = {};
    _layoutCache[layoutKey(key)] = ids;
    scheduleSave();
  }

  function getKey(key) {
    return (_layoutCache && _layoutCache[layoutKey(key)]) ? _layoutCache[layoutKey(key)] : null;
  }

  function clearLayout() {
    if (!_layoutCache) _layoutCache = {};
    if (STORE_PREFIX) {
      Object.keys(_layoutCache).forEach(function (key) {
        if (key.indexOf(STORE_PREFIX) === 0) delete _layoutCache[key];
      });
    } else {
      delete _layoutCache.sections;
      CARD_GROUPS.forEach(function (group) {
        delete _layoutCache[group.key];
      });
    }
    if (!API) {
      try {
        if (STORE_PREFIX) {
          localStorage.setItem(STORAGE_KEY, JSON.stringify(_layoutCache));
        } else {
          localStorage.removeItem(STORAGE_KEY);
        }
      } catch (e) {}
      return;
    }
    fetch(API.saveUrl, {
      method     : 'POST',
      credentials: 'same-origin',
      headers    : {
        'Content-Type': 'application/json',
        'X-CSRFToken' : API.csrf
      },
      body: JSON.stringify({ layout: _layoutCache })
    });
  }

  /* ─────────────────────────────────────────
     LOAD SORTABLEJS FROM CDN
  ───────────────────────────────────────── */
  function loadSortable(cb) {
    if (window.Sortable) { cb(); return; }
    var s    = document.createElement('script');
    s.src    = 'https://cdnjs.cloudflare.com/ajax/libs/Sortable/1.15.2/Sortable.min.js';
    s.onload = cb;
    s.onerror = function () { console.warn('[LyraDrag] SortableJS failed to load'); };
    document.head.appendChild(s);
  }

  /* ─────────────────────────────────────────
     FIX ANIMATIONS
  ───────────────────────────────────────── */
  function freezeAnim(el) {
    el.style.opacity   = '1';
    el.style.animation = 'none';
    el.style.transform = 'none';
  }

  /* ─────────────────────────────────────────
     DRAG HANDLE SVG
  ───────────────────────────────────────── */
  var DOTS_SVG = '<svg viewBox="0 0 10 16" xmlns="http://www.w3.org/2000/svg">'
    + '<circle cx="3" cy="2"  r="1.4"/><circle cx="7" cy="2"  r="1.4"/>'
    + '<circle cx="3" cy="6"  r="1.4"/><circle cx="7" cy="6"  r="1.4"/>'
    + '<circle cx="3" cy="10" r="1.4"/><circle cx="7" cy="10" r="1.4"/>'
    + '<circle cx="3" cy="14" r="1.4"/><circle cx="7" cy="14" r="1.4"/>'
    + '</svg>';

  /* ─────────────────────────────────────────
     STYLES
  ───────────────────────────────────────── */
  function injectStyles() {
    if (document.getElementById('_lyra_drag_css')) return;
    var style = document.createElement('style');
    style.id  = '_lyra_drag_css';
    style.textContent = ''
      + '#lyraArrangeBtn {'
      + '  position:fixed;top:12px;right:22px;z-index:9500;'
      + '  display:flex;align-items:center;gap:8px;'
      + '  background:#ffffff;border:1.5px solid #dde0f2;border-radius:40px;'
      + '  padding:7px 18px;box-shadow:0 3px 16px rgba(85,88,139,.16);'
      + '  font-family:"Plus Jakarta Sans",sans-serif;'
      + '  font-size:12px;font-weight:700;color:#55588b;'
      + '  cursor:pointer;user-select:none;'
      + '  transition:background .2s,color .2s,box-shadow .2s;'
      + '}'
      + '#lyraArrangeBtn:hover{box-shadow:0 6px 24px rgba(85,88,139,.24);}'
      + '#lyraArrangeBtn.active{background:#55588b;color:#fff;border-color:#55588b;}'
      + '#lyraArrangeBtn .btn-ico{font-size:15px;line-height:1;}'
      + '#lyraArrangeBtn .btn-reset{'
      + '  display:none;background:rgba(255,255,255,.18);'
      + '  border:1px solid rgba(255,255,255,.35);border-radius:20px;'
      + '  padding:2px 10px;font-size:11px;color:#fff;'
      + '  cursor:pointer;font-weight:700;margin-left:4px;'
      + '}'
      + '#lyraArrangeBtn.active .btn-reset{display:inline-block;}'

      /* saving indicator */
      + '#lyraSavingDot{'
      + '  position:fixed;top:46px;right:22px;z-index:9500;'
      + '  font-size:10px;font-weight:600;color:#55588b;'
      + '  display:none;align-items:center;gap:5px;'
      + '  background:#fff;border:1px solid #dde0f2;border-radius:20px;'
      + '  padding:3px 10px;box-shadow:0 2px 8px rgba(85,88,139,.1);'
      + '}'
      + '#lyraSavingDot.show{display:flex;}'
      + '#lyraSavingDot .dot{'
      + '  width:6px;height:6px;border-radius:50%;background:#55588b;'
      + '  animation:lyraPulse .8s infinite;'
      + '}'
      + '@keyframes lyraPulse{0%,100%{opacity:1;}50%{opacity:.3;}}'

      /* card handle */
      + '.lyra-drag-handle{'
      + '  position:absolute;top:9px;right:9px;'
      + '  width:24px;height:24px;border-radius:7px;'
      + '  background:rgba(85,88,139,.07);border:1px solid rgba(85,88,139,.18);'
      + '  display:flex;align-items:center;justify-content:center;'
      + '  cursor:grab;opacity:0;pointer-events:none;'
      + '  transition:opacity .18s,background .18s;z-index:30;'
      + '}'
      + '.lyra-drag-handle svg{width:10px;height:13px;fill:#55588b;display:block;}'
      + '.lyra-drag-handle:active{cursor:grabbing;}'

      /* section handle */
      + '.lyra-section-handle{'
      + '  width:28px;height:28px;border-radius:8px;'
      + '  background:rgba(85,88,139,.07);border:1px solid rgba(85,88,139,.18);'
      + '  display:inline-flex;align-items:center;justify-content:center;'
      + '  cursor:grab;opacity:0;pointer-events:none;'
      + '  transition:opacity .18s,background .18s;'
      + '  flex-shrink:0;margin-right:8px;'
      + '}'
      + '.lyra-section-handle svg{width:10px;height:13px;fill:#55588b;display:block;}'
      + '.lyra-section-handle:active{cursor:grabbing;}'
      + '.lyra-synth-head{display:flex;align-items:center;padding-bottom:10px;}'

      /* show in arrange mode */
      + 'body.lyra-arrange-mode .lyra-drag-handle,'
      + 'body.lyra-arrange-mode .lyra-section-handle{opacity:1;pointer-events:auto;}'
      + 'body.lyra-arrange-mode .lyra-drag-handle:hover,'
      + 'body.lyra-arrange-mode .lyra-section-handle:hover{background:rgba(85,88,139,.18);}'

      /* container outlines */
      + 'body.lyra-arrange-mode #kpiGrid,'
      + 'body.lyra-arrange-mode #modGrid,'
      + 'body.lyra-arrange-mode .charts-row,'
      + 'body.lyra-arrange-mode .mid-row,'
      + 'body.lyra-arrange-mode .bottom-row{'
      + '  outline:2px dashed rgba(85,88,139,.22);border-radius:16px;min-height:60px;'
      + '}'
      + 'body.lyra-arrange-mode .lyra-sortable-container{'
      + '  outline:2px dashed rgba(85,88,139,.22);border-radius:16px;min-height:60px;'
      + '}'
      + 'body.lyra-arrange-mode .lyra-section-wrap{'
      + '  outline:1px dashed rgba(85,88,139,.14);border-radius:16px;padding:2px;'
      + '}'

      /* sortable states */
      + '.lyra-ghost{opacity:.25!important;outline:2px dashed #55588b!important;border-radius:14px!important;background:#eef0fb!important;}'
      + '.lyra-section-ghost{opacity:.20!important;outline:2px dashed #55588b!important;border-radius:16px!important;background:#eef0fb!important;}'
      + '.lyra-chosen{cursor:grabbing!important;}'
      + '.lyra-drag-clone{opacity:1!important;box-shadow:0 20px 50px rgba(85,88,139,.28)!important;transform:rotate(1deg) scale(1.02)!important;}'
      + '.lyra-section-clone{opacity:.95!important;box-shadow:0 24px 60px rgba(85,88,139,.22)!important;transform:scale(1.01)!important;border-radius:16px!important;}'

      /* always keep cards visible */
      + '#kpiGrid .kpi-card,#modGrid .mod-card,'
      + '.charts-row .panel,.mid-row .panel,.bottom-row .panel{opacity:1!important;}';

    document.head.appendChild(style);
  }

  /* ─────────────────────────────────────────
     SAVING INDICATOR
  ───────────────────────────────────────── */
  function showSaving() {
    var dot = document.getElementById('lyraSavingDot');
    if (dot) dot.classList.add('show');
  }
  function hideSaving() {
    var dot = document.getElementById('lyraSavingDot');
    if (dot) dot.classList.remove('show');
  }

  function buildSavingDot() {
    var el = document.createElement('div');
    el.id  = 'lyraSavingDot';
    el.innerHTML = '<span class="dot"></span> Saving layout...';
    document.body.appendChild(el);
  }

  /* Override scheduleSave to show/hide indicator */
  var _origScheduleSave = scheduleSave;
  scheduleSave = function () {
    showSaving();
    if (_saveTimer) clearTimeout(_saveTimer);
    _saveTimer = setTimeout(function () {
      persistLayout();
      /* hide dot after a short delay so user sees confirmation */
      setTimeout(hideSaving, 1200);
    }, 800);
  };

  /* ─────────────────────────────────────────
     SECTION WRAPPING
  ───────────────────────────────────────── */
  function wrapSections(dash) {
    var children = Array.prototype.slice.call(dash.children);
    children.forEach(function (child, i) {
      if (/^(STYLE|SCRIPT|LINK|TEMPLATE|META)$/i.test(child.tagName)) return;
      if (child.classList.contains('lyra-section-wrap')) return;
      var wrap = document.createElement('div');
      wrap.className = 'lyra-section-wrap';
      var sLbl = child.querySelector('.s-lbl');
      var slug = sLbl
        ? sLbl.textContent.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 30)
        : 'section-' + i;
      wrap.dataset.lyraId = 'sec__' + slug;
      dash.insertBefore(wrap, child);
      wrap.appendChild(child);
      addSectionHandle(wrap, child);
    });
  }

  function addSectionHandle(wrap, inner) {
    if (wrap.querySelector('.lyra-section-handle')) return;
    var handle = document.createElement('div');
    handle.className = 'lyra-section-handle';
    handle.title     = 'Drag to reorder section';
    handle.innerHTML = DOTS_SVG;
    var sHead = inner.querySelector('.s-head');
    if (sHead) {
      sHead.insertBefore(handle, sHead.firstChild);
    } else {
      var strip = document.createElement('div');
      strip.className = 'lyra-synth-head';
      strip.appendChild(handle);
      wrap.insertBefore(strip, inner);
    }
  }

  /* ─────────────────────────────────────────
     SECTION-LEVEL SORTABLE
  ───────────────────────────────────────── */
  function makeSectionSortable(dash, layout) {
    if (!dash) return;

    wrapSections(dash);

    /* restore saved order */
    var saved = getKey('sections');
    if (saved && saved.length) {
      saved.forEach(function (id) {
        var el = dash.querySelector('.lyra-section-wrap[data-lyra-id="' + id + '"]');
        if (el) dash.appendChild(el);
      });
    }

    var inst = Sortable.create(dash, {
      animation    : 260,
      handle       : '.lyra-section-handle',
      draggable    : '.lyra-section-wrap',
      ghostClass   : 'lyra-section-ghost',
      chosenClass  : 'lyra-chosen',
      dragClass    : 'lyra-section-clone',
      disabled     : true,
      forceFallback: false,
      onEnd: function () {
        var ids = [];
        var wraps = dash.children;
        for (var i = 0; i < wraps.length; i++) {
          if (wraps[i].dataset.lyraId) ids.push(wraps[i].dataset.lyraId);
        }
        setKey('sections', ids);
      }
    });

    SORTABLES.push(inst);
  }

  /* ─────────────────────────────────────────
     CARD-LEVEL SORTABLE
  ───────────────────────────────────────── */
  function stampCardIds(container, childSel, prefix) {
    container.querySelectorAll(':scope > ' + childSel).forEach(function (el, i) {
      if (!el.dataset.lyraId) {
        var label = el.querySelector('.kpi-label, .crm-kpi-label, .mod-name, .panel-title');
        var slug  = label
          ? label.textContent.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 30)
          : String(i);
        el.dataset.lyraId = prefix + '__' + slug;
      }
    });
  }

  function restoreCardOrder(container, childSel, saved) {
    if (!saved || !saved.length) return;
    saved.forEach(function (id) {
      var el = container.querySelector('[data-lyra-id="' + id + '"]');
      if (el) container.appendChild(el);
    });
  }

  function addCardHandle(el) {
    if (el.querySelector('.lyra-drag-handle')) return;
    var h = document.createElement('div');
    h.className = 'lyra-drag-handle';
    h.title     = 'Drag to reorder';
    h.innerHTML = DOTS_SVG;
    el.style.position = 'relative';
    el.appendChild(h);
  }

  function makeSortable(container, childSel, storeKey, layout) {
    if (!container) return;
    container.classList.add('lyra-sortable-container');

    stampCardIds(container, childSel, storeKey);

    container.querySelectorAll(':scope > ' + childSel).forEach(function (el) {
      freezeAnim(el);
      addCardHandle(el);
    });

    restoreCardOrder(container, childSel, getKey(storeKey));

    var inst = Sortable.create(container, {
      animation    : 200,
      handle       : '.lyra-drag-handle',
      ghostClass   : 'lyra-ghost',
      chosenClass  : 'lyra-chosen',
      dragClass    : 'lyra-drag-clone',
      disabled     : true,
      forceFallback: false,
      onEnd: function () {
        var ids = [];
        container.querySelectorAll(':scope > ' + childSel).forEach(function (el) {
          ids.push(el.dataset.lyraId);
        });
        setKey(storeKey, ids);
      }
    });

    SORTABLES.push(inst);
  }

  /* ─────────────────────────────────────────
     ARRANGE MODE TOGGLE
  ───────────────────────────────────────── */
  var arrangeActive = false;

  function toggleArrange() {
    arrangeActive = !arrangeActive;
    var btn = document.getElementById('lyraArrangeBtn');
    btn.classList.toggle('active', arrangeActive);
    btn.querySelector('.btn-lbl').textContent = arrangeActive ? DONE_LABEL : ARRANGE_LABEL;
    document.body.classList.toggle('lyra-arrange-mode', arrangeActive);
    SORTABLES.forEach(function (s) { s.option('disabled', !arrangeActive); });
  }

  /* ─────────────────────────────────────────
     TOOLBAR
  ───────────────────────────────────────── */
  function buildToolbar() {
    var btn = document.createElement('div');
    btn.id  = 'lyraArrangeBtn';
    btn.innerHTML =
      '<span class="btn-ico">&#x283F;</span>'
      + '<span class="btn-lbl">' + ARRANGE_LABEL + '</span>'
      + '<span class="btn-reset">&#x21BA; Reset</span>';

    btn.addEventListener('click', function (e) {
      if (e.target.classList.contains('btn-reset')) {
        if (confirm(RESET_CONFIRM)) {
          clearLayout();
          window.location.reload();
        }
        return;
      }
      toggleArrange();
    });

    document.body.appendChild(btn);
    buildSavingDot();
  }

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && arrangeActive) toggleArrange();
  });

  /* ─────────────────────────────────────────
     BOOT
  ───────────────────────────────────────── */
  function boot() {
    injectStyles();

    /* Fetch layout from server FIRST, then initialise everything */
    fetchLayout(function (layout) {
      setTimeout(function () {
        var dash = document.querySelector(SECTION_CONTAINER);

        /* Section-level */
        if (ENABLE_SECTIONS) makeSectionSortable(dash, layout);

        /* Card-level */
        CARD_GROUPS.forEach(function (group) {
          makeSortable(
            document.querySelector(group.container),
            group.child,
            group.key,
            layout
          );
        });

        buildToolbar();
      }, 300);
    });
  }

  loadSortable(function () {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', boot);
    } else {
      boot();
    }
  });

})();
