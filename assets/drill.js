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
      root.addEventListener('submit', function (e) { e.preventDefault(); if (S) check(); });
      root.addEventListener('pointerdown', onDown);
      root.addEventListener('touchstart', onTouchStart, { passive: true });
      root.addEventListener('touchmove', onTouchMove, { passive: false });
      root.addEventListener('touchend', onTouchEnd);
      root.addEventListener('touchcancel', onTouchEnd);
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
    else if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') { e.preventDefault(); judge(e.key === 'ArrowRight' ? 'yes' : 'no', e.key === 'ArrowRight' ? 1 : -1); }
  });

  function bar(n) {
    return '<div class="dr-bar"><button class="dr-x" type="button" data-act="close" aria-label="닫기">' + ICON_X + '</button><span class="t">' + S.title + '</span><span class="n">' + n + '</span></div>';
  }
  // 진행 막대 폭은 마크업 style 속성 대신 CSSOM으로 넣는다(CSP style-src에 걸리지 않게).
  function widths() { [].forEach.call(root.querySelectorAll('[data-w]'), function (e) { e.style.width = e.getAttribute('data-w') + '%'; }); }
  function prog() {
    var tot = S.list.length, a, b, la, lb, lc;
    if (S.mode !== 'card') {
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
    var it = S.queue[0], done = S.mode !== 'card' ? S.answered - (it && it.pick != null ? 1 : 0) : S.list.filter(function (x) { return x.done; }).length;
    return Math.min(done + 1, S.list.length) + ' / ' + S.list.length;
  }
  function render() {
    if (!S.queue.length) return result();
    var it = S.queue[0], c = it.c, h = bar(counter()) + prog();
    if (S.mode !== 'card') {
      var k = kindOf(it), done = it.pick != null, num = '문제 ' + (S.answered + (done ? 0 : 1)) + '. ';
      var nextBtn = '<button class="dr-btn" type="button" data-act="next">' + (S.queue.length > 1 ? '다음 문제' : '결과 보기') + '</button>';
      if (k === 'write') {
        h += '<div class="dr-fc fit"><div class="dr-q">' + num + '뜻을 보고 단어를 쓰세요</div><div class="dr-qmean">' + esc(c.m) + '</div><p class="dr-qhint">' + hint(c) + '</p>' +
          '<form class="dr-write" autocomplete="off"><input class="dr-field' + (done ? (it.ok ? ' right' : ' wrong') : '') + '" type="text" lang="' + c.l +
          '" autocapitalize="off" autocorrect="off" spellcheck="false" enterkeyhint="done" aria-label="단어 입력" placeholder="여기에 쓰세요"' +
          (done ? ' value="' + esc(it.pick) + '" disabled' : '') + '></form>';
        if (!done) h += '<button class="dr-skip" type="button" data-act="giveup">모르겠어요</button>';
        else h += verdict(it, k) + '<div class="dr-answer"><div><span class="lb">정답</span><b lang="' + c.l + '">' + esc(c.w) + '</b>' + (c.r ? '<span class="rd" lang="' + c.l + '">' + esc(c.r) + '</span>' : '') +
          '</div><button class="dr-listen" type="button" data-act="say">' + ICON_SPK + ' <span>듣기</span></button></div>' +
          (c.ex ? '<div class="dr-ex dr-gap10"><div class="lb">지문 속 문장</div><p class="en" lang="' + c.l + '">' + c.ex + '</p></div>' : '');
        h += '</div><div class="dr-acts">' + (done ? nextBtn : '<button class="dr-btn" type="button" data-act="check">확인</button>') + '</div>';
      } else {
        var cz = k === 'cloze', ans = cz ? c.ca : c.m;
        if (!it.opts || it.qk !== k) {
          var pool = cz ? CARDS.concat(S.list.map(function (x) { return x.c; })).map(function (x) { return x.ca || x.w; }) : (c.alts || []);
          pool = pool.filter(function (m, i, a) { return m !== ans && a.indexOf(m) === i; });
          it.opts = shuffle(shuffle(pool).slice(0, 3).concat([ans])); it.qk = k;
        }
        h += '<div class="dr-fc fit"><div class="dr-q">' + num + (cz ? '빈칸에 알맞은 단어를 고르세요' : '알맞은 뜻을 고르세요') + '</div>';
        if (cz) h += '<p class="dr-cloze" lang="' + c.l + '">' + c.cz.replace('<span class="dr-blank"></span>', '<span class="dr-blank' + (done ? ' right">' + esc(ans) : '">') + '</span>') + '</p>' +
          (c.ek ? '<p class="dr-cko">' + esc(c.ek) + '</p>' : '');
        else h += '<div class="dr-qword" lang="' + c.l + '">' + esc(c.w) + '</div>' + (c.sh ? '<p class="dr-qsub" lang="' + c.l + '">' + c.sh + '</p>' : '');
        h += '<div class="dr-opts">' + it.opts.map(function (m, i) {
          var cls = '', r = '';
          if (done) { if (m === ans) { cls = ' right'; r = '<span class="r">정답</span>'; } else if (i === it.pick) { cls = ' wrong'; r = '<span class="r">내 답</span>'; } }
          return '<button class="dr-opt' + cls + '" type="button" data-act="pick" data-i="' + i + '"' + (cz ? ' lang="' + c.l + '"' : '') + (done ? ' disabled' : '') + '><span class="k">' + (i + 1) + '</span>' + esc(m) + r + '</button>';
        }).join('') + '</div>';
        if (done) {
          h += verdict(it, k);
          if (!cz && c.ek) h += '<div class="dr-ex"><div class="lb">해석</div><p class="ko flat">' + esc(c.ek) + '</p></div>';
        }
        h += '</div>';
        if (done) h += '<div class="dr-acts">' + nextBtn + '</div>';
      }
    } else if (!S.flip) {
      // 카드 아무 곳이나 누르면 뒤집힌다. 듣기 단추는 data-act="say"가 먼저 잡혀 뒤집히지 않는다.
      h += '<div class="dr-stage">' + under() + '<div class="dr-fc tap swipe" data-act="flip" role="button" tabindex="0" aria-label="카드를 눌러 뜻 보기, 옆으로 밀어 판정">' + STAMPS + tag(it) + '<div class="dr-mid"><div class="dr-word" lang="' + c.l + '">' + esc(c.w) + '</div>' +
        (c.r ? '<div class="dr-pron" lang="' + c.l + '">' + esc(c.r) + '</div>' : '') +
        '<button class="dr-listen" type="button" data-act="say">' + ICON_SPK + ' <span>듣기</span></button></div>' +
        '<p class="dr-taphint">' + ICON_TAP + ' 카드를 누르면 뜻이 나와요</p></div></div>' +
        '<div class="dr-swipehint" aria-hidden="true"><span class="l">← 몰랐어요</span><span class="c">뜻을 안 봐도 밀 수 있어요</span><span class="r">알았어요 →</span></div>';
    } else {
      var yes = it.wrong === 0 ? '바로 통과' : it.streak > 0 ? '한 번 더 맞혀서 통과' : '2번 연속이면 통과';
      h += '<div class="dr-stage">' + under() + '<div class="dr-fc swipe" tabindex="0" aria-label="오른쪽으로 밀면 알았어요, 왼쪽으로 밀면 몰랐어요">' + STAMPS + tag(it) + '<div class="dr-mid"><div class="dr-word sm" lang="' + c.l + '">' + esc(c.w) + '</div>' +
        (c.r ? '<div class="dr-pron" lang="' + c.l + '">' + esc(c.r) + '</div>' : '') + '<div class="dr-mean">' + esc(c.m) + '</div>' +
        (c.ex ? '<div class="dr-ex"><div class="lb">지문 속 문장</div><p class="en" lang="' + c.l + '">' + c.ex + '</p>' + (c.ek ? '<p class="ko">' + esc(c.ek) + '</p>' : '') + '</div>' : '') +
        '</div></div></div><div class="dr-swipehint" aria-hidden="true"><span class="l">← 몰랐어요</span><span class="c">옆으로 밀어서 넘겨요</span><span class="r">알았어요 →</span></div>' +
        '<div class="dr-acts"><div class="dr-judge sm"><button class="dr-no" type="button" data-act="no">몰랐어요<small>조금 뒤 다시 나와요</small></button>' +
        '<button class="dr-yes" type="button" data-act="yes">알았어요<small>' + yes + '</small></button></div></div>';
    }
    root.innerHTML = '<div class="dr-in">' + h + '</div>';
    widths();
    root.scrollTop = 0;
    var f = root.querySelector('.dr-field:not([disabled]),[data-act=flip],[data-act=next],.dr-judge .dr-yes,.dr-opt'); if (f) f.focus({ preventScroll: true });
    // 앞면이 나오자마자 단어를 읽어 준다. 시작, 판정 같은 누름에서 바로 불리므로 브라우저 자동 재생 제한에 걸리지 않는다.
    if (S.mode === 'card' && !S.flip) say(c);
  }
  var STAMPS = '<span class="dr-stamp sy" aria-hidden="true">알았어요</span><span class="dr-stamp sn" aria-hidden="true">몰랐어요</span>';
  function under() {
    var nx = S.queue[1];
    return nx ? '<div class="dr-fc under" aria-hidden="true">' + tag(nx) + '<div class="dr-mid"><div class="dr-word" lang="' + nx.c.l + '">' + esc(nx.c.w) + '</div></div></div>' : '';
  }
  // 문제 종류: 빈칸 자료가 없는 단어는 뜻 고르기로 묻는다.
  function kindOf(it) { return S.mode === 'write' ? 'write' : S.mode === 'cloze' && it.c.cz ? 'cloze' : 'mean'; }
  function verdict(it, k) {
    var c = it.c, t = !it.ok ? '틀렸어요. 오답 노트에 담았어요' : it.near ? '맞았어요. 철자를 한 번 더 확인해 보세요' : k === 'cloze' ? '맞았어요. ' + c.w + ': ' + c.m : '맞았어요';
    return '<div class="dr-verdict' + (it.ok ? ' ok' : '') + '">' + esc(t) + '</div>';
  }
  function hint(c) {
    var s = c.l === 'ja' ? (c.r || c.w) : c.w.replace(/\s*\([^)]*\)/g, ''), n = s.replace(/\s/g, '').length;
    return (c.l === 'ja' ? '읽기 ' : '') + '“' + esc(s.charAt(0)) + '”로 시작하는 ' + n + '글자' + (c.l !== 'ja' && /\s/.test(s.trim()) ? ', 낱말 ' + s.trim().split(/\s+/).length + '개' : '');
  }
  // 쓰기 채점: 대소문자, 띄어쓰기, 문장부호, 괄호 속 말은 보지 않는다. 독일어는 ae/oe/ue/ss, 일본어는 가타카나와 읽기도 정답.
  function norm(s, l, raw) {
    s = String(s).normalize('NFKC').toLowerCase().replace(/\([^)]*\)/g, ' ').replace(/[.,!?'"’`…~〜]/g, '').replace(/\s+/g, ' ').trim();
    if (l === 'de' && !raw) s = s.replace(/ä/g, 'ae').replace(/ö/g, 'oe').replace(/ü/g, 'ue').replace(/ß/g, 'ss');
    if (l === 'en') s = s.replace(/^to /, '');
    if (l === 'ja') s = s.replace(/[\u30a1-\u30f6]/g, function (ch) { return String.fromCharCode(ch.charCodeAt(0) - 0x60); }).replace(/\s/g, '');
    return s;
  }
  function dist(a, b) {
    var d = [], i, j;
    for (i = 0; i <= a.length; i++) d[i] = [i];
    for (j = 1; j <= b.length; j++) d[0][j] = j;
    for (i = 1; i <= a.length; i++) for (j = 1; j <= b.length; j++)
      d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
    return d[a.length][b.length];
  }
  function grade(c, v) {
    // linked (to) 는 linked, linked to 둘 다 정답
    var forms = [c.w, c.w.replace(/[()]/g, '')].concat(c.r ? [c.r] : []);
    var t = norm(v, c.l), keys = forms.map(function (x) { return norm(x, c.l); });
    if (keys.indexOf(t) >= 0) return { ok: true };
    // 한 글자 오타는 봐주되, 움라우트를 빠뜨린 것(Blatter ↔ Blätter)은 틀린 것으로 본다
    var rt = norm(v, c.l, true), rk = norm(c.w, c.l, true);
    var fold = function (x) { return x.replace(/ä/g, 'a').replace(/ö/g, 'o').replace(/ü/g, 'u').replace(/ß/g, 's'); };
    var near = c.l !== 'ja' && rk.length >= 6 && dist(rt, rk) <= 1 && !(c.l === 'de' && fold(rt) === fold(rk));
    return { ok: near, near: near };
  }
  function answer(it, v, ok, near) {
    it.pick = v; it.ok = ok; it.near = !!near;
    if (it.first === null) it.first = ok;
    if (!ok) it.wrong++;
    S.answered++; S.shown++; render();
  }
  function check() {
    var it = S.queue[0], f = root.querySelector('.dr-field');
    if (!f || f.disabled) return;
    if (!f.value.trim()) return f.focus();
    var g = grade(it.c, f.value); answer(it, f.value.trim(), g.ok, g.near);
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
    player.onerror = function () { if (n === sayN) speak(); };
    player.src = c.au; on(true);
    var pr = player.play(); if (pr && pr.catch) pr.catch(speak);
  }
  function hush() { sayN++; if (player) player.pause(); if ('speechSynthesis' in window) speechSynthesis.cancel(); }
  function flip() { S.flip = true; render(); }

  // 판정: 1은 오른쪽(알았어요), -1은 왼쪽(몰랐어요). 보던 카드를 복제해 날려 보내고 다음 카드는 바로 그린다.
  function judge(act, dir) {
    var it = S.queue[0], fc = root.querySelector('.dr-fc.swipe'), ghost = null;
    if (fc) {
      ghost = fc.cloneNode(true); ghost.classList.remove('swipe', 'back', 'tap'); ghost.removeAttribute('data-act'); ghost.classList.add('fly'); ghost.removeAttribute('tabindex');
      ghost.style.transform = fc.style.transform || ''; stamp(ghost, dir * 80);
    }
    S.queue.shift(); S.flip = false; S.shown++;
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
    fc.querySelector('.dr-stamp.sy').style.opacity = dx > 0 ? a : 0;
    fc.querySelector('.dr-stamp.sn').style.opacity = dx < 0 ? a : 0;
  }

  // 스와이프: 카드(앞면, 뒷면)를 옆으로 밀어 판정한다. 휴대폰은 touch 이벤트로 받아, 가로로 미는 게 확실해지면
  // touchmove 기본 동작을 막아 페이지 스크롤이 끌기를 빼앗지 않게 한다(pointer 이벤트는 스크롤이 시작되면 pointercancel로 끊긴다).
  // 세로로 움직이면 끌기를 포기하고 스크롤에 맡긴다. 마우스는 pointer 이벤트로 받는다.
  var drag = null, noClick = 0;
  function begin(e, x, y, kind) {
    var fc = e.target.closest('.dr-fc.swipe');
    if (!fc || !S || S.mode !== 'card' || e.target.closest('button')) return false;
    drag = { fc: fc, kind: kind, x: x, y: y, dx: 0, on: false, dead: false, lx: x, lt: Date.now(), v: 0 };
    fc.classList.remove('back');
    return true;
  }
  function move(x, y) {
    if (!drag || drag.dead) return false;
    var dx = x - drag.x, dy = y - drag.y;
    if (!drag.on) {
      if (Math.max(Math.abs(dx), Math.abs(dy)) < 6) return false;
      if (Math.abs(dx) <= Math.abs(dy)) { drag.dead = true; return false; }
      drag.on = true;
    }
    var t = Date.now();
    if (t > drag.lt) { drag.v = (x - drag.lx) / (t - drag.lt); drag.lx = x; drag.lt = t; }
    drag.dx = dx;
    drag.fc.style.transform = 'translateX(' + dx + 'px) rotate(' + (dx / 20) + 'deg)';
    stamp(drag.fc, dx);
    return true;
  }
  function end(ok) {
    var d = drag; drag = null;
    if (!d || !d.on) return;
    noClick = Date.now() + 100;  // 마우스로 끌고 놓으면 바로 따라오는 click 이 앞면을 뒤집지 않게
    var limit = Math.min(90, d.fc.offsetWidth * 0.22), fast = Math.abs(d.v) > 0.5 && Math.abs(d.dx) > 30 && (d.v > 0) === (d.dx > 0);
    if (ok && (Math.abs(d.dx) >= limit || fast)) return judge(d.dx > 0 ? 'yes' : 'no', d.dx > 0 ? 1 : -1);
    d.fc.classList.add('back'); d.fc.style.transform = ''; stamp(d.fc, 0);
  }
  function onTouchStart(e) {
    if (drag) return end(false);
    if (e.touches.length !== 1) return;
    begin(e, e.touches[0].clientX, e.touches[0].clientY, 'touch');
  }
  function onTouchMove(e) {
    if (!drag || drag.kind !== 'touch') return;
    if (e.touches.length !== 1) return end(false);
    if (move(e.touches[0].clientX, e.touches[0].clientY) && e.cancelable) e.preventDefault();
  }
  function onTouchEnd(e) {
    if (drag && drag.kind === 'touch') end(e.type === 'touchend');
  }
  function onDown(e) {
    if (e.pointerType !== 'mouse' || e.button > 0 || drag) return;
    if (!begin(e, e.clientX, e.clientY, 'mouse')) return;
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
    window.addEventListener('pointercancel', onUp);
  }
  function onMove(e) { if (drag && drag.kind === 'mouse') move(e.clientX, e.clientY); }
  function onUp(e) {
    window.removeEventListener('pointermove', onMove);
    window.removeEventListener('pointerup', onUp);
    window.removeEventListener('pointercancel', onUp);
    if (drag && drag.kind === 'mouse') end(e.type === 'pointerup');
  }

  function onClick(e) {
    var b = e.target.closest('[data-act]'); if (!b || !S) return;
    if (Date.now() < noClick && b.getAttribute('data-act') === 'flip') return;
    var act = b.getAttribute('data-act'), it = S.queue[0];
    if (act === 'close') return close();
    if (act === 'say') return say(it.c);
    if (act === 'flip') return flip();
    if (act === 'yes' || act === 'no') return judge(act, act === 'yes' ? 1 : -1);
    if (act === 'pick') {
      if (it.pick != null) return;
      var i = +b.getAttribute('data-i');
      return answer(it, i, it.opts[i] === (kindOf(it) === 'cloze' ? it.c.ca : it.c.m));
    }
    if (act === 'check') return check();
    if (act === 'giveup') { if (it.pick == null) answer(it, '', false); return; }
    if (act === 'next') {
      // 카드와 같은 규칙: 틀리면 같은 회차 뒤로, 한 번에 못 맞힌 단어는 연속 2번 맞혀야 빠진다.
      var right = it.ok; S.queue.shift(); it.pick = null; it.ok = null;
      if (!right) { it.streak = 0; later(it); }
      else if (it.wrong === 0 || it.streak >= 1) it.done = true;
      else { it.streak++; later(it); }
      return render();
    }
    if (act === 'retry') return start(S.list.filter(function (x) { return x.wrong > 0; }).map(function (x) { return x.c; }), S.mode, 'retry');
  }

  function start(list, mode, kind) {
    S = { mode: mode, kind: kind, flip: false, shown: 0, answered: 0,
          title: kind === 'review' ? '단어 복습' : mode !== 'card' ? '문제 풀기' : '오늘 단어 외우기' };
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
      '<div class="dr-stats"><div class="dr-stat"><b>' + tot + '</b><span>외운 단어</span></div><div class="dr-stat"><b>' + S.shown + '</b><span>' + (S.mode !== 'card' ? '푼 문제' : '넘긴 카드') + '</span></div>' +
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
    // 고른 방식(카드/문제, 문제 종류)은 이 기기에 기억해 다음에도 그대로 보여 준다.
    var PREF = 'drill:pref', pref = {};
    try { pref = JSON.parse(localStorage.getItem(PREF)) || {}; } catch (e) {}
    var mode = pref.m === 'quiz' ? 'quiz' : 'card', qt = ['quiz', 'write', 'cloze'].indexOf(pref.q) >= 0 ? pref.q : 'quiz';
    var modes = card.querySelectorAll('.dr-mode'), qts = card.querySelectorAll('.dr-qt'), qbox = document.getElementById('dr-qts'), go1 = document.getElementById('dr-start');
    function paint() {
      [].forEach.call(modes, function (x) { x.setAttribute('aria-pressed', String(x.getAttribute('data-mode') === mode)); });
      [].forEach.call(qts, function (x) { x.setAttribute('aria-pressed', String(x.getAttribute('data-qt') === qt)); });
      if (qbox) qbox.hidden = mode !== 'quiz';
      go1.textContent = CARDS.length + (mode === 'card' ? '개 외우기 시작' : '문제 풀기 시작');
    }
    [].forEach.call(modes, function (m) { m.addEventListener('click', function () { mode = m.getAttribute('data-mode'); paint(); }); });
    [].forEach.call(qts, function (m) { m.addEventListener('click', function () { qt = m.getAttribute('data-qt'); paint(); }); });
    paint();
    go1.addEventListener('click', function () {
      var m = mode === 'card' ? 'card' : qt;
      try { localStorage.setItem(PREF, JSON.stringify({ m: mode, q: qt })); } catch (e) {}
      ga('word_drill_start', { lang: LANG, day: DAY, mode: m });
      start(CARDS, m, 'today');
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
