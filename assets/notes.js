// 내 해석 노트(/me/notes/, 시안 design/mine-notes M16~M20, M22, M26, M27, M29, M31). 기록은 mine.js 가 이 기기에서 읽고 쓴다.
// 화면은 # 뒤로 나눈다: 없음(목록), en/2026-11-24/b(지문 하루), en/~(묶음 답), retry[/언어[/시작/끝]](다시 풀기), retry/en/2026-11-24/b, ask/en(목록 + 물어보기)
(function () {
  'use strict';
  var M = window.mineNotes, box = document.getElementById('mn'), esc = M.esc;
  var YMD = /^\d{4}-\d\d-\d\d$/, WD = '일월화수목금토', LNAME = { en: '영어', ja: '일본어', de: '독일어' };
  var lang = '', week = true, pages = {}, run = null, view = 0;
  try { localStorage.setItem('mine:seen', '1'); } catch (e) {}
  function ic(d, fill) { return '<svg viewBox="0 0 24 24" fill="' + (fill ? 'currentColor' : 'none') + '" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="' + d + '"/></svg>'; }
  var STAR = 'M12 3.5l2.6 5.4 5.9.8-4.3 4.1 1 5.9-5.2-2.8-5.2 2.8 1-5.9-4.3-4.1 5.9-.8z', CHAT = 'M4 5h16v11H10l-4 4v-4H4z', BACK = 'M15 5l-7 7 7 7';
  function date(d) { return new Date(d + 'T00:00:00'); }
  function md(d) { return Number(d.slice(5, 7)) + '월 ' + Number(d.slice(8, 10)) + '일'; }
  function crumb(href, t) { return '<a class="mn-crumb" href="' + href + '">' + ic(BACK) + t + '</a>'; }
  function q(s) { return box.querySelector(s); }
  function on(s, fn) { var el = q(s); if (el) el.addEventListener('click', fn); }
  function h1() { var h = q('h1, [data-focus]'); if (h) { h.tabIndex = -1; h.focus({ preventScroll: true }); } window.scrollTo(0, 0); }
  function langs() {
    var n = {};
    Object.keys(M.load()).forEach(function (k) { if (M.DAYKEY.test(k)) n[k.slice(0, 2)] = Math.max(n[k.slice(0, 2)] || 0, M.load()[k].u || 0); });
    Object.keys(M.loadAi()).forEach(function (k) { if (M.AIKEY.test(k)) n[k.slice(0, 2)] = n[k.slice(0, 2)] || 0; });
    return Object.keys(n).sort(function (a, b) { return n[b] - n[a]; });  // 가장 최근에 쓴 언어부터
  }

  // 지문 페이지에서 원문과 모범 해석을 가져온다(같은 사이트의 생성 페이지). 실패하면 이 기기에 남긴 원문만 보인다
  function page(id) {
    var p = id.split('/'), url = '/' + p[0] + '/' + p[1] + '/';
    if (!pages[url]) pages[url] = fetch(url).then(function (r) { if (!r.ok) throw new Error(r.status); return r.text(); })
      .then(function (t) { return [].slice.call(new DOMParser().parseFromString(t, 'text/html').querySelectorAll('#passage .sent')); })
      .catch(function (e) { delete pages[url]; throw e; });
    return pages[url].then(function (sents) {
      return sents.map(function (s) {
        var a = p[2] === 'a' && s.querySelector('.en-a'), en = s.querySelector(a ? '.en-a' : '.en').cloneNode(true), ko = s.querySelector(a ? '.ko-a' : '.ko');
        [].forEach.call(en.querySelectorAll('.badge'), function (x) { x.remove(); });
        var plain = en.cloneNode(true);
        [].forEach.call(plain.querySelectorAll('rt, rp'), function (x) { x.remove(); });
        return { node: en, e: plain.textContent.trim(), ko: ko ? ko.textContent.trim() : '' };
      });
    });
  }
  // 쓴 뒤 지문이 바뀌었으면 번호가 어긋날 수 있다. 원문이 같을 때만 그 문장의 모범 해석을 쓴다
  function match(list, i, e) { var x = list && list[i]; return x && (!e || x.e === e) ? x : null; }
  function putText(el, x, e) {
    el.textContent = '';
    if (x) [].slice.call(document.importNode(x.node, true).childNodes).forEach(function (n) { el.appendChild(n); }); else el.textContent = e || '';
  }

  // 붙인 답에서 "2번"처럼 문장 번호가 또렷한 줄부터 다음 번호나 다음 제목 전까지. "2)", "2." 는 소제목일 수 있어 쓰지 않는다. 못 찾으면 빈 글
  function part(text, n) {
    var lines = text.split('\n'), out = [], hit = false, head = /^[\s#>*-]*(\d{1,2})\s*번(?=[\s:.,)*]|문장|$)/, stop = /^(?:\s*\**\d{1,2}[.)]|\s*#|\s*\**오늘\s)/;
    lines.forEach(function (l) {
      var m = head.exec(l);
      if (m) hit = Number(m[1]) === n; else if (stop.test(l)) hit = false;
      if (hit) out.push(l);
    });
    return out.join('\n').trim();
  }
  function aiHtml(id, n) {
    return (M.loadAi()[id] || []).map(function (x) {
      return '<div class="mn-ai"><div class="h">' + ic(CHAT) + '붙여 둔 AI 답<span>' + md(M.ymd(x.u)) + '</span></div><div class="t' + (x.v.length > 220 || x.v.split('\n').length > 5 ? ' cut' : '') + '">' + esc(x.v) + '</div>' +
        '<div class="b"><button type="button" data-more aria-expanded="false">전체 보기</button><button type="button" data-del="' + Number(x.u) + '">지우기</button></div></div>';
    }).join('');
  }
  function wireAi(id, again) {
    [].forEach.call(box.querySelectorAll('.mn-ai'), function (el) {
      var t = el.querySelector('.t'), m = el.querySelector('[data-more]'), d = el.querySelector('[data-del]');
      m.hidden = !t.classList.contains('cut');
      m.addEventListener('click', function () { var o = t.classList.toggle('open'); m.textContent = o ? '접기' : '전체 보기'; m.setAttribute('aria-expanded', String(o)); });
      d.addEventListener('click', function () {
        if (!confirm('붙여 둔 이 답을 지울까요? 되돌릴 수 없어요.')) return;
        if (!M.delAi(id, Number(d.dataset.del))) return M.toast('지우지 못했어요', '잠시 뒤에 다시 해 주세요.');
        again();
      });
    });
  }

  // 목록(M16, M22, M29)
  function list(ask) {
    var ls = langs();
    if (!ls.length) {
      box.innerHTML = crumb('/me/', '마이페이지') + '<h1>내 해석 노트</h1><section class="mn-card mn-empty">' + ic('M4 20l1-4L16 5l3 3L8 19z') + '<b>아직 쓴 해석이 없어요</b>' +
        '<p>지문에서 "문장마다 해석 쓰기"를 켜고<br>한 줄씩 적어 보세요. 여기에 저절로 모여요.</p><a class="lw-btn" id="mnGo" href="/en/">오늘 지문에서 써 보기</a></section>' +
        '<p class="mn-note">쓴 해석은 이 기기에만 저장돼요. 다른 기기에서 쓴 것은 <button type="button" id="mnFile">가져오기</button>로 옮길 수 있어요.</p>';
      on('#mnFile', files);
      fetch('/latest.json', { cache: 'no-store' }).then(function (r) { return r.json(); }).then(function (d) { if (q('#mnGo')) q('#mnGo').href = '/en/' + d.langs.en.latest + '/'; }, function () {});
      return h1();
    }
    if (ls.indexOf(lang) < 0) lang = ls[0];
    var f = { lang: lang, week: week }, n = M.size(f), star = M.size({ lang: lang, week: week, star: true }), ai = M.aiCount(f);
    var all = M.loadAi(), days = {}, since = Date.now() - 7 * 864e5;
    M.pick({ lang: lang, week: week, any: true }).forEach(function (d) { days[d.id] = d; });
    Object.keys(all).forEach(function (k) {  // 쓴 문장은 지웠어도 붙인 답이 남은 지문
      if (!M.AIKEY.test(k) || k.slice(0, 2) !== lang || days[k] || k.slice(3) === '~' || (week && !all[k].some(function (x) { return x.u >= since; }))) return;
      var r = M.load()[k];
      days[k] = { id: k, d: k.split('/')[1], t: (r && r.t) || md(k.split('/')[1]) + ' 지문', list: [], n: r && r.n };
    });
    var rowsHtml = Object.keys(days).map(function (k) { return days[k]; }).sort(function (a, b) { return a.d < b.d ? 1 : a.d > b.d ? -1 : a.id < b.id ? 1 : -1; }).map(function (d) {
      var w = d.list.filter(function (x) { return x.v; }).length, s = d.list.filter(function (x) { return x.st; }).length;
      return row(d.id, d.d, esc(d.t) + (d.id.slice(-1) === 'a' ? ' <small>기초</small>' : ''), all[d.id], (d.n ? w + '/' + d.n : w + '문장'), s);
    }).join('');
    var bun = (all[lang + '/~'] || []).filter(function (x) { return !week || x.u >= since; });
    if (bun.length) rowsHtml = row(lang + '/~', M.ymd(bun[0].u), '여러 지문 묶음에 받은 AI 답', bun, '', 0) + rowsHtml;
    box.innerHTML = crumb('/me/', '마이페이지') + '<h1>내 해석 노트</h1><section class="mn-card"><div class="mn-k">' + (week ? '최근 7일' : '전체') + '</div><div class="mn-big">' + n + '<small>문장 썼어요</small></div>' +
      '<div class="mn-m"><span>' + ic(STAR, 1) + '헷갈림 ' + star + '</span><span>' + ic(CHAT) + 'AI 답 ' + ai + '</span></div>' +
      '<div class="lw-row">' + (star ? '<a class="lw-btn line" href="#retry/' + lang + (week ? '/week' : '') + '">' + ic(STAR) + star + '문장 다시 풀기</a>' : '') +
      '<button class="lw-btn" type="button" id="mnAsk">' + ic(CHAT) + 'AI에게 물어보기</button></div></section>' +
      '<div class="mn-f"><button type="button" data-w="1" aria-pressed="' + week + '">최근 7일</button><button type="button" data-w="" aria-pressed="' + !week + '">전체</button>' +
      '<select aria-label="언어">' + ls.map(function (l) { return '<option value="' + l + '"' + (l === lang ? ' selected' : '') + '>' + LNAME[l] + '</option>'; }).join('') + '</select></div>' +
      '<section class="mn-card mn-list">' + (rowsHtml || '<p>최근 7일에는 쓴 해석이 없어요. 전체에서 지난 기록을 볼 수 있어요.</p>') + '</section>' +
      '<p class="mn-note">이 기기에만 저장돼요. 기기를 바꾸기 전에 <button type="button" id="mnFile">내보내기</button>로 파일을 받아 두세요.</p>';
    function openAsk(span) {
      span = span && span.from ? span : {};
      if (!M.size(span.from ? { lang: lang, from: span.from, to: span.to } : { lang: lang, week: true }) && !M.size({ lang: lang, star: true })) return M.toast('물어볼 문장이 없어요', '최근 7일에 쓴 해석이나 헷갈림 표시가 있어야 해요.');
      M.askSheet({ lang: lang, from: span.from, to: span.to, saved: function () { list(); } });
    }
    on('#mnAsk', openAsk); on('#mnFile', files);
    [].forEach.call(box.querySelectorAll('[data-w]'), function (b) {
      b.addEventListener('click', function () { week = !!b.dataset.w; list(); var x = q('[data-w="' + b.dataset.w + '"]'); if (x) x.focus(); });
    });
    q('select').addEventListener('change', function (e) { lang = e.target.value; list(); q('select').focus(); });
    h1();
    if (ask) openAsk(ask);
  }
  function row(id, d, t, ai, n, s) {
    return '<a class="mn-li" href="#' + id + '"><span class="d">' + Number(d.slice(5, 7)) + '.' + Number(d.slice(8, 10)) + '<small>' + WD[date(d).getDay()] + '</small></span><span class="t">' + t + '</span>' +
      (ai && ai.length ? '<em>AI 답</em>' : '') + '<span class="n">' + n + (s ? ' ' + ic(STAR, 1) + s : '') + '</span></a>';
  }

  // 내보내기와 가져오기(M26)
  function files() {
    var n = M.size({}), a = M.aiCount({});
    var s = M.open('<h3>내보내기와 가져오기</h3><p>쓴 해석, 헷갈림 표시, 붙인 AI 답을 파일 하나로 옮겨요.</p>' +
      '<button class="mn-opt" type="button" data-x="out"' + (n || a ? '' : ' disabled') + '><b>파일로 내보내기</b><span>지금까지 쓴 것 ' + n + '문장, AI 답 ' + a + '개</span></button>' +
      '<button class="mn-opt" type="button" data-x="in"><b>파일에서 가져오기</b><span>지금 있는 기록에 더해요. 이 기기에 쓴 글은 바뀌지 않아요.</span></button>' +
      '<input type="file" accept=".json,application/json" hidden><p class="lw-err" role="alert" hidden></p><div class="lw-row"><button class="lw-btn line" type="button" data-x="no">닫기</button></div>', '내보내기와 가져오기');
    var inp = s.querySelector('input'), err = s.querySelector('.lw-err');
    function say(t) { err.textContent = t; err.hidden = false; }
    s.querySelector('[data-x=no]').addEventListener('click', M.close);
    s.querySelector('[data-x=out]').addEventListener('click', function () {
      var u = URL.createObjectURL(new Blob([M.dump()], { type: 'application/json' })), l = document.createElement('a');
      l.href = u; l.download = 'dokhaehanip-notes-' + M.ymd(Date.now()) + '.json';
      document.body.appendChild(l); l.click(); l.remove(); setTimeout(function () { URL.revokeObjectURL(u); }, 10000);
      M.ga('notes_export', {});
    });
    s.querySelector('[data-x=in]').addEventListener('click', function () { inp.click(); });
    inp.addEventListener('change', function () {
      var f = inp.files[0]; inp.value = '';
      if (!f) return;
      if (f.size > 6e6) return say('파일이 너무 커요. 노트에서 내보낸 파일인지 확인해 주세요.');
      f.text().then(function (t) {
        var r = M.restore(t);
        if (!r) return say('노트에서 내보낸 파일이 아니에요.');
        if (r.failed) return say('저장 공간이 모자라 가져오지 못했어요. 지금 기록은 그대로예요.');
        M.close(); week = false; route();
        M.toast('가져왔어요', '지문 ' + r.days + '개, AI 답 ' + r.answers + '개를 더했어요.');
      }, function () { say('파일을 읽지 못했어요.'); });
    });
  }

  // 지문 하루(M17, M27)와 묶음 답
  function day(id) {
    var p = id.split('/'), d = M.load()[id], mine = view;
    if (p[1] === '~') {
      box.innerHTML = crumb('#', '내 해석 노트') + '<h1>여러 지문 묶음에 받은 AI 답</h1><section class="mn-card">' + (aiHtml(id) || '<p>붙여 둔 답이 없어요.</p>') + '</section>';
      wireAi(id, function () { day(id); });
      return h1();
    }
    if (!d && !M.loadAi()[id]) { location.replace('#'); return; }
    d = d || { t: md(p[1]) + ' 지문', s: {} };
    var open = {}, allOpen = false;
    function draw(sents, failed) {
      var total = Math.max(sents ? sents.length : 0, d.n || 0, Object.keys(d.s).reduce(function (m, i) { return Math.max(m, Number(i) + 1); }, 0));
      var wrote = Object.keys(d.s).filter(function (i) { return d.s[i].v; }).length, stars = Object.keys(d.s).filter(function (i) { return d.s[i].st; }).length;
      var ai = aiHtml(id);
      box.innerHTML = crumb('#', '내 해석 노트') + '<h1>' + esc(d.t) + '</h1><p class="mn-sub">' + md(p[1]) + ' ' + WD[date(p[1]).getDay()] + '요일, ' + LNAME[p[0]] + ' ' + (p[2] === 'a' ? '기초' : '중급') + ', ' + (total ? total + '문장 중 ' : '') + wrote + '문장</p>' +
        '<section class="mn-card">' + (ai || '<p>AI에게 받은 답을 붙여 두면 다시 풀 때 같이 보여요.</p>') + '<button class="lw-btn line" type="button" id="mnPaste">' + (ai ? '답 더 붙이기' : '받은 답 붙여 두기') + '</button></section>' +
        (sents ? '<button class="mn-tg" type="button" role="switch" id="mnAll" aria-checked="' + allOpen + '">모범 해석 모두 펼치기<i></i></button>' : failed ? '<p class="mn-note">모범 해석을 불러오지 못했어요. 인터넷 연결을 확인한 뒤 다시 열어 주세요.</p>' : '') + '<section class="mn-card" id="mnS"></section>' +
        '<div class="mn-dock">' + (stars ? '<a class="lw-btn line" href="#retry/' + id + '">다시 풀기</a>' : '<a class="lw-btn line" href="/' + p[0] + '/' + p[1] + '/?level=' + p[2] + '">지문 열기</a>') +
        '<button class="lw-btn" type="button" id="mnAsk"' + (wrote || stars ? '' : ' disabled') + '>' + ic(CHAT) + 'AI에게 물어보기</button></div>';
      for (var i = 0; i < total; i++) sentence(i, d.s[i] || { v: '', st: false, e: '' }, sents);
      wireAi(id, function () { day(id); });
      on('#mnPaste', function () { M.pasteSheet({ lang: p[0], id: id, saved: function () { day(id); } }); });
      on('#mnAsk', function () { M.askSheet({ lang: p[0], id: id, saved: function () { day(id); } }); });
      on('#mnAll', function () {
        allOpen = !allOpen; q('#mnAll').setAttribute('aria-checked', String(allOpen));
        [].forEach.call(box.querySelectorAll('.mn-s'), function (el, k) { open[k] = allOpen; setModel(el, allOpen); });
      });
    }
    function setModel(el, o) { var m = el.querySelector('.mn-model'), c = el.querySelector('.mn-cmp'); if (m) { m.hidden = !o; c.setAttribute('aria-expanded', String(o)); c.hidden = o; } }
    function sentence(i, x, sents) {
      var hit = match(sents, i, x.e), el = document.createElement('div');
      el.className = 'mn-s';
      el.innerHTML = '<div class="hd"><b>' + (i + 1) + '</b><span class="e" lang="' + p[0] + '"></span><button class="lw-star" type="button" aria-pressed="' + !!x.st + '" aria-label="' + (i + 1) + '번 문장 헷갈림 표시">' + ic(STAR) + '</button></div>' +
        '<div class="q' + (x.v ? '' : ' none') + '">' + (x.v ? esc(x.v) : '아직 안 씀') + '</div>' + (x.r ? '<div class="q old"><small>' + md(M.ymd(x.r.u)) + '에 다시 쓴 해석</small>' + esc(x.r.v) + '</div>' : '') +
        (hit && hit.ko ? '<button class="mn-cmp" type="button" aria-expanded="false">모범 해석</button><div class="mn-model" hidden><small>모범 해석</small>' + esc(hit.ko) + '</div>' : '');
      putText(el.querySelector('.e'), hit, x.e);
      var st = el.querySelector('.lw-star'), c = el.querySelector('.mn-cmp');
      st.addEventListener('click', function () {
        var now = st.getAttribute('aria-pressed') !== 'true';
        if (!M.edit(id, i, function (s) { s.st = now; if (!s.e && hit) s.e = hit.e; }, { t: d.t, u: d.u, n: d.n || (sents && sents.length) })) return M.toast('저장하지 못했어요', '이 기기의 저장 공간을 확인해 주세요.');
        st.setAttribute('aria-pressed', String(now)); d = M.load()[id] || { t: d.t, u: d.u, n: d.n, s: {} };
        var any = Object.keys(d.s).some(function (k) { return d.s[k].st; }), b = q('.mn-dock a');
        b.textContent = any ? '다시 풀기' : '지문 열기'; b.href = any ? '#retry/' + id : '/' + p[0] + '/' + p[1] + '/?level=' + p[2];
      });
      if (c) c.addEventListener('click', function () { open[i] = true; setModel(el, true); });
      if (open[i]) setModel(el, true);
      q('#mnS').appendChild(el);
    }
    draw(null); h1();
    page(id).then(function (s) { if (view === mine) draw(s); }, function () { if (view === mine) draw(null, true); });
  }

  // 헷갈린 문장 다시 풀기(M19, M20, M31)
  function retry(a) {
    var f = { star: true }, from = '#', id = a.slice(0, 3).join('/');
    if (M.DAYKEY.test(id)) { f.id = id; from = '#' + id; }
    else if (LNAME[a[0]]) { f.lang = a[0]; if (a[1] === 'week') f.week = true; else if (a[2]) { f.from = a[1]; f.to = a[2]; } }
    var items = [];
    M.pick(f).forEach(function (d) { d.list.forEach(function (x) { items.push({ id: d.id, t: d.t, d: d.d, i: x.i, e: x.e, v: x.v, r: x.r }); }); });
    if (!items.length) { location.replace(from); return; }
    run = { items: items, at: 0, known: 0, from: from };
    M.ga('retry_start', { n: items.length });
    write();
  }
  function head(x) {
    var n = run.items.length, k = run.at + 1;
    return crumb(run.from, '그만하기') + '<div class="mn-prog"><b data-focus>헷갈린 문장 다시 풀기</b><span>' + k + ' / ' + n + '</span><i><u style="width:' + k / n * 100 + '%"></u></i></div>' +
      '<section class="mn-card mn-rs"><div class="from">' + md(x.d) + ', ' + esc(x.t) + ', ' + (x.i + 1) + '번 문장</div><div class="big" lang="' + x.id.slice(0, 2) + '"></div>';
  }
  function write() {
    var x = run.items[run.at], mine = view, at = run.at;
    box.innerHTML = head(x) + '<textarea rows="3" maxlength="1000" spellcheck="false" aria-label="다시 쓰는 해석" placeholder="내 말로 적어 보세요"></textarea><p class="hint">지난번 해석과 모범 해석은 다 쓰고 나면 보여요.</p></section>' +
      '<div class="mn-dock"><button class="lw-btn line" type="button" id="mnNo">모르겠어요</button><button class="lw-btn" type="button" id="mnOk" disabled>맞춰 보기</button></div>';
    putText(q('.big'), null, x.e); h1();
    var ta = q('textarea'), ok = q('#mnOk');
    ta.addEventListener('input', function () { ok.disabled = !ta.value.trim(); });
    ta.addEventListener('keydown', function (e) { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing && e.keyCode !== 229) { e.preventDefault(); if (!ok.disabled) ok.click(); } });
    ok.addEventListener('click', function () { check(ta.value.trim()); });
    on('#mnNo', function () { check(''); });
    page(x.id).then(function (s) {
      x.hit = match(s, x.i, x.e);
      if (view === mine && run && run.at === at) { if (x.hit) putText(q('.big'), x.hit); if (x.late) x.late(); }
    }, function () { x.failed = true; if (view === mine && run && run.at === at && x.late) x.late(); });
  }
  function check(v) {
    var x = run.items[run.at], old = x.r ? { v: x.r.v, t: md(M.ymd(x.r.u)) + '에 다시 쓴 해석' } : x.v ? { v: x.v, t: md(x.d) + ' 지문에 쓴 해석' } : null;
    var ai = (M.loadAi()[x.id] || []).map(function (a) { return part(a.v, x.i + 1); }).filter(Boolean)[0];
    box.innerHTML = head(x) + '<small>지금 쓴 해석</small><div class="q' + (v ? '' : ' none') + '">' + (v ? esc(v) : '모르겠어요') + '</div>' +
      (old ? '<small>' + old.t + '</small><div class="q old">' + esc(old.v) + '</div>' : '') + '<div class="mn-model"><small>모범 해석</small><span id="mnKo"></span></div>' +
      (ai ? '<div class="mn-ai"><div class="h">' + ic(CHAT) + '붙여 둔 AI 답</div><div class="t">' + esc(ai) + '</div></div>' : aiHtml(x.id)) + '</section>' +
      '<div class="mn-dock"><button class="lw-btn line" type="button" id="mnStill">' + ic(STAR, 1) + '아직 헷갈려요</button><button class="lw-btn" type="button" id="mnKnow">이제 알아요</button></div>';
    x.late = function () {
      putText(q('.big'), x.hit, x.e);
      q('#mnKo').textContent = x.hit && x.hit.ko ? x.hit.ko : x.hit !== undefined || x.failed ? '모범 해석을 불러오지 못했어요.' : '불러오는 중이에요.';
    };
    if (!ai) wireAi(x.id, function () { check(v); });
    x.late(); h1();
    function next(know) {
      var ok = M.edit(x.id, x.i, function (s) { if (v) s.r = { v: v, u: Date.now() }; s.st = !know; if (!s.e) s.e = x.e; }, { t: x.t });
      if (!ok) return M.toast('저장하지 못했어요', '이 기기의 저장 공간을 확인해 주세요.');
      if (know) run.known++;
      if (++run.at < run.items.length) return write();
      var n = run.items.length, k = run.known;
      M.ga('retry_done', { n: n, known: k });
      box.innerHTML = crumb(run.from, '내 해석 노트') + '<section class="mn-card mn-empty">' + ic('M5 12.5l4.5 4.5L19 7') + '<b data-focus>' + n + '문장을 다시 풀었어요</b><p>이제 알아요 ' + k + '문장, 아직 헷갈려요 ' + (n - k) + '문장</p><a class="lw-btn" href="' + run.from + '">노트로 돌아가기</a></section>';
      run = null; h1();
    }
    on('#mnStill', function () { next(false); });
    on('#mnKnow', function () { next(true); });
  }

  function route() {
    var h = location.hash.slice(1), a = h.split('/');
    view++; run = null; M.close();
    if (a[0] === 'retry') return retry(a.slice(1));
    if (M.AIKEY.test(h)) { lang = a[0]; return day(h); }
    if (a[0] === 'ask' && LNAME[a[1]]) { lang = a[1]; history.replaceState(null, '', location.pathname); return list(YMD.test(a[2]) && YMD.test(a[3]) ? { from: a[2], to: a[3] } : {}); }
    list();
  }
  window.addEventListener('hashchange', route);
  route();
  M.ga('notes_open', {});
})();
