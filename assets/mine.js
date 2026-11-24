// 내 해석 기록(시안 design/mine-notes): 저장소, AI 에게 물어볼 글, 시트를 지문 페이지(linewrite.js), 노트(notes.js), 마이페이지와 주간 복습 카드가 같이 쓴다.
// 모두 이 기기의 localStorage 에만 있다.
//   mine:v1  { 'en/2026-11-24/b': { t: 주제, u: 지문에 쓴 때, m: 노트에서 고친 때, n: 문장 수, s: { 0: { v: 해석, st: 헷갈림, e: 원문, r: { v, u } 다시 쓴 해석 } } } }
//   mine:ai  { 'en/2026-11-24/b' 또는 'en/~'(여러 지문 묶음): [{ v: 붙인 답, u }] }
(function () {
  var KEY = 'mine:v1', AI = 'mine:ai', WEEK = 7 * 864e5, MAXA = 20000;
  var DAYKEY = /^(en|ja|de)\/\d{4}-\d\d-\d\d\/[ab]$/, AIKEY = /^(en|ja|de)\/(\d{4}-\d\d-\d\d\/[ab]|~)$/;
  // 질문 머리와 자주 틀리는 부분: tools/langs.py 와 같은 글(tests/test_linewrite.py 가 맞춰 본다)
  var WHO = {
    en: ['나는 CEFR B1~B2 수준의 한국인 영어 학습자입니다.', '자주 틀리는 부분(문장 끝의 시간, 수량 정보, 큰 숫자, 비슷하게 생긴 단어, 관사와 복수 -s, 숙어 의미)도 함께 짚어 주세요.'],
    ja: ['나는 JLPT N3 수준의 한국인 일본어 학습자입니다.', '자주 틀리는 부분(조사 は・が・を・に・で, 동사 활용과 시제, 한자 읽기, 숫자와 조수사)도 함께 짚어 주세요.'],
    de: ['나는 CEFR B1~B2 수준의 한국인 독일어 학습자입니다.', '자주 틀리는 부분(명사 성(der/die/das), 격변화(Kasus), 분리동사(trennbare Verben), 문장 끝 동사 위치(Verbstellung), 복합 명사)도 함께 짚어 주세요.']
  };
  function esc(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;'); }
  function read(k) {
    try { var v = JSON.parse(localStorage.getItem(k)); return v && typeof v === 'object' && !Array.isArray(v) ? v : {}; } catch (e) { return {}; }
  }
  function load() { return read(KEY); }
  function loadAi() { return read(AI); }
  function write(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); return true; } catch (e) { return false; } }
  function trim(d) {  // 남길 것이 없는 문장은 뺀다
    Object.keys(d.s).forEach(function (i) { var x = d.s[i]; if (!x.v && !x.st && !x.r) delete d.s[i]; });
    return Object.keys(d.s).length ? d : null;
  }
  function put(id, d) { var all = load(); if (d && trim(d)) all[id] = d; else delete all[id]; return write(KEY, all); }
  // 문장 하나를 고친다. 저장할 때마다 새로 읽어 다른 탭이 쓴 것을 지우지 않는다
  function edit(id, i, fn) {
    var d = load()[id];
    if (!d || !d.s) return false;
    if (!d.s[i]) d.s[i] = { v: '', st: false, e: '' };
    fn(d.s[i]); d.m = Date.now(); return put(id, d);  // u(지문에 쓴 때)는 그대로 두고 m 만 바꾼다
  }
  function addAi(id, text) {
    var all = loadAi(), a = all[id] || [];
    all[id] = [{ v: text.slice(0, MAXA), u: Date.now() }].concat(a);
    return write(AI, all);
  }
  function delAi(id, u) {
    var all = loadAi();
    all[id] = (all[id] || []).filter(function (x) { return x.u !== u; });
    if (!all[id].length) delete all[id];
    return write(AI, all);
  }
  // 조건에 맞는 지문과 문장: {lang, id, week, star, from, to} -> [{id, t, d, list: [{i, e, v, st, r}]}], 오래된 지문부터
  function pick(q) {
    var all = load(), since = Date.now() - WEEK, out = [];
    Object.keys(all).sort(function (a, b) { return a.split('/')[1] < b.split('/')[1] ? -1 : a.split('/')[1] > b.split('/')[1] ? 1 : a < b ? -1 : 1; }).forEach(function (k) {
      var d = all[k], p = k.split('/');
      if (!DAYKEY.test(k) || !d || !d.s || (q.lang && p[0] !== q.lang) || (q.id && k !== q.id) || (q.week && !(d.u >= since)) || (q.from && p[1] < q.from) || (q.to && p[1] > q.to)) return;
      var list = Object.keys(d.s).map(Number).sort(function (a, b) { return a - b; }).map(function (i) {
        var x = d.s[i]; return { i: i, e: x.e, v: x.v, st: x.st, r: x.r };
      }).filter(function (x) { return q.star ? x.st : q.any ? true : x.v; });
      if (list.length) out.push({ id: k, t: d.t, d: p[1], n: d.n, u: d.u, list: list });
    });
    return out;
  }
  function size(q) { return pick(q).reduce(function (n, d) { return n + d.list.length; }, 0); }
  // 붙인 AI 답 수: 지문에 붙인 답과 묶음 답. 주간은 붙인 때, 기간은 지문 날짜로 센다(묶음 답은 붙인 날짜)
  function ymd(u) { var d = new Date(u); return d.getFullYear() + '-' + ('0' + (d.getMonth() + 1)).slice(-2) + '-' + ('0' + d.getDate()).slice(-2); }
  function aiCount(q) {
    var all = loadAi(), since = Date.now() - WEEK, n = 0;
    Object.keys(all).forEach(function (k) {
      var p = k.split('/');
      if (!AIKEY.test(k) || (q.lang && p[0] !== q.lang)) return;
      all[k].forEach(function (x) {
        var day = p[1] === '~' ? ymd(x.u) : p[1];
        if ((!q.week || x.u >= since) && (!q.from || day >= q.from) && (!q.to || day <= q.to)) n++;
      });
    });
    return n;
  }

  // 파일로 옮기기(M26). 파일은 밖에서 온 값이라 모양을 하나씩 확인한 것만 받는다
  function dump() { return JSON.stringify({ app: 'dokhaehanip-mine', ver: 1, mine: load(), ai: loadAi() }); }
  function str(v, max) { return typeof v === 'string' ? v.slice(0, max) : ''; }
  function time(v) { return typeof v === 'number' && isFinite(v) && v > 0 ? Math.min(v, Date.now()) : 0; }
  function last(d) { return Math.max(d.u || 0, d.m || 0); }
  function cleanDay(d) {
    if (!d || typeof d !== 'object' || !d.s || typeof d.s !== 'object') return null;
    var o = { t: str(d.t, 200), u: time(d.u), m: time(d.m), n: d.n > 0 && d.n < 100 ? Math.floor(d.n) : 0, s: {} };
    Object.keys(d.s).forEach(function (i) {
      var x = d.s[i];
      if (!/^\d{1,2}$/.test(i) || !x || typeof x !== 'object') return;
      var y = { v: str(x.v, 1000), st: x.st === true, e: str(x.e, 2000) };
      if (x.r && str(x.r.v, 1000)) y.r = { v: str(x.r.v, 1000), u: time(x.r.u) };
      o.s[i] = y;
    });
    return trim(o);
  }
  // 합치기: 같은 지문은 나중에 고친 쪽, AI 답은 글이 다른 것만 더한다. 받은 지문과 답의 수를 돌려준다(못 읽으면 null)
  function restore(text) {
    var f; try { f = JSON.parse(text); } catch (e) { return null; }
    if (!f || f.app !== 'dokhaehanip-mine' || !f.mine || typeof f.mine !== 'object') return null;
    var all = load(), ai = loadAi(), days = 0, answers = 0, old = localStorage.getItem(KEY);
    Object.keys(f.mine).forEach(function (k) {
      var d = DAYKEY.test(k) && cleanDay(f.mine[k]);
      if (d && !(all[k] && last(all[k]) >= last(d))) { all[k] = d; days++; }
    });
    if (f.ai && typeof f.ai === 'object') Object.keys(f.ai).forEach(function (k) {
      if (!AIKEY.test(k) || !Array.isArray(f.ai[k])) return;
      var a = ai[k] || [];
      f.ai[k].forEach(function (x) {
        var v = str(x && x.v, MAXA);
        if (!v.trim() || a.some(function (y) { return y.v === v; })) return;
        var u = time(x.u);
        while (a.some(function (y) { return y.u === u; })) u++;  // u 는 지울 때 쓰는 이름이라 겹치지 않게
        a.push({ v: v, u: u }); answers++;
      });
      if (a.length) ai[k] = a.sort(function (x, y) { return y.u - x.u; });
    });
    if (!write(KEY, all)) return { failed: true };
    if (!write(AI, ai)) {  // 반만 들어가지 않게 되돌린다
      try { if (old === null) localStorage.removeItem(KEY); else localStorage.setItem(KEY, old); } catch (e) {}
      return { failed: true };
    }
    return { days: days, answers: answers };
  }

  // 시트
  var dim, sheet, back;
  function close() {
    if (!sheet) return;
    dim.remove(); sheet.remove(); sheet = dim = null;
    if (back) back.focus({ preventScroll: true });
  }
  function open(html, title) {
    if (sheet) { dim.remove(); sheet.remove(); } else back = document.activeElement;
    dim = document.createElement('div'); dim.className = 'lw-dim'; dim.addEventListener('click', close);
    sheet = document.createElement('div'); sheet.className = 'lw-sheet'; sheet.tabIndex = -1;
    sheet.setAttribute('role', 'dialog'); sheet.setAttribute('aria-modal', 'true'); sheet.setAttribute('aria-label', title);
    sheet.innerHTML = html;
    document.body.appendChild(dim); document.body.appendChild(sheet); sheet.focus({ preventScroll: true });
    return sheet;
  }
  document.addEventListener('keydown', function (e) {
    if (!sheet) return;
    if (e.key === 'Escape') return close();
    if (e.key !== 'Tab') return;
    var f = [].slice.call(sheet.querySelectorAll('button, input:not(:disabled), textarea')), a = document.activeElement;
    if (e.shiftKey && (a === f[0] || a === sheet)) { e.preventDefault(); f[f.length - 1].focus(); }
    else if (!e.shiftKey && a === f[f.length - 1]) { e.preventDefault(); f[0].focus(); }
  });
  function toast(title, text, act, fn) {
    var t = document.createElement('div'); t.className = 'lw-toast'; t.setAttribute('role', 'status');
    t.innerHTML = '<div><b>' + esc(title) + '</b>' + esc(text) + '</div>';
    if (act) {
      var b = document.createElement('button'); b.type = 'button'; b.textContent = act;
      b.addEventListener('click', function () { t.remove(); fn(); }); t.appendChild(b);
    }
    document.body.appendChild(t); setTimeout(function () { t.remove(); }, act ? 8000 : 3500);
  }
  function ga(name, p) { if (typeof gtag === 'function') gtag('event', name, p); }

  // AI 에게 물어보기(M13, M14, M21, M30). ctx: { lang, id(지문 하나를 볼 때) }
  var ASK = {
    fix: ['문장별로 고쳐 받기', '잘 잡은 것, 틀린 부분과 이유, 더 자연스러운 해석', '내 해석을 문장 번호별로 원문과 대조해 피드백해 주세요.\n1) 잘 잡은 것: 한두 줄, 사실만.\n2) 짚을 것: 틀렸거나 놓친 부분, 올바른 해석, 이유를 번호로 정리.\n3) 오늘 하나만 가져간다면: 핵심 패턴 하나.'],
    habit: ['반복되는 실수 찾기', '자주 틀리는 습관 3가지와 예시, 다음에 연습할 것', '내 해석을 원문과 대조해 반복되는 실수 습관을 최대 3가지 찾아 주세요. 습관마다 내 해석에서 예시를 들고, 다음에 무엇을 연습하면 좋을지 알려 주세요. 근거가 부족하면 억지로 채우지 마세요.'],
    quiz: ['복습 문제 받기', '내가 틀린 부분으로 짧은 해석 문제 5개', '내 해석에서 틀렸거나 어색한 부분을 먼저 짧게 짚고, 그 부분을 연습할 짧은 해석 문제 5개를 같은 난이도로 내 주세요. 정답은 내가 답한 뒤에 알려 주세요.']
  };
  var sel = { range: 'today', ask: 'fix' };
  function query(ctx, range) { return range === 'today' ? { lang: ctx.lang, id: ctx.id } : range === 'week' ? { lang: ctx.lang, week: true } : { lang: ctx.lang, star: true }; }
  function compose(ctx, range, ask) {
    var body = pick(query(ctx, range)).map(function (d) {
      return '[지문] ' + d.t + ' (' + d.d + ')\n\n' + d.list.map(function (x) {
        return (x.i + 1) + '. ' + x.e + '\n내 해석: ' + (x.v || '(아직 못 씀)') + (x.st ? ' (헷갈림)' : '');
      }).join('\n\n');
    }).join('\n\n');
    return [WHO[ctx.lang][0] + ' 아래는 읽은 문장과 내가 쓴 해석입니다.', body,
      '[요청]\n' + ASK[ask][2] + '\n' + WHO[ctx.lang][1] + '\n칭찬은 과하지 않게, 한국어 존댓말로 답해 주세요.'].join('\n\n');
  }
  function askSheet(ctx) {
    var n = { today: ctx.id ? size(query(ctx, 'today')) : 0, week: size(query(ctx, 'week')), star: size(query(ctx, 'star')) };
    if (!n[sel.range]) sel.range = n.today ? 'today' : n.week ? 'week' : 'star';
    function seg(k, t) {
      return '<label><input type="radio" name="lw-r" value="' + k + '"' + (sel.range === k ? ' checked' : '') + (n[k] ? '' : ' disabled') + '>' + t + '<small>' + n[k] + '문장</small></label>';
    }
    var s = open('<h3>AI에게 물어보기</h3><p>원문과 내 해석을 질문과 함께 복사해요. 평소 쓰는 AI 채팅에 붙여 넣으면 돼요.</p>' +
      '<fieldset><legend>범위</legend><div class="lw-seg">' + (ctx.id ? seg('today', '이 지문') : '') + seg('week', '최근 7일') + seg('star', '헷갈림') + '</div></fieldset>' +
      '<fieldset><legend>무엇을 물어볼까요</legend>' + Object.keys(ASK).map(function (k) {
        return '<label class="lw-rad"><input type="radio" name="lw-a" value="' + k + '"' + (sel.ask === k ? ' checked' : '') + '><span><b>' + ASK[k][0] + '</b><span>' + ASK[k][1] + '</span></span></label>';
      }).join('') + '</fieldset><p>안 쓴 문장은 빼고 보내요. 헷갈림은 안 쓴 문장도 보내요.</p>' +
      '<div class="lw-row"><button class="lw-btn line" type="button" data-x="view">미리 보기</button><button class="lw-btn" type="button" data-x="copy">복사하기</button></div>' +
      '<button class="lw-link" type="button" data-x="paste">답을 받았나요? 붙여 두기</button>', 'AI에게 물어보기');
    s.addEventListener('change', function (e) { sel[e.target.name === 'lw-r' ? 'range' : 'ask'] = e.target.value; });
    s.querySelector('[data-x=view]').addEventListener('click', function () { textSheet(ctx, false); });
    s.querySelector('[data-x=copy]').addEventListener('click', function () { copy(ctx); });
    s.querySelector('[data-x=paste]').addEventListener('click', function () { pasteSheet(ctx); });
  }
  function textSheet(ctx, failed) {
    var title = failed ? '자동 복사가 안 됐어요' : '미리 보기';
    var s = open('<h3>' + title + '</h3><p>' + (failed ? '브라우저가 복사를 막았어요. 아래 글을 길게 눌러 전체 선택한 뒤 복사해 주세요.' : '이대로 복사돼요.') + '</p>' +
      '<textarea class="lw-area" readonly aria-label="복사할 글">' + esc(compose(ctx, sel.range, sel.ask)) + '</textarea>' +
      '<div class="lw-row"><button class="lw-btn line" type="button" data-x="back">' + (failed ? '닫기' : '뒤로') + '</button><button class="lw-btn" type="button" data-x="copy">' + (failed ? '다시 시도' : '복사하기') + '</button></div>', title);
    if (failed) { var a = s.querySelector('textarea'); a.focus(); a.select(); }
    s.querySelector('[data-x=back]').addEventListener('click', failed ? close : function () { askSheet(ctx); });
    s.querySelector('[data-x=copy]').addEventListener('click', function () { copy(ctx); });
  }
  function copy(ctx) {
    var text = compose(ctx, sel.range, sel.ask);
    function done() {
      ga('feedback_copy', { lang: ctx.lang, day: ctx.id ? ctx.id.split('/')[1] : '', range: sel.range, ask: sel.ask });
      close();
      toast('복사했어요', 'AI 답을 받으면 노트에 붙여 두세요.', '답 붙이기', function () { pasteSheet(ctx); });
    }
    function old() {
      var ta = document.createElement('textarea'), ok = false;
      ta.value = text; ta.readOnly = true; ta.style.cssText = 'position:fixed;top:0;left:0;opacity:0';
      (sheet || document.body).appendChild(ta); ta.select();
      try { ok = document.execCommand('copy'); } catch (e) {}
      ta.remove();
      if (ok) done(); else textSheet(ctx, true);
    }
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done, old); else old();
  }

  // AI 답 붙여 두기(M18). 지문 하나에 물었으면 그 지문, 여러 지문이면 묶음
  function pasteSheet(ctx) {
    var day = ctx.id && ctx.id.split('/')[1], one = !!ctx.id && sel.range === 'today';
    var label = day && Number(day.slice(5, 7)) + '월 ' + Number(day.slice(8)) + '일 지문';
    var s = open('<h3>AI 답 붙여 두기</h3><p>받은 답을 붙여 두면 노트에서 다시 보고, 다시 풀 때 같이 봐요. 이 기기에만 저장돼요.</p>' +
      (ctx.id ? '<fieldset><legend>어디에 붙일까요</legend><div class="lw-seg two"><label><input type="radio" name="lw-p" value="one"' + (one ? ' checked' : '') + '>' + label + '</label>' +
        '<label><input type="radio" name="lw-p" value="all"' + (one ? '' : ' checked') + '>여러 지문 묶음</label></div></fieldset>' : '') +
      '<button class="lw-btn line" type="button" data-x="paste">복사한 답 붙여넣기</button>' +
      '<textarea class="lw-area short" maxlength="' + MAXA + '" aria-label="받은 AI 답" placeholder="여기에 받은 답을 붙여 넣어 주세요"></textarea><p class="lw-err" role="alert" hidden></p>' +
      '<div class="lw-row"><button class="lw-btn line" type="button" data-x="no">닫기</button><button class="lw-btn" type="button" data-x="save">저장</button></div>', 'AI 답 붙여 두기');
    var ta = s.querySelector('textarea'), err = s.querySelector('.lw-err');
    function say(t) { err.textContent = t; err.hidden = false; }
    ta.addEventListener('input', function () { err.hidden = true; });
    s.querySelector('[data-x=paste]').addEventListener('click', function () {
      function no() { ta.focus(); say('브라우저가 붙여넣기를 막았어요. 아래 칸을 길게 눌러 붙여 넣어 주세요.'); }
      if (!navigator.clipboard || !navigator.clipboard.readText) return no();
      navigator.clipboard.readText().then(function (t) { if (!t.trim()) return no(); ta.value = t.slice(0, MAXA); err.hidden = true; }, no);
    });
    s.querySelector('[data-x=no]').addEventListener('click', close);
    s.querySelector('[data-x=save]').addEventListener('click', function () {
      var t = ta.value.trim(), w = s.querySelector('[name=lw-p]:checked');
      if (!t) { ta.focus(); return say('붙일 답이 아직 없어요.'); }
      var id = ctx.id && w && w.value === 'one' ? ctx.id : ctx.lang + '/~';
      if (!addAi(id, t)) return say('저장하지 못했어요. 이 기기의 저장 공간을 확인해 주세요.');
      ga('answer_paste', { lang: ctx.lang });
      close();
      toast('붙여 두었어요', '마이페이지의 내 해석 노트에서 볼 수 있어요.', '노트 보기', function () { location.href = '/me/notes/#' + id; });
      if (ctx.saved) ctx.saved();
    });
  }

  // 마이페이지와 주간 복습 페이지의 카드(M15, M23, M28). 보여 줄 것이 없으면 주간 카드는 나오지 않는다
  function card(el) {
    var q = { lang: el.dataset.lang, from: el.dataset.from, to: el.dataset.to };
    if (!q.from) q.week = true;
    var star = size({ lang: q.lang, from: q.from, to: q.to, star: true }), n = size(q), ai = aiCount(q.from ? q : {});
    el.querySelector('[data-n=w]').textContent = n;
    el.querySelector('[data-n=s]').textContent = star;
    el.querySelector('[data-n=a]').textContent = ai;
    var r = el.querySelector('[data-n=retry]');
    r.hidden = !star; r.textContent = '★ ' + star + '문장 다시 풀기';
    r.href = '/me/notes/#retry' + (q.lang ? '/' + q.lang : '') + (q.from ? '/' + q.from + '/' + q.to : '');
    var nw = el.querySelector('.mc-new'), seen = true;
    try { seen = !!localStorage.getItem('mine:seen'); } catch (e) {}
    if (nw) nw.hidden = seen;
    el.hidden = !!q.from && !n && !star && !ai;
  }
  function cards() { [].forEach.call(document.querySelectorAll('[data-mine-card]'), card); }

  window.mineNotes = { load: load, loadAi: loadAi, put: put, edit: edit, addAi: addAi, delAi: delAi, pick: pick, size: size, aiCount: aiCount,
    dump: dump, restore: restore, compose: compose, askSheet: askSheet, pasteSheet: pasteSheet, open: open, close: close, toast: toast,
    ga: ga, esc: esc, ymd: ymd, cards: cards, DAYKEY: DAYKEY, AIKEY: AIKEY };
  cards();
  window.addEventListener('pageshow', function (e) { if (e.persisted) cards(); });
})();
