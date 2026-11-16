(function () {
  'use strict';

  var KEY = 'orderHistory.v1';
  var SYNC = /*__SYNC__*/null;          // { token, gist } — 빌드 시 주입
  var API = 'https://api.github.com/gists/';
  var FILE = 'orders.json';
  var remoteAt = 0;                     // 서버 상태의 updatedAt
  var pushing = false, pullTimer = null;
  var PRODUCTS = /*__PRODUCTS__*/[];
  var ICONS = /*__ICONS__*/[];
  var list = document.getElementById('orderList');
  var empty = document.getElementById('dkEmpty');
  var monthEl = document.getElementById('dkMonth');
  var totalEl = document.getElementById('dkTotal');
  var modal = document.getElementById('dkModal');
  var cardTitle = document.getElementById('dkTitle');
  var form = document.getElementById('dkForm');
  var toastEl = document.getElementById('dkToast');

  var orders = [];
  var editingId = null;
  var formIcon = null;

  function $(id) { return document.getElementById(id); }
  function uid() { return Date.now().toString(36) + Math.random().toString(36).slice(2, 7); }
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function won(n) { return '₩' + Number(n).toLocaleString('ko-KR'); }
  function priceText(o) {
    return o.currency === 'USD' ? 'US$' + Number(o.amount).toFixed(2) : won(o.amount);
  }
  function dateText(iso) {
    var p = String(iso).split('-');
    if (p.length !== 3) return iso;
    return p[0] + '. ' + Number(p[1]) + '. ' + Number(p[2]) + '.';
  }
  function today() {
    var d = new Date();
    var m = String(d.getMonth() + 1).padStart(2, '0');
    var day = String(d.getDate()).padStart(2, '0');
    return d.getFullYear() + '-' + m + '-' + day;
  }
  function toast(msg) {
    toastEl.textContent = msg;
    toastEl.classList.add('on');
    clearTimeout(toastEl._t);
    toastEl._t = setTimeout(function () { toastEl.classList.remove('on'); }, 1800);
  }
  function save() {
    try { localStorage.setItem(KEY, JSON.stringify(orders)); } catch (e) { toast('저장 공간이 부족합니다'); }
    queuePush();
  }
  function load() {
    try {
      var raw = JSON.parse(localStorage.getItem(KEY) || '[]');
      orders = Array.isArray(raw) ? raw : [];
    } catch (e) { orders = []; }
    try { remoteAt = Number(localStorage.getItem(KEY + '.at')) || 0; } catch (e) { remoteAt = 0; }
  }

  /* ── 다른 기기와 동기화(Gist) ──────────────────────────── */
  function mark(state) {
    var el = $('dkSync');
    if (!el) return;
    el.dataset.state = state;
    el.title = state === 'ok' ? '동기화됨'
      : state === 'err' ? '동기화 실패 — 오프라인 상태로 저장 중'
      : '동기화 중…';
  }

  function headers() {
    return { Authorization: 'token ' + SYNC.token, Accept: 'application/vnd.github+json' };
  }

  function apply(remote, at) {
    orders = Array.isArray(remote) ? remote : [];
    remoteAt = at;
    try {
      localStorage.setItem(KEY, JSON.stringify(orders));
      localStorage.setItem(KEY + '.at', String(remoteAt));
    } catch (e) { /* 무시 */ }
    render();
  }

  function pull() {
    if (!SYNC || !SYNC.token || !SYNC.gist) return;
    if (pushing) return;
    fetch(API + SYNC.gist, { headers: headers() })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (!data) { mark('err'); return; }
        var f = data.files && data.files[FILE];
        if (!f) { mark('ok'); return; }
        var at = Date.parse(data.updated_at) || 0;
        if (at > remoteAt) {
          var parsed;
          try { parsed = JSON.parse(f.content); } catch (e) { mark('err'); return; }
          if (pushing) { queuePull(); return; }
          apply(parsed.orders, at);
        }
        mark('ok');
      })
      .catch(function () { mark('err'); });
  }

  function queuePull() {
    clearTimeout(pullTimer);
    pullTimer = setTimeout(pull, 1200);
  }

  var pushTimer = null;
  function queuePush() {
    if (!SYNC || !SYNC.token || !SYNC.gist) return;
    clearTimeout(pushTimer);
    pushTimer = setTimeout(push, 700);
  }

  function push() {
    if (!SYNC || !SYNC.token || !SYNC.gist || pushing) return;
    pushing = true;
    mark('busy');
    fetch(API + SYNC.gist, {
      method: 'PATCH',
      headers: Object.assign({ 'Content-Type': 'application/json' }, headers()),
      body: JSON.stringify({ files: { 'orders.json': { content: JSON.stringify({ orders: orders }) } } })
    }).then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (!data) { mark('err'); return; }
        remoteAt = Date.parse(data.updated_at) || Date.now();
        try { localStorage.setItem(KEY + '.at', String(remoteAt)); } catch (e) { }
        mark('ok');
      })
      .catch(function () { mark('err'); })
      .then(function () { pushing = false; });
  }

  function startSync() {
    if (!SYNC || !SYNC.token || !SYNC.gist) return;
    pull();
    setInterval(function () {
      if (!document.hidden) pull();
    }, 3000);
    document.addEventListener('visibilitychange', function () {
      if (!document.hidden) pull();
    });
  }

  /* ── 요약(월·총액) ─────────────────────────────────────── */
  function updateSummary() {
    var paid = orders.filter(function (o) {
      return o.currency !== 'USD' && o.status !== '취소됨';
    });
    var sum = paid.reduce(function (a, o) { return a + Number(o.amount || 0); }, 0);
    var month = '';
    var dated = orders.map(function (o) { return o.date; }).filter(Boolean).sort();
    if (dated.length) month = Number(dated[dated.length - 1].split('-')[1]);
    else month = new Date().getMonth() + 1;
    monthEl.textContent = month + '월';
    totalEl.textContent = won(sum);
  }

  /* ── 목록 렌더 ─────────────────────────────────────────── */
  function toolsHtml(o, i) {
    return '<div class="dk-tools">' +
      '<button type="button" data-act="up" title="위로" ' + (i === 0 ? 'disabled' : '') + '>↑</button>' +
      '<button type="button" data-act="down" title="아래로" ' + (i === orders.length - 1 ? 'disabled' : '') + '>↓</button>' +
      '<button type="button" data-act="copy" title="복제">복제</button>' +
      '<button type="button" data-act="edit" title="편집">편집</button>' +
      '<button type="button" class="del" data-act="del" title="삭제">✕</button>' +
      '</div>';
  }

  function rowHtml(o, i) {
    return '<div class="RqCJic"><img class="T75of p36pgb" src="' + esc(o.icon) + '" alt="' + esc(o.title) + '"></div>' +
      '<div class="bBW4qb">' +
        '<div class="D9le5c">' +
          '<div class="SKMdtf"><div><span class="XqqpEd">' + esc(o.title) + '</span>' +
            (o.status ? '<div class="hmlfEe">' + esc(o.status) + '</div>' : '') +
          '</div>' +
          '<div class="V8HwNc">' + dateText(o.date) + '</div></div>' +
          '<div class="mshXob">' + priceText(o) + '</div>' +
        '</div>' +
        '<div class="mJ6jFd">' +
          '<div class="UdUOmc"><div class="SzAnZb">' +
            (o.report ? '<div class="Qfonhf"><button class="J0MfDf" type="button">문제 신고</button></div>' : '') +
            '<div class="Qfonhf"></div><div class="c82gZb"></div>' +
          '</div></div>' +
        '</div>' +
      '</div>';
  }

  function render() {
    list.innerHTML = orders.map(function (o, i) {
      return '<div class="U6fuTe" data-id="' + o.id + '">' + rowHtml(o, i) + toolsHtml(o, i) + '</div>';
    }).join('');
    empty.hidden = orders.length > 0;
    updateSummary();
  }

  function indexOf(id) {
    for (var i = 0; i < orders.length; i++) if (orders[i].id === id) return i;
    return -1;
  }

  /* ── 모달 ─────────────────────────────────────────────── */
  function setIcon(src) {
    formIcon = src || null;
    var wrap = $('dkIcons');
    Array.prototype.forEach.call(wrap.querySelectorAll('button[data-icon]'), function (b) {
      b.setAttribute('aria-pressed', b.getAttribute('data-icon') === formIcon ? 'true' : 'false');
    });
    $('dkUrl').value = formIcon && formIcon.indexOf('data:') !== 0 ? formIcon : '';
    $('dkPreview').src = formIcon || '';
    $('dkPreview').hidden = !formIcon;
  }

  function fillForm(o) {
    $('dkName').value = o ? o.title : '';
    $('dkDate').value = o ? o.date : today();
    $('dkAmount').value = o ? o.amount : '';
    $('dkCurrency').value = o ? o.currency : 'KRW';
    $('dkStatus').value = o ? (o.status || '') : '';
    $('dkReport').checked = o ? !!o.report : true;
    setIcon(o ? o.icon : (ICONS[0] && ICONS[0].src));
    setProduct(null);
  }

  function open(o) {
    editingId = o ? o.id : null;
    cardTitle.textContent = o ? '주문 편집' : '주문 추가';
    $('dkRepeatField').hidden = !!o;
    $('dkRepeat').value = 1;
    fillForm(o || null);
    modal.hidden = false;
    (document.body || document.documentElement).style.overflow = 'hidden';
    setTimeout(function () { $('dkName').focus(); }, 30);
  }

  function close() {
    modal.hidden = true;
    (document.body || document.documentElement).style.overflow = '';
    editingId = null;
  }

  /* ── 빠른 상품(이름·금액·아이콘 한 번에) ───────────────── */
  function setProduct(idx) {
    Array.prototype.forEach.call($('dkProducts').querySelectorAll('.dk-chip'), function (c, i) {
      c.setAttribute('aria-pressed', idx === i ? 'true' : 'false');
    });
  }

  (function buildProducts() {
    var wrap = $('dkProducts');
    if (!PRODUCTS.length) { wrap.parentElement.hidden = true; return; }
    PRODUCTS.forEach(function (p, i) {
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'dk-chip';
      b.setAttribute('aria-pressed', 'false');
      b.innerHTML = '<img src="' + p.icon + '" alt=""><span>' + esc(p.label) + '</span>' +
        '<em>' + won(p.amount) + '</em>';
      b.addEventListener('click', function () {
        $('dkName').value = p.label;
        $('dkAmount').value = p.amount;
        $('dkCurrency').value = 'KRW';
        setIcon(p.icon);
        setProduct(i);
        $('dkRepeat').focus();
        $('dkRepeat').select();
      });
      wrap.appendChild(b);
    });
  })();

  /* ── 아이콘 그리드 ────────────────────────────────────── */
  (function buildPresets() {
    var wrap = $('dkIcons');
    ICONS.forEach(function (p) {
      var b = document.createElement('button');
      b.type = 'button';
      b.setAttribute('data-icon', p.src);
      b.setAttribute('aria-pressed', 'false');
      b.title = p.name;
      b.innerHTML = '<img src="' + p.src + '" alt="">';
      wrap.appendChild(b);
    });
    wrap.addEventListener('click', function (ev) {
      var b = ev.target.closest('button[data-icon]');
      if (b) { setIcon(b.getAttribute('data-icon')); setProduct(null); }
    });
  })();

  $('dkUrl').addEventListener('input', function (ev) {
    var v = ev.target.value.trim();
    formIcon = v || null;
    $('dkPreview').src = v;
    $('dkPreview').hidden = !v;
    Array.prototype.forEach.call($('dkIcons').querySelectorAll('button[data-icon]'), function (b) {
      b.setAttribute('aria-pressed', 'false');
    });
  });

  $('dkPick').addEventListener('click', function () { $('dkFile').click(); });

  $('dkFile').addEventListener('change', function (ev) {
    var f = ev.target.files && ev.target.files[0];
    if (!f) return;
    var fr = new FileReader();
    fr.onload = function () {
      var img = new Image();
      img.onload = function () {
        var s = Math.min(img.width, img.height);
        var cv = document.createElement('canvas');
        cv.width = cv.height = 128;
        cv.getContext('2d').drawImage(img, (img.width - s) / 2, (img.height - s) / 2, s, s, 0, 0, 128, 128);
        setIcon(cv.toDataURL('image/webp', 0.92));
      };
      img.src = fr.result;
    };
    fr.readAsDataURL(f);
    ev.target.value = '';
  });

  /* ── 폼 제출 ──────────────────────────────────────────── */
  form.addEventListener('submit', function (ev) {
    ev.preventDefault();
    var title = $('dkName').value.trim();
    var amount = Number($('dkAmount').value);
    if (!title) { $('dkName').focus(); return; }
    if (!isFinite(amount) || amount < 0) { $('dkAmount').focus(); return; }

    var base = {
      title: title,
      date: $('dkDate').value || today(),
      amount: amount,
      currency: $('dkCurrency').value,
      status: $('dkStatus').value || null,
      report: $('dkReport').checked,
      icon: formIcon || (PRESETS[0] && PRESETS[0].src) || ''
    };

    if (editingId) {
      var at = indexOf(editingId);
      if (at > -1) orders[at] = Object.assign({}, orders[at], base);
      save(); render(); close(); toast('수정했습니다');
      return;
    }

    var n = Math.max(1, Math.min(50, Number($('dkRepeat').value) || 1));
    for (var i = 0; i < n; i++) orders.push(Object.assign({ id: uid() }, base));
    save(); render(); close();
    toast(n > 1 ? n + '건을 추가했습니다' : '추가했습니다');
    var last = list.lastElementChild;
    if (last) last.scrollIntoView({ block: 'nearest' });
  });

  /* ── 행 도구 ──────────────────────────────────────────── */
  list.addEventListener('click', function (ev) {
    var btn = ev.target.closest('button[data-act]');
    if (!btn) return;
    var row = ev.target.closest('.U6fuTe');
    if (!row) return;
    var at = indexOf(row.getAttribute('data-id'));
    if (at < 0) return;
    var act = btn.getAttribute('data-act');

    if (act === 'up' && at > 0) {
      orders.splice(at - 1, 0, orders.splice(at, 1)[0]);
      save(); render();
    } else if (act === 'down' && at < orders.length - 1) {
      orders.splice(at + 1, 0, orders.splice(at, 1)[0]);
      save(); render();
    } else if (act === 'copy') {
      orders.splice(at + 1, 0, Object.assign({}, orders[at], { id: uid() }));
      save(); render(); toast('복제했습니다');
    } else if (act === 'edit') {
      open(orders[at]);
    } else if (act === 'del') {
      orders.splice(at, 1);
      save(); render(); toast('삭제했습니다');
    }
  });

  /* ── 캡쳐(편집 UI 숨기고 이미지로 저장) ───────────────── */
  function stamp() {
    var d = new Date(), p = function (n) { return String(n).padStart(2, '0'); };
    return 'order-history-' + d.getFullYear() + p(d.getMonth() + 1) + p(d.getDate()) + '-' +
      p(d.getHours()) + p(d.getMinutes()) + '.png';
  }

  /* 캡쳐용: 마스크 아이콘과 리거처 아이콘을 캔버스 그림으로 굳힌다 */
  function freezeIcons() {
    var undo = [];

    Array.prototype.forEach.call(document.querySelectorAll('.google-material-icons'), function (el) {
      var txt = (el.textContent || '').trim();
      if (!txt) return;
      var cs = getComputedStyle(el);
      var s = Math.round(parseFloat(cs.fontSize) || 18);
      var cv = document.createElement('canvas');
      cv.width = cv.height = s * 2;
      var ctx = cv.getContext('2d');
      ctx.scale(2, 2);
      ctx.font = cs.fontSize + ' "Google Material Icons"';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillStyle = cs.color;
      ctx.fillText(txt, s / 2, s / 2 + 1);
      var img = new Image();
      img.src = cv.toDataURL();
      img.width = img.height = s;
      img.setAttribute('aria-hidden', 'true');
      img.style.cssText = 'display:inline-block;vertical-align:-4px';
      el.style.display = 'none';
      el.parentNode.insertBefore(img, el.nextSibling);
      undo.push(function () { img.remove(); el.style.display = ''; });
    });

    Array.prototype.forEach.call(document.querySelectorAll('.CkmxFd, [style*="mask-image"], [style*="mask:"]'), function (el) {
      var cs = getComputedStyle(el);
      var mask = cs.webkitMaskImage || cs.maskImage;
      if (!mask || mask === 'none') return;
      var m = mask.match(/url\((['"]?)(.*?)\1\)/);
      if (!m) return;
      var w = el.offsetWidth || 24;
      var h = el.offsetHeight || 24;
      var img = new Image();
      img.onload = function () {
        var cv = document.createElement('canvas');
        cv.width = w * 4;
        cv.height = h * 4;
        var ctx = cv.getContext('2d');
        ctx.scale(4, 4);
        ctx.fillStyle = cs.backgroundColor && cs.backgroundColor !== 'rgba(0, 0, 0, 0)'
          ? cs.backgroundColor : cs.color;
        ctx.fillRect(0, 0, w, h);
        ctx.globalCompositeOperation = 'destination-in';
        ctx.drawImage(img, 0, 0, w, h);
        el.dataset.dkStyle = el.getAttribute('style') || '';
        el.style.maskImage = 'none';
        el.style.webkitMaskImage = 'none';
        el.style.backgroundColor = 'transparent';
        el.style.backgroundImage = 'url(' + cv.toDataURL() + ')';
        el.style.backgroundSize = 'contain';
        el.style.backgroundPosition = '50%';
        el.style.backgroundRepeat = 'no-repeat';
      };
      img.src = m[2];
      undo.push(function () {
        if (el.dataset.dkStyle !== undefined) {
          el.setAttribute('style', el.dataset.dkStyle);
          delete el.dataset.dkStyle;
        }
      });
    });

    return function () { undo.forEach(function (f) { f(); }); };
  }

  function capture() {
    if (typeof html2canvas !== 'function') { toast('캡쳐 모듈을 불러오지 못했습니다'); return; }
    if (!modal.hidden) close();
    var btn = $('dkShot');
    btn.disabled = true;
    btn.querySelector('span').textContent = '캡쳐 중…';
    document.body.classList.add('capture-mode');
    var unfreeze = freezeIcons();

    var ready = Promise.resolve();
    if (document.fonts && document.fonts.ready) ready = document.fonts.ready;
    ready.then(function () {
      return new Promise(function (r) { requestAnimationFrame(function () { requestAnimationFrame(r); }); });
    }).then(function () {
      return html2canvas(document.body, {
        backgroundColor: '#ffffff',
        scale: 2,
        logging: false,
        useCORS: true,
        windowWidth: document.documentElement.clientWidth,
        ignoreElements: function (el) { return el.classList && el.classList.contains('dk-toast'); }
      });
    }).then(function (canvas) {
      var a = document.createElement('a');
      a.href = canvas.toDataURL('image/png');
      a.download = stamp();
      a.click();
      toast('이미지를 저장했습니다');
    }).catch(function () {
      toast('캡쳐에 실패했습니다');
    }).then(function () {
      document.body.classList.remove('capture-mode');
      unfreeze();
      btn.disabled = false;
      btn.querySelector('span').textContent = '캡쳐';
    });
  }

  /* ── 하단 도구: 내보내기/가져오기/전체 삭제 ───────────── */
  $('dkAdd').addEventListener('click', function () { open(null); });
  $('dkShot').addEventListener('click', capture);
  $('dkCancel').addEventListener('click', close);
  $('dkX').addEventListener('click', close);
  modal.addEventListener('mousedown', function (ev) { if (ev.target === modal) close(); });
  document.addEventListener('keydown', function (ev) { if (ev.key === 'Escape' && !modal.hidden) close(); });

  $('dkExport').addEventListener('click', function () {
    var blob = new Blob([JSON.stringify(orders, null, 2)], { type: 'application/json' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'orders-' + today() + '.json';
    a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 2000);
  });

  $('dkImport').addEventListener('click', function () { $('dkImportFile').click(); });
  $('dkImportFile').addEventListener('change', function (ev) {
    var f = ev.target.files && ev.target.files[0];
    if (!f) return;
    var fr = new FileReader();
    fr.onload = function () {
      try {
        var data = JSON.parse(fr.result);
        if (!Array.isArray(data)) throw new Error('형식 오류');
        orders = data.map(function (o) {
          return {
            id: uid(), title: String(o.title || '상품'),
            date: o.date || today(), amount: Number(o.amount) || 0,
            currency: o.currency === 'USD' ? 'USD' : 'KRW',
            status: o.status || null, report: !!o.report, icon: o.icon || ''
          };
        });
        save(); render(); close(); toast(orders.length + '건을 불러왔습니다');
      } catch (e) { toast('JSON 파일을 읽을 수 없습니다'); }
    };
    fr.readAsText(f);
    ev.target.value = '';
  });

  $('dkClear').addEventListener('click', function () {
    if (!orders.length) return toast('이미 비어 있습니다');
    if (!confirm('주문 내역을 모두 지울까요? (' + orders.length + '건)')) return;
    orders = []; save(); render(); close(); toast('모두 지웠습니다');
  });

  load();
  render();
  startSync();
})();
