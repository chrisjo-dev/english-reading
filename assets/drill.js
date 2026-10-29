// 지문 페이지 단어 암기 반복(이슈 #16). tools/drill.py 가 페이지에 자료와 이 파일을 넣는다.
(function () {
  var dataEl = document.getElementById('drill-data');
  var P = location.pathname.split('/'), LANG = P[1] || '', DAY = P[2] || '';
  var CARDS = [];
  try { CARDS = dataEl ? JSON.parse(dataEl.textContent) : []; } catch (e) {}
  var KEY = 'drill:v1', INT = [1, 3, 7, 14], SPEECH = { en: 'en-US', ja: 'ja-JP', de: 'de-DE' };
  var ICON_X = '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M5 5l10 10M15 5L5 15"/></svg>';
  var ICON_SPK = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 5 6 9H3v6h3l5 4z"/><path d="M15.5 8.5a5 5 0 0 1 0 7"/><path d="M18.5 5.5a9 9 0 0 1 0 13"/></svg>';
  var ICON_TAP = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 11V5a2 2 0 0 1 4 0v6"/><path d="M13 10a2 2 0 0 1 4 0v2"/><path d="M17 12a2 2 0 0 1 4 0v3a7 7 0 0 1-7 7h-1a7 7 0 0 1-5.6-2.8L4 15.5a2 2 0 0 1 3-2.6L9 15"/></svg>';
  CARDS.forEach(function (c) { c.l = LANG; c.d = DAY; c.k = LANG + '|' + DAY + '|' + c.w; });

  function load() { try { var v = JSON.parse(localStorage.getItem(KEY)); if (v && v.items) return v; } catch (e) {} return { items: {} }; }
  function store(db) { try { localStorage.setItem(KEY, JSON.stringify(db)); } catch (e) {} }
  function pad(n) { return (n < 10 ? '0' : '') + n; }
  function ymd(d) { return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); }
  function parse(s) { var a = s.split('-'); return new Date(+a[0], a[1] - 1, +a[2]); }
  function today() { return ymd(new Date()); }
  function add(s, n) { var d = parse(s); d.setDate(d.getDate() + n); return ymd(d); }
  function md(s) { var d = parse(s); return (d.getMonth() + 1) + '/' + d.getDate(); }
  function kday(s) { var d = parse(s); return (d.getMonth() + 1) + '월 ' + d.getDate() + '일'; }
  function ga(name, p) { if (typeof gtag === 'function') gtag('event', name, p); }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function shuffle(a) { for (var i = a.length - 1; i > 0; i--) { var j = Math.floor(Math.random() * (i + 1)), t = a[i]; a[i] = a[j]; a[j] = t; } return a; }

  // 복습할 단어: 같은 언어, 복습일이 오늘이거나 지난 단어
  function dueCards() {
    var db = load(), t = today(), out = [];
    for (var k in db.items) { var c = db.items[k]; if (c.l === LANG && c.due && c.due <= t) out.push(c); }
    return out.sort(function (a, b) { return a.due < b.due ? -1 : a.due > b.due ? 1 : 0; });
  }
  function showDue() {
    var el = document.getElementById('dr-due'); if (!el) return;
    var due = dueCards(); el.hidden = !due.length; if (!due.length) return;
    var days = {}, nd = 0, wrong = 0;
    due.forEach(function (c) { if (!days[c.d]) { days[c.d] = 1; nd++; } if (c.x > 0) wrong++; });
    var one = Object.keys(days)[0];
    var src = nd > 1 ? '지문 ' + nd + '개의 단어 ' + due.length + '개' : (one === add(today(), -1) ? '어제' : kday(one)) + ' 단어 ' + due.length + '개';
    document.getElementById('dr-due-n').textContent = due.length;
    document.getElementById('dr-due-t').textContent = '오늘 복습할 단어 ' + due.length + '개';
    document.getElementById('dr-due-s').textContent = src + (wrong ? ', 오답 ' + wrong + '개' : '');
  }

  // 화면
  var root = null, S = null;
  function open() {
    if (!root) {
      root = document.createElement('div'); root.className = 'dr'; root.setAttribute('role', 'dialog'); root.setAttribute('aria-modal', 'true');
      root.addEventListener('click', onClick);
      root.addEventListener('pointerdown', onDown);
      document.body.appendChild(root);
    }
    root.hidden = false; document.body.classList.add('dr-open');
  }
  function close() {
    hush();
    if (root) { root.hidden = true; root.innerHTML = ''; }
    document.body.classList.remove('dr-open'); S = null; showDue();
  }
  document.addEventListener('keydown', function (e) {
    if (!S) return;
    if (e.key === 'Escape') return close();
    if (S.mode !== 'card' || !S.queue.length) return;
    if (!S.flip && (e.key === 'Enter' || e.key === ' ') && e.target.classList && e.target.classList.contains('tap')) { e.preventDefault(); flip(); }
    else if (S.flip && (e.key === 'ArrowRight' || e.key === 'ArrowLeft')) { e.preventDefault(); judge(e.key === 'ArrowRight' ? 'yes' : 'no', e.key === 'ArrowRight' ? 1 : -1); }
  });

  function bar(n) {
    return '<div class="dr-bar"><button class="dr-x" type="button" data-act="close" aria-label="닫기">' + ICON_X + '</button><span class="t">' + S.title + '</span><span class="n">' + n + '</span></div>';
  }
  // 진행 막대 폭은 마크업 style 속성 대신 CSSOM으로 넣는다(CSP style-src에 걸리지 않게).
  function widths() { [].forEach.call(root.querySelectorAll('[data-w]'), function (e) { e.style.width = e.getAttribute('data-w') + '%'; }); }
  function prog() {
    var tot = S.list.length, a, b, la, lb, lc;
    if (S.mode === 'quiz') {
      a = S.list.filter(function (x) { return x.first === true; }).length; b = S.list.filter(function (x) { return x.first === false; }).length;
      la = '맞힘 ' + a; lb = '오답 ' + b; lc = '남은 문제 ' + S.queue.length;
    } else {
      a = S.list.filter(function (x) { return x.done; }).length; b = S.list.filter(function (x) { return !x.done && x.wrong > 0; }).length;
      la = '외운 단어 ' + a; lb = '다시 볼 단어 ' + b; lc = '남은 카드 ' + S.queue.length;
    }
    return '<div class="dr-prog"><div class="dr-track"><i class="ok" data-w="' + (a / tot * 100) + '"></i><i class="re" data-w="' + (b / tot * 100) + '"></i></div>' +
      '<div class="dr-legend"><span><i class="ok"></i>' + la + '</span><span><i class="re"></i>' + lb + '</span><span>' + lc + '</span></div></div>';
  }
  function tag(it) {
    return it.wrong > 0 ? '<span class="dr-tag re">다시 보는 단어</span>' : '<span class="dr-tag">' + kday(it.c.d) + ' 지문</span>';
  }
  function counter() {
    var it = S.queue[0], done = S.mode === 'quiz' ? S.answered - (it && it.pick != null ? 1 : 0) : S.list.filter(function (x) { return x.done; }).length;
    return Math.min(done + 1, S.list.length) + ' / ' + S.list.length;
  }
  function render() {
    if (!S.queue.length) return result();
    var it = S.queue[0], c = it.c, h = bar(counter()) + prog();
    if (S.mode === 'quiz') {
      if (!it.opts) {
        var alts = shuffle((c.alts || []).filter(function (m) { return m !== c.m; })).slice(0, 3);
        it.opts = shuffle(alts.concat([c.m]));
      }
      h += '<div class="dr-fc fit"><div class="dr-q">문제 ' + (S.answered + (it.pick != null ? 0 : 1)) + '. 알맞은 뜻을 고르세요</div>' +
        '<div class="dr-qword" lang="' + c.l + '">' + esc(c.w) + '</div>' + (c.sh ? '<p class="dr-qsub" lang="' + c.l + '">' + c.sh + '</p>' : '') +
        '<div class="dr-opts">' + it.opts.map(function (m, i) {
          var cls = '', r = '';
          if (it.pick != null) { if (m === c.m) { cls = ' right'; r = '<span class="r">정답</span>'; } else if (i === it.pick) { cls = ' wrong'; r = '<span class="r">내 답</span>'; } }
          return '<button class="dr-opt' + cls + '" type="button" data-act="pick" data-i="' + i + '"' + (it.pick != null ? ' disabled' : '') + '><span class="k">' + (i + 1) + '</span>' + esc(m) + r + '</button>';
        }).join('') + '</div>';
      if (it.pick != null) {
        var ok = it.opts[it.pick] === c.m;
        h += '<div class="dr-verdict' + (ok ? ' ok' : '') + '">' + (ok ? '맞았어요' : '틀렸어요. 오답 노트에 담았어요') + '</div>';
        if (c.ek) h += '<div class="dr-ex"><div class="lb">해석</div><p class="ko flat">' + esc(c.ek) + '</p></div>';
      }
      h += '</div>';
      if (it.pick != null) h += '<div class="dr-acts"><button class="dr-btn" type="button" data-act="next">' + (S.queue.length > 1 ? '다음 문제' : '결과 보기') + '</button></div>';
    } else if (!S.flip) {
      // 카드 아무 곳이나 누르면 뒤집힌다. 듣기 단추는 data-act="say"가 먼저 잡혀 뒤집히지 않는다.
      h += '<div class="dr-stage"><div class="dr-fc tap" data-act="flip" role="button" tabindex="0" aria-label="카드를 눌러 뜻 보기">' + tag(it) + '<div class="dr-mid"><div class="dr-word" lang="' + c.l + '">' + esc(c.w) + '</div>' +
        (c.r ? '<div class="dr-pron" lang="' + c.l + '">' + esc(c.r) + '</div>' : '') +
        '<button class="dr-listen" type="button" data-act="say">' + ICON_SPK + ' <span>듣기</span></button></div>' +
        '<p class="dr-taphint">' + ICON_TAP + ' 카드를 누르면 뜻이 나와요</p></div></div>';
    } else {
      var yes = it.wrong === 0 ? '바로 통과' : it.streak > 0 ? '한 번 더 맞혀서 통과' : '2번 연속이면 통과', nx = S.queue[1];
      h += '<div class="dr-stage">' + (nx ? '<div class="dr-fc under" aria-hidden="true">' + tag(nx) + '<div class="dr-mid"><div class="dr-word" lang="' + nx.c.l + '">' + esc(nx.c.w) + '</div></div></div>' : '') +
        '<div class="dr-fc swipe" tabindex="0" aria-label="오른쪽으로 밀면 알았어요, 왼쪽으로 밀면 몰랐어요"><span class="dr-stamp yes" aria-hidden="true">알았어요</span><span class="dr-stamp no" aria-hidden="true">몰랐어요</span>' +
        tag(it) + '<div class="dr-mid"><div class="dr-word sm" lang="' + c.l + '">' + esc(c.w) + '</div>' +
        (c.r ? '<div class="dr-pron" lang="' + c.l + '">' + esc(c.r) + '</div>' : '') + '<div class="dr-mean">' + esc(c.m) + '</div>' +
        (c.ex ? '<div class="dr-ex"><div class="lb">지문 속 문장</div><p class="en" lang="' + c.l + '">' + c.ex + '</p>' + (c.ek ? '<p class="ko">' + esc(c.ek) + '</p>' : '') + '</div>' : '') +
        '</div></div></div><div class="dr-swipehint" aria-hidden="true"><span class="l">← 몰랐어요</span><span class="c">옆으로 밀어서 넘겨요</span><span class="r">알았어요 →</span></div>' +
        '<div class="dr-acts"><div class="dr-judge sm"><button class="dr-no" type="button" data-act="no">몰랐어요<small>조금 뒤 다시 나와요</small></button>' +
        '<button class="dr-yes" type="button" data-act="yes">알았어요<small>' + yes + '</small></button></div></div>';
    }
    root.innerHTML = '<div class="dr-in">' + h + '</div>';
    widths();
    root.scrollTop = 0;
    var f = root.querySelector('[data-act=flip],[data-act=next],.dr-judge .dr-yes,.dr-opt'); if (f) f.focus({ preventScroll: true });
    // 앞면이 나오자마자 단어를 읽어 준다. 시작, 판정 같은 누름에서 바로 불리므로 브라우저 자동 재생 제한에 걸리지 않는다.
    if (S.mode === 'card' && !S.flip) say(c);
  }
  function later(it) { S.queue.splice(Math.min(3, S.queue.length), 0, it); }

  // iOS는 처음 누름에서 재생한 Audio 요소만 이후 자동 재생을 허락하므로 하나를 계속 쓴다.
  var player = null, sayN = 0;
  function say(c) {
    var n = ++sayN, btn = root && root.querySelector('.dr-listen');
    function on(v) {
      if (n !== sayN || !btn) return;
      btn.classList.toggle('on', v); btn.querySelector('span').textContent = v ? '읽어 주는 중' : '듣기';
    }
    function speak() {
      if (n !== sayN || !('speechSynthesis' in window)) return on(false);
      speechSynthesis.cancel(); var u = new SpeechSynthesisUtterance(c.w); u.lang = SPEECH[c.l] || 'en-US'; u.rate = 0.9;
      u.onend = u.onerror = function () { on(false); }; on(true); speechSynthesis.speak(u);
    }
    if ('speechSynthesis' in window) speechSynthesis.cancel();
    if (player) player.pause();
    if (!c.au) return speak();
    if (!player) player = new Audio();
    player.onended = function () { on(false); };
    player.src = c.au; on(true);
    var pr = player.play(); if (pr && pr.catch) pr.catch(speak);
  }
  function hush() { sayN++; if (player) player.pause(); if ('speechSynthesis' in window) speechSynthesis.cancel(); }
  function flip() { S.flip = true; S.shown++; render(); }

  // 판정: 1은 오른쪽(알았어요), -1은 왼쪽(몰랐어요). 보던 카드를 복제해 날려 보내고 다음 카드는 바로 그린다.
  function judge(act, dir) {
    var it = S.queue[0], fc = root.querySelector('.dr-fc.swipe'), ghost = null;
    if (fc) {
      ghost = fc.cloneNode(true); ghost.classList.remove('swipe', 'back'); ghost.classList.add('fly'); ghost.removeAttribute('tabindex');
      ghost.style.transform = fc.style.transform || ''; stamp(ghost, dir * 80);
    }
    S.queue.shift(); S.flip = false;
    if (act === 'no') { if (it.first === null) it.first = false; it.wrong++; it.streak = 0; later(it); }
    else if (it.first === null) { it.first = true; it.done = true; }
    else if (it.streak < 1) { it.streak++; later(it); }
    else it.done = true;
    render();
    var host = root.querySelector('.dr-fc.tap');
    if (!ghost || !host || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    host.parentNode.insertBefore(ghost, host);
    ghost.getBoundingClientRect();
    ghost.style.transform = 'translateX(' + (dir * 130) + '%) rotate(' + (dir * 20) + 'deg)'; ghost.style.opacity = '0';
    setTimeout(function () { if (ghost.parentNode) ghost.parentNode.removeChild(ghost); }, 300);
  }
  function stamp(fc, dx) {
    var a = Math.min(Math.abs(dx) / 80, 1);
    fc.querySelector('.dr-stamp.yes').style.opacity = dx > 0 ? a : 0;
    fc.querySelector('.dr-stamp.no').style.opacity = dx < 0 ? a : 0;
  }

  // 스와이프: 뒷면 카드를 손가락(마우스)으로 끌어 옆으로 넘긴다. 세로 스크롤은 브라우저에 맡긴다(touch-action: pan-y).
  var drag = null;
  function onDown(e) {
    var fc = e.target.closest('.dr-fc.swipe');
    if (!fc || !S || !S.flip || e.button > 0 || e.target.closest('button')) return;
    drag = { fc: fc, id: e.pointerId, x: e.clientX, y: e.clientY, dx: 0, on: false };
    fc.classList.remove('back');
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
    window.addEventListener('pointercancel', onUp);
  }
  function onMove(e) {
    if (!drag || e.pointerId !== drag.id) return;
    var dx = e.clientX - drag.x, dy = e.clientY - drag.y;
    if (!drag.on) { if (Math.abs(dx) < 8 || Math.abs(dx) < Math.abs(dy)) return; drag.on = true; }
    drag.dx = dx;
    drag.fc.style.transform = 'translateX(' + dx + 'px) rotate(' + (dx / 20) + 'deg)';
    stamp(drag.fc, dx);
  }
  function onUp(e) {
    if (!drag || e.pointerId !== drag.id) return;
    var d = drag; drag = null;
    window.removeEventListener('pointermove', onMove);
    window.removeEventListener('pointerup', onUp);
    window.removeEventListener('pointercancel', onUp);
    var limit = Math.min(100, d.fc.offsetWidth * 0.25);
    if (e.type === 'pointerup' && Math.abs(d.dx) >= limit) return judge(d.dx > 0 ? 'yes' : 'no', d.dx > 0 ? 1 : -1);
    d.fc.classList.add('back'); d.fc.style.transform = ''; stamp(d.fc, 0);
  }

  function onClick(e) {
    var b = e.target.closest('[data-act]'); if (!b || !S) return;
    var act = b.getAttribute('data-act'), it = S.queue[0];
    if (act === 'close') return close();
    if (act === 'say') return say(it.c);
    if (act === 'flip') return flip();
    if (act === 'yes' || act === 'no') return judge(act, act === 'yes' ? 1 : -1);
    if (act === 'pick') {
      if (it.pick != null) return;
      it.pick = +b.getAttribute('data-i'); var ok = it.opts[it.pick] === it.c.m; if (it.first === null) it.first = ok; if (!ok) it.wrong++;
      S.answered++; S.shown++; return render();
    }
    if (act === 'next') {
      // 카드와 같은 규칙: 틀리면 같은 회차 뒤로, 한 번에 못 맞힌 단어는 연속 2번 맞혀야 빠진다.
      var right = it.opts[it.pick] === it.c.m; S.queue.shift(); it.pick = null;
      if (!right) { it.streak = 0; later(it); }
      else if (it.wrong === 0 || it.streak >= 1) it.done = true;
      else { it.streak++; later(it); }
      return render();
    }
    if (act === 'retry') return start(S.list.filter(function (x) { return x.wrong > 0; }).map(function (x) { return x.c; }), S.mode, 'retry');
  }

  function start(list, mode, kind) {
    S = { mode: mode, kind: kind, flip: false, shown: 0, answered: 0,
          title: kind === 'review' ? '단어 복습' : mode === 'quiz' ? '문제 풀기' : '오늘 단어 외우기' };
    S.list = list.map(function (c) { return { c: c, wrong: 0, streak: 0, first: null, done: false }; });
    S.queue = S.list.slice();
    if (kind !== 'today') shuffle(S.queue);
    open(); render();
  }

  // 회차를 마치면 단어를 담고 복습일을 정한다. 처음 담는 단어와 틀린 단어는 1일 뒤, 복습에서 한 번에 맞히면 다음 간격으로.
  function commit() {
    var db = load(), t = today();
    S.list.forEach(function (it) {
      var c = it.c, rec = db.items[c.k];
      if (!rec) { rec = {}; rec.s = 0; rec.due = add(t, 1); }
      else if (it.wrong > 0) { rec.s = 0; rec.due = add(t, 1); }
      else if (rec.due && rec.due <= t) { rec.s = (rec.s || 0) + 1; rec.due = rec.s >= INT.length ? null : add(t, INT[rec.s]); }
      ['k', 'l', 'd', 'w', 'r', 'm', 'ex', 'sh', 'ek', 'au', 'alts'].forEach(function (f) { if (c[f] != null) rec[f] = c[f]; });
      rec.x = it.wrong;
      db.items[c.k] = rec;
    });
    store(db);
  }

  function result() {
    var tot = S.list.length, first = S.list.filter(function (x) { return x.first === true; }).length;
    var wrongs = S.list.filter(function (x) { return x.wrong > 0; }).sort(function (a, b) { return b.wrong - a.wrong; });
    if (S.kind !== 'retry') {
      commit();
      ga('word_drill_done', { lang: LANG, day: S.kind === 'review' ? 'review' : DAY, mode: S.mode, first_try: first, total: tot });
    }
    var t = today(), d1 = add(t, 1), d2 = add(d1, 3), d3 = add(d2, 7), d4 = add(d3, 14), gap = function (d) { return Math.round((parse(d) - parse(t)) / 864e5) + '일 뒤'; };
    var h = '<div class="dr-bar"><button class="dr-x" type="button" data-act="close" aria-label="닫기">' + ICON_X + '</button><span class="t">' + S.title + '</span><span class="n">완료</span></div>' +
      '<section class="card"><div class="step">' + (S.kind === 'retry' ? '오답 다시 결과' : S.kind === 'review' ? '복습 결과' : '오늘 결과') + '</div>' +
      '<div class="dr-score"><b>' + first + '</b><span>/ ' + tot + '개 한 번에 맞혔어요</span></div>' +
      '<div class="dr-stats"><div class="dr-stat"><b>' + tot + '</b><span>외운 단어</span></div><div class="dr-stat"><b>' + S.shown + '</b><span>' + (S.mode === 'quiz' ? '푼 문제' : '넘긴 카드') + '</span></div>' +
      '<div class="dr-stat"><b>' + wrongs.length + '</b><span>틀린 단어</span></div></div></section>' +
      '<section class="card"><h2 class="dr-h12">오답 노트</h2>' +
      (wrongs.length ? '<div>' + wrongs.map(function (x) {
        return '<div class="dr-wl"><b lang="' + x.c.l + '">' + esc(x.c.w) + '<em>' + x.wrong + '번 틀림</em></b><span>' + esc(x.c.m) + '</span></div>';
      }).join('') + '</div><div class="dr-gap"><button class="dr-btn ghost" type="button" data-act="retry">오답 ' + wrongs.length + '개만 다시</button></div>'
        : '<p class="dr-none">틀린 단어 없이 모두 맞혔어요.</p>') + '</section>' +
      '<section class="card"><h2 class="dr-h6">다음 복습</h2>' +
      '<p class="desc dr-next">잊을 때쯤 다시 보여 드려요. 틀린 단어는 처음부터 다시 세요.</p>' +
      '<div class="dr-sched"><div class="dr-dot next"><b>내일</b><span>' + md(d1) + '</span></div><div class="dr-dot"><b>' + md(d2) + '</b><span>' + gap(d2) + '</span></div>' +
      '<div class="dr-dot"><b>' + md(d3) + '</b><span>' + gap(d3) + '</span></div><div class="dr-dot"><b>' + md(d4) + '</b><span>' + gap(d4) + '</span></div></div>' +
      '<div class="dr-gap"><button class="dr-btn" type="button" data-act="close">완료</button></div></section>';
    root.innerHTML = '<div class="dr-in">' + h + '</div>';
    widths();
    root.scrollTop = 0;
  }

  // 진입 카드
  var card = document.getElementById('drill');
  if (card && CARDS.length) {
    var mode = 'card', modes = card.querySelectorAll('.dr-mode');
    [].forEach.call(modes, function (m) {
      m.addEventListener('click', function () {
        mode = m.getAttribute('data-mode');
        [].forEach.call(modes, function (x) { x.setAttribute('aria-pressed', String(x === m)); });
      });
    });
    document.getElementById('dr-start').addEventListener('click', function () {
      ga('word_drill_start', { lang: LANG, day: DAY, mode: mode });
      start(CARDS, mode, 'today');
    });
  }
  var go = document.getElementById('dr-due-go');
  if (go) go.addEventListener('click', function () {
    var due = dueCards(); if (!due.length) return showDue();
    ga('word_review_start', { lang: LANG, due: due.length });
    start(due, 'card', 'review');
  });
  showDue();
})();
