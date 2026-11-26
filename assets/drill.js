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
  // 로그인(assets/auth.js). 설정 전(ready=false)에는 잠금 없이 예전처럼 동작한다.
  var AUTH = window.dkhAuth || { ready: false, hasSession: function () { return false; } };
  function locked() { return AUTH.ready && !AUTH.hasSession(); }
  var KICON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 3C6.48 3 2 6.5 2 10.8c0 2.78 1.87 5.22 4.68 6.6l-.95 3.48c-.08.3.26.55.52.38l4.15-2.74c.52.06 1.06.1 1.6.1 5.52 0 10-3.5 10-7.82S17.52 3 12 3z"/></svg>';
  var GICON = '<svg viewBox="0 0 48 48" aria-hidden="true"><path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/><path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/><path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/><path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/></svg>';
  function joinHref(from) { return AUTH.joinUrl ? AUTH.joinUrl(location.pathname + '#drill', from) : '/join/'; }
  // 로그인 화면으로 갈 때: 돌아오면 문제 풀기가 골라져 있게 하고, 몇 명이 눌렀는지 센다
  function toJoin(from) {
    try { var p = JSON.parse(localStorage.getItem('drill:pref')) || {}; p.m = 'quiz'; localStorage.setItem('drill:pref', JSON.stringify(p)); } catch (e) {}
    ga('word_gate_click', { lang: LANG, day: DAY, from: from });
    if (AUTH.logEvent) AUTH.logEvent('gate_join_click', LANG);
  }
  var gateSeen = false;
  function gateShown(from) {
    if (gateSeen) return; gateSeen = true;
    ga('word_gate_shown', { lang: LANG, day: DAY, from: from });
    if (AUTH.logEvent) AUTH.logEvent('gate_shown', LANG);
  }
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
      var it0 = S.queue[0]; la = '맞힘 ' + a; lb = '오답 ' + b; lc = '남은 문제 ' + (S.queue.length - (it0 && it0.pick != null ? 1 : 0));
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
      if (k === 'write' || k === 'cloze') {
        // 빈칸 채우기도 보기 없이 직접 쓴다. 쓰는 칸은 따로 두지 않고 예문 속 빈칸이 입력 칸이다(W22, W23). 정답은 예문에 쓰인 꼴(c.ca)이다.
        var cw = k === 'cloze', ansW = cw ? c.ca : (c.ar ? c.ar + ' ' : '') + c.w;
        var input = '<input class="dr-field' + (cw ? ' dr-inb' : '') + (done ? (it.ok ? ' right' : ' wrong') : '') + '" type="text" lang="' + c.l +
          '" autocapitalize="off" autocorrect="off" spellcheck="false" enterkeyhint="go" aria-label="' + (cw ? '빈칸에 들어갈 단어' : '단어 입력') + '"' + (cw ? ' size="' + blankSize(c) + '"' : ' placeholder="여기에 쓰세요"') +
          (done ? ' value="' + esc(it.pick) + '" disabled' : '') + '>';
        h += '<div class="dr-fc fit"><div class="dr-q">' + num + (cw ? '문장 속 빈칸에 바로 쓰세요' : '뜻을 보고 단어를 쓰세요') + '</div><form class="dr-write" autocomplete="off">';
        if (cw) h += '<p class="dr-cloze" lang="' + c.l + '">' + c.cz.replace('<span class="dr-blank"></span>', function () {
            return done ? (it.ok && !it.near ? '' : it.pick ? '<s class="dr-inw">' + esc(it.pick) + '</s>' : '') + '<span class="dr-blank right">' + esc(c.ca) + '</span>' : input;
          }) + '</p>' +
          (!done ? (c.ek ? '<p class="dr-cko">' + esc(c.ek) + '</p>' : '') + '<p class="dr-qhint">뜻: ' + esc(c.mh || c.m) + '<br>' + hint(c, true) + '</p>' : '');
        else h += '<div class="dr-qmean">' + esc(c.mh || c.m) + '</div><p class="dr-qhint">' + hint(c) + '</p>' + input;
        h += '</form>';
        if (!done) h += '<button class="dr-skip" type="button" data-act="giveup">모르겠어요</button>';
        else h += verdict(it, k) + '<div class="dr-answer"><div><span class="lb">정답</span><b lang="' + c.l + '">' + esc(ansW) + '</b>' + (c.r && !cw ? '<span class="rd" lang="' + c.l + '">' + esc(c.r) + '</span>' : '') +
          '</div><button class="dr-listen" type="button" data-act="say">' + ICON_SPK + ' <span>듣기</span></button></div>' +
          (cw ? '<div class="dr-ex dr-gap10"><div class="lb">해석</div><p class="en" lang="' + c.l + '">' + (c.ex || '') + '</p>' + (c.ek ? '<p class="ko">' + esc(c.ek) + ' ' + esc(c.w + ': ' + c.m) + '</p>' : '') + '</div>'
            : c.ex ? '<div class="dr-ex dr-gap10"><div class="lb">지문 속 문장</div><p class="en" lang="' + c.l + '">' + c.ex + '</p></div>' : '');
        h += '</div><div class="dr-acts">' + (done ? nextBtn : '<button class="dr-btn" type="button" data-act="check">확인</button>') + '</div>';
      } else {
        var ans = c.mh || c.m;
        if (!it.opts || it.qk !== k) {
          var pool = c.alts || [];
          pool = pool.filter(function (m, i, a) { return m !== ans && a.indexOf(m) === i; });
          it.opts = shuffle(shuffle(pool).slice(0, 3).concat([ans])); it.qk = k;
        }
        h += '<div class="dr-fc fit"><div class="dr-q">' + num + '알맞은 뜻을 고르세요</div>';
        h += '<div class="dr-qword" lang="' + c.l + '">' + esc(c.w) + '</div>' + (c.sh ? '<p class="dr-qsub" lang="' + c.l + '">' + c.sh + '</p>' : '');
        h += '<div class="dr-opts">' + it.opts.map(function (m, i) {
          var cls = '', r = '';
          if (done) { if (m === ans) { cls = ' right'; r = '<span class="r">정답</span>'; } else if (i === it.pick) { cls = ' wrong'; r = '<span class="r">내 답</span>'; } }
          return '<button class="dr-opt' + cls + '" type="button" data-act="pick" data-i="' + i + '"' + (done ? ' disabled' : '') + '><span class="k">' + (i + 1) + '</span>' + esc(m) + r + '</button>';
        }).join('') + '</div>';
        if (done) {
          h += verdict(it, k);
          if (c.ek) h += '<div class="dr-ex"><div class="lb">해석</div><p class="ko flat">' + esc(c.ek) + '</p></div>';
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
    else if (S.mode !== 'card' && it.pick == null) warm();
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
  // 빈칸 채우기 정답 꼴: 예문에 쓰인 형태(c.ca). 일본어는 사전형과 같을 때만 읽기로 써도 정답이다.
  function clozeForms(c) { return [c.ca].concat(c.l === 'ja' && c.ca === c.w && c.r ? [c.r] : []); }
  // 빈칸 폭: 힌트로 알려 주는 글자 수에 맞추고 너무 좁거나 넓지 않게
  function blankSize(c) { return Math.max(6, Math.min(18, c.ca.length * (c.l === 'ja' ? 2 : 1) + 2)); }
  function hint(c, cw) {
    if (cw) {
      var f = clozeForms(c), s = f[f.length - 1], n = s.replace(/\s/g, '').length;
      return (s !== c.ca ? '읽기 ' : '') + '“' + esc(s.charAt(0)) + '”로 시작하는 ' + n + '글자';
    }
    // 독일어 명사(ar 있음): 관사 포함 정답이므로 “관사 + 단어” 안내, 첫 글자 힌트
    if (c.ar) {
      var n = c.w.replace(/\s/g, '').length;
      return '관사 + 단어 | “' + esc(c.w.charAt(0)) + '”로 시작하는 ' + n + '글자';
    }
    var s = c.l === 'ja' ? (c.r || c.w) : c.w.replace(/\s*\([^)]*\)/g, ''), n = s.replace(/\s/g, '').length;
    return (c.l === 'ja' ? '읽기 ' : '') + '”' + esc(s.charAt(0)) + '”로 시작하는 ' + n + '글자' + (c.l !== 'ja' && /\s/.test(s.trim()) ? ', 낱말 ' + s.trim().split(/\s+/).length + '개' : '');
  }
  // 쓰기 채점: 대소문자, 띄어쓰기, 문장부호, 괄호 속 말은 보지 않는다. 독일어는 ae/oe/ue/ss, 일본어는 가타카나와 읽기도 정답.
  function norm(s, l, raw) {
    s = String(s).normalize('NFKC').toLowerCase().replace(/\([^)]*\)/g, ' ').replace(/[.,!?'"’`…~〜]/g, '').replace(/\s+/g, ' ').trim();
    if (l === 'de') s = s.replace(/^(der|die|das) /, '');  // 관사를 붙여 써도(das Ufer) 정답
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
  function grade(c, v, cw) {
    if (cw) {
      // 빈칸은 예문 속 꼴 그대로(관사 없음). 대소문자, 문장부호는 보지 않고 한 글자 오타는 봐준다.
      var tc = norm(v, c.l), fs = clozeForms(c);
      if (fs.some(function (x) { return norm(x, c.l) === tc; })) return { ok: true };
      var rc = norm(v, c.l, true), rf = norm(c.ca, c.l, true);
      var fd = function (x) { return x.replace(/ä/g, 'a').replace(/ö/g, 'o').replace(/ü/g, 'u').replace(/ß/g, 's'); };
      var nr = c.l !== 'ja' && rf.length >= 6 && dist(rc, rf) <= 1 && !(c.l === 'de' && fd(rc) === fd(rf));
      return { ok: nr, near: nr };
    }
    // 독일어 명사(ar 있음): 관사 포함 정답, 예: "die Dose"
    if (c.ar) {
      // 관사를 빼지 않는 norm: 대소문자/문장부호/띄어쓰기 정규화, 움라우트는 ae/oe/ue/ss로
      var normNoun = function (s, raw) {
        s = String(s).normalize('NFKC').toLowerCase().replace(/\([^)]*\)/g, ' ').replace(/[.,!?'"'`…~〜]/g, '').replace(/\s+/g, ' ').trim();
        if (!raw) s = s.replace(/ä/g, 'ae').replace(/ö/g, 'oe').replace(/ü/g, 'ue').replace(/ß/g, 'ss');
        return s;
      };
      var full = c.ar + ' ' + c.w;
      var t = normNoun(v), key = normNoun(full);
      if (t === key) return { ok: true };
      // 한 글자 오타 허용 (움라우트 누락은 오답)
      var rt = normNoun(v, true), rk = normNoun(full, true);
      var fold = function (x) { return x.replace(/ä/g, 'a').replace(/ö/g, 'o').replace(/ü/g, 'u').replace(/ß/g, 's'); };
      var near = rk.length >= 6 && dist(rt, rk) <= 1 && !(fold(rt) === fold(rk));
      if (near) return { ok: true, near: true };
      // 관사 없이 명사만 썼는지 확인 → 재시도 안내
      if (norm(v, 'de') === norm(c.w, 'de')) return { ok: false, missingArticle: true };
      return { ok: false };
    }
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
    // 맞든 틀리든 판정하는 순간 소리를 들려준다. 빈칸 채우기는 예문 전체, 나머지는 단어(이슈 #23)
    say(it.c, kindOf(it) === 'cloze');
  }
  function check() {
    var it = S.queue[0], f = root.querySelector('.dr-field');
    if (!f || f.disabled) return;
    if (!f.value.trim()) return f.focus();
    var g = grade(it.c, f.value, kindOf(it) === 'cloze');
    // 독일어 명사에서 관사 없이 명사만 쓴 경우: 재시도 허용, 관사 안내 표시
    if (g.missingArticle) {
      var ph = root.querySelector('.dr-qhint');
      if (ph) ph.textContent = '관사도 함께 써 주세요 (예: der …)';
      f.select();
      return;
    }
    answer(it, f.value.trim(), g.ok, g.near);
  }
  function later(it) { S.queue.splice(Math.min(3, S.queue.length), 0, it); }

  // iOS는 처음 누름에서 재생한 Audio 요소만 이후 자동 재생을 허락하므로 하나를 계속 쓴다.
  var player = null, sayN = 0;
  // 예문 글자(루비 읽기는 빼고). 예문 음성 파일이 없거나 예전에 담은 카드일 때 브라우저 음성으로 읽는다
  function exText(c) {
    var d = document.createElement('div'); d.innerHTML = c.ex || '';
    [].forEach.call(d.querySelectorAll('rt'), function (e) { e.remove(); });
    return d.textContent.trim();
  }
  function say(c, ex) {
    var src = ex ? c.sa : c.au, text = ex ? exText(c) || c.w : c.w;
    var n = ++sayN, btn = root && root.querySelector('.dr-listen');
    function on(v) {
      if (n !== sayN || !btn) return;
      btn.classList.toggle('on', v); btn.querySelector('span').textContent = v ? '읽어 주는 중' : '듣기';
    }
    function speak() {
      if (n !== sayN || !('speechSynthesis' in window)) return on(false);
      speechSynthesis.cancel(); var u = new SpeechSynthesisUtterance(text); u.lang = SPEECH[c.l] || 'en-US'; u.rate = 0.9;
      u.onend = u.onerror = function () { on(false); }; on(true); speechSynthesis.speak(u);
    }
    if ('speechSynthesis' in window) speechSynthesis.cancel();
    if (player) player.pause();
    if (!src) return speak();
    if (!player) player = new Audio();
    player.onended = function () { on(false); };
    player.onerror = function () { if (n === sayN) speak(); };
    if (player.src !== abs(src) || player.error) player.src = src; else player.currentTime = 0;  // 미리 받아 둔 소리는 그대로 처음부터
    on(true);
    var pr = player.play(); if (pr && pr.catch) pr.catch(speak);
  }
  // 문제가 나올 때 답 소리를 미리 받아 둔다. 답을 고른 뒤에야 받기 시작하면 받는 시간만큼 늦게 읽는다.
  // 지금 문제는 재생할 player 에 미리 넣고, 다음 문제 두 개는 HTTP 캐시에 받아 둔다.
  var warmed = {};
  function srcOf(it) { return kindOf(it) === 'cloze' ? it.c.sa : it.c.au; }
  function abs(src) { return new URL(src, location.href).href; }
  function warm() {
    var src = srcOf(S.queue[0]);
    if (src) {
      if (!player) player = new Audio();
      if (player.src !== abs(src)) { player.onended = player.onerror = null; player.preload = 'auto'; player.src = src; player.load(); }
    }
    S.queue.slice(1, 3).forEach(function (x) {
      var s = srcOf(x); if (!s || warmed[s]) return; warmed[s] = 1;
      if (window.fetch) fetch(s).then(function (r) { return r.blob(); }).catch(function () {});
    });
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
    var lg = e.target.closest('[data-login]'); if (lg) return toJoin('result');
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
      return answer(it, i, it.opts[i] === (it.c.mh || it.c.m));
    }
    if (act === 'check') return check();
    if (act === 'giveup') { if (it.pick == null) answer(it, '', false); return; }
    if (act === 'next') {
      // 카드와 같은 규칙: 틀리면 같은 회차 뒤로, 한 번에 못 맞힌 단어는 연속 2번 맞혀야 빠진다.
      hush();  // 긴 예문을 읽는 중에 다음 문제로 넘어가면 멈춘다
      var right = it.ok; S.queue.shift(); it.pick = null; it.ok = null;
      if (!right) { it.streak = 0; later(it); }
      else if (it.wrong === 0 || it.streak >= 1) it.done = true;
      else { it.streak++; later(it); }
      return render();
    }
    if (act === 'again') {
      var qt2 = b.getAttribute('data-qt');
      ga('word_drill_start', { lang: LANG, day: S.kind === 'review' ? 'review' : DAY, mode: qt2, from: 'result' });
      return start(S.list.map(function (x) { return x.c; }), qt2, S.kind);
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
    var db = load(), t = today(), now = new Date().toISOString();
    S.list.forEach(function (it) {
      var c = it.c, rec = db.items[c.k];
      if (!rec) { rec = {}; rec.s = 0; rec.due = add(t, 1); }
      else if (it.wrong > 0) { rec.s = 0; rec.due = add(t, 1); }
      else if (rec.due && rec.due <= t) { rec.s = (rec.s || 0) + 1; rec.due = rec.s >= INT.length ? null : add(t, INT[rec.s]); }
      ['k', 'l', 'd', 'w', 'r', 'm', 'mh', 'ex', 'sh', 'ek', 'au', 'sa', 'alts'].forEach(function (f) { if (c[f] != null) rec[f] = c[f]; });
      rec.x = it.wrong; rec.t = now;
      db.items[c.k] = rec;
    });
    db.days = (db.days || []).filter(function (d) { return d !== t; }).concat([t]).slice(-400);
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
      '<div class="dr-stat"><b>' + wrongs.length + '</b><span>틀린 단어</span></div></div>' +
      (AUTH.hasSession() && S.kind !== 'retry' ? '<div class="dr-saved" id="dr-saved">기록을 저장하는 중이에요</div>' : '') + '</section>' + nextTypes(tot) +
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
    if (locked()) gateShown('result');
    var sv = document.getElementById('dr-saved');
    if (sv && AUTH.sync) AUTH.sync().then(function (db) {
      if (!db) { sv.hidden = true; return; }
      var st = AUTH.streak(db.days);
      sv.innerHTML = '✓ 기록을 저장했어요<a href="/me/">' + (st.now > 1 ? '🔥 연속 ' + st.now + '일' : '마이페이지') + '</a>';
    }).catch(function () {
      sv.className = 'dr-saved err'; sv.textContent = '지금은 저장하지 못했어요. 다음에 열 때 함께 올려요.';
    });
  }

  // 결과 화면의 "이어서 문제 풀기"(W15, W16): 같은 단어로 다른 문제를 바로 시작한다. 방금 푼 종류는 맨 뒤에 "한 번 더"로.
  var QTYPES = [['quiz', '뜻 고르기', '4개 중 하나 고르기'], ['write', '단어 쓰기', '뜻 보고 단어 입력'], ['cloze', '빈칸 채우기', '예문 빈칸에 단어 입력']];
  function nextTypes(tot) {
    if (locked()) {
      // 로그인 전(K08): 문제는 잠그고 카카오, Google 로 시작하게 한다
      return '<section class="card"><h2 class="dr-h6">이제 문제로 확인해 볼까요?</h2><p class="desc dr-next">외운 단어 ' + tot + '개를 문제로 풀면 진짜 기억에 남아요.</p><div class="dr-ntypes">' +
        QTYPES.map(function (q) {
          return '<div class="dr-ntype lk"><span class="tx"><b>' + q[1] + '</b><span>' + q[2] + '</span></span><span class="go" aria-label="로그인 필요">🔒</span></div>';
        }).join('') + '</div><div class="dr-gap"><a class="dr-kbtn" data-login="kakao" href="' + joinHref('result') + '">' + KICON + '카카오로 시작하고 문제 풀기</a>' +
        '<a class="dr-gbtn" data-login="google" href="' + joinHref('result') + '">' + GICON + 'Google로 시작하기</a>' +
        '<button class="dr-later" type="button" data-act="close">오늘은 여기까지</button></div></section>';
    }
    var cur = S.mode, ts = QTYPES.filter(function (q) { return q[0] !== cur; }).concat(QTYPES.filter(function (q) { return q[0] === cur; }));
    return '<section class="card"><h2 class="dr-h6">' + (cur === 'card' ? '이어서 문제 풀기' : '이어서 다른 문제 풀기') + '</h2>' +
      '<p class="desc dr-next">' + (cur === 'card' ? '방금 외운 단어 ' + tot + '개로 바로 풀어 봐요.' : '같은 단어 ' + tot + '개를 다른 방식으로 풀어 봐요.') + '</p><div class="dr-ntypes">' +
      ts.map(function (q, i) {
        var done = q[0] === cur;
        return '<button class="dr-ntype' + (done ? ' done' : i === 0 ? ' first' : '') + '" type="button" data-act="again" data-qt="' + q[0] + '"><span class="tx"><b>' + q[1] +
          (done ? '<i class="badge">방금 풀었어요</i>' : '') + '</b><span>' + q[2] + '</span></span><span class="go">' + (done ? '한 번 더' : '시작') + '</span></button>';
      }).join('') + '</div></section>';
  }

  // 진입 카드
  var card = document.getElementById('drill');
  if (card && CARDS.length) {
    // 고른 방식(카드/문제, 문제 종류)은 이 기기에 기억해 다음에도 그대로 보여 준다.
    var PREF = 'drill:pref', pref = {};
    try { pref = JSON.parse(localStorage.getItem(PREF)) || {}; } catch (e) {}
    var mode = pref.m === 'quiz' ? 'quiz' : 'card', qt = ['quiz', 'write', 'cloze'].indexOf(pref.q) >= 0 ? pref.q : 'quiz';
    var modes = card.querySelectorAll('.dr-mode'), qts = card.querySelectorAll('.dr-qt'), qbox = document.getElementById('dr-qts'), go1 = document.getElementById('dr-start');
    var gate = document.getElementById('dr-gate'), foot = document.getElementById('dr-foot');
    [].forEach.call(card.querySelectorAll('[data-login]'), function (a) { a.href = joinHref('entry'); a.addEventListener('click', function () { toJoin('entry'); }); });
    function paint() {
      [].forEach.call(modes, function (x) { x.setAttribute('aria-pressed', String(x.getAttribute('data-mode') === mode)); });
      [].forEach.call(qts, function (x) { x.setAttribute('aria-pressed', String(x.getAttribute('data-qt') === qt)); });
      if (qbox) qbox.hidden = mode !== 'quiz';
      go1.textContent = CARDS.length + (mode === 'card' ? '개 외우기 시작' : '문제 풀기 시작');
      // 로그인 전 문제 풀기(K07): 종류에 자물쇠, 시작 버튼 대신 로그인 안내
      var lk = mode === 'quiz' && locked();
      if (qbox) qbox.classList.toggle('locked', lk);
      if (gate) gate.hidden = !lk;
      go1.hidden = lk;
      if (foot) foot.hidden = lk && !!gate;
      if (lk) gateShown('entry');
      var sub = card.querySelector('.dr-mode[data-mode="quiz"] span');
      if (sub) sub.textContent = locked() ? '로그인하면 열려요' : '문제 종류를 골라요';
      if (foot && AUTH.hasSession()) foot.textContent = foot.textContent.replace('고른 방식과 기록은 이 기기에만 남아요.', '기록은 내 계정에 저장돼요.');
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
  // 로그인한 사람은 다른 기기에서 쌓은 기록을 받아 와 복습 띠를 다시 그린다
  if (AUTH.hasSession() && AUTH.sync) AUTH.sync().then(function (db) { if (db) showDue(); }, function () {});
})();
