// 문장마다 내 해석 쓰기(시안 design/mine-notes M11~M14, M21, M24, M25). 쓴 글은 이 기기에만 남는다.
// 지문 페이지 인라인 스크립트의 rows, sentenceText, isLevelA, HEAD, WEAK, gaEvent 를 쓴다.
(function () {
  var KEY = 'mine:v1', ON = 'mine:on', root = document.documentElement;
  var dock = document.getElementById('lw-dock'), sw = document.getElementById('lw-sw');
  if (!dock || !sw || typeof rows === 'undefined') return;
  var tas = rows.map(function (r) { return r.querySelector('.lw textarea'); });
  var stars = rows.map(function (r) { return r.querySelector('.lw-star'); });
  var cmps = rows.map(function (r) { return r.querySelector('.lw-cmp'); });
  var path = location.pathname.split('/'), lang = path[1], day = path[2];
  var topic = document.querySelector('h1 em').textContent;
  var id, timer = 0, dirty = false, started = false, state = '';
  var $ = function (x) { return document.getElementById(x); };
  var hintEl = $('hinttext'), hint0 = hintEl ? hintEl.textContent : '';

  function esc(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;'); }
  function load() { try { return JSON.parse(localStorage.getItem(KEY)) || {}; } catch (e) { return {}; } }
  function pos() { return isLevelA() ? 'a' : 'b'; }
  function has(i) { return !!tas[i].value.trim(); }
  function count() { return tas.filter(function (_, i) { return has(i); }).length; }
  function grow(t) { t.style.height = 'auto'; t.style.height = (t.scrollHeight + 2) + 'px'; }
  function current() {
    var s = {};
    tas.forEach(function (t, i) {
      var v = t.value.trim(), st = stars[i].getAttribute('aria-pressed') === 'true';
      if (v || st) s[i] = { v: v, st: st, e: sentenceText(rows[i]) };
    });
    return s;
  }
  // 다른 탭이 쓴 다른 날 기록을 지우지 않게, 저장할 때마다 새로 읽어 이 지문 것만 바꾼다
  function save() {
    clearTimeout(timer); timer = 0;
    if (!dirty) return;
    try {
      var all = load(), s = current();
      if (Object.keys(s).length) all[id] = { t: topic, u: Date.now(), s: s }; else delete all[id];
      localStorage.setItem(KEY, JSON.stringify(all));
      dirty = false; state = 'ok';
    } catch (e) { state = 'bad'; }
    paint();
  }
  function touch() { dirty = true; clearTimeout(timer); timer = setTimeout(save, 300); paint(); }
  function paint() {
    var n = count(), st = $('lw-st');
    $('lw-n').textContent = rows.length + '문장 중 ' + n + '문장';
    st.className = state;
    st.textContent = state === 'bad' ? '저장하지 못했어요' : dirty ? '저장하는 중' : state === 'ok' ? '이 기기에 저장됨' : '쓰면 이 기기에 저장돼요';
    cmps.forEach(function (c, i) { c.hidden = !has(i); });
    var left = rows.length - n;
    accN.textContent = left ? left + '문장 남음' : '다 썼어요';
  }
  function fill() {
    id = lang + '/' + day + '/' + pos();
    var d = load()[id], s = (d && d.s) || {};
    tas.forEach(function (t, i) {
      t.value = (s[i] && s[i].v) || '';
      stars[i].setAttribute('aria-pressed', String(!!(s[i] && s[i].st)));
      grow(t);
    });
    dirty = false; state = d ? 'ok' : ''; paint();
  }
  function setOn(on, keep) {
    root.classList.toggle('lw-off', !on); sw.setAttribute('aria-checked', String(on));
    if (hintEl) hintEl.textContent = on ? '번호를 누르면 그 문장이 들려요. 문장 아래에 해석을 쓰면 모범 해석과 맞춰 볼 수 있어요.' : hint0;
    if (keep) { try { localStorage.setItem(ON, on ? '1' : '0'); } catch (e) {} }
    if (on) tas.forEach(grow);
  }

  // 키보드 위에 붙는 줄(M12)
  var acc = document.createElement('div'); acc.className = 'lw-acc';
  acc.innerHTML = '<button class="lw-btn line" type="button">이전</button><span></span><button class="lw-btn" type="button">다음 문장</button>';
  document.body.appendChild(acc);
  var accN = acc.querySelector('span'), accB = acc.querySelectorAll('button'), at = -1;
  var coarse = window.matchMedia && matchMedia('(pointer: coarse)').matches, vv = window.visualViewport;
  function place() { if (vv) acc.style.bottom = Math.max(0, window.innerHeight - vv.offsetTop - vv.height) + 'px'; }
  if (vv) { vv.addEventListener('resize', place); vv.addEventListener('scroll', place); }
  function go(i) { if (i >= 0 && i < tas.length) { tas[i].focus({ preventScroll: true }); tas[i].scrollIntoView({ block: 'nearest' }); } else if (tas[at]) tas[at].blur(); }
  acc.addEventListener('pointerdown', function (e) { e.preventDefault(); });  // 누르는 동안 글자판이 닫히지 않게
  accB[0].addEventListener('click', function () { go(at - 1); });
  accB[1].addEventListener('click', function () { go(at + 1); });

  tas.forEach(function (t, i) {
    t.addEventListener('input', function () {
      grow(t); touch();
      if (!started) { started = true; gaEvent('line_write', { lang: lang, day: day }); }
    });
    t.addEventListener('focus', function () {
      at = i; accB[0].disabled = i === 0; accB[1].textContent = i === tas.length - 1 ? '완료' : '다음 문장';
      if (coarse) { document.body.classList.add('lw-typing'); place(); }
    });
    t.addEventListener('blur', function () { document.body.classList.remove('lw-typing'); save(); });
    t.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey && !e.isComposing && e.keyCode !== 229) { e.preventDefault(); go(i + 1); }
    });
    stars[i].addEventListener('click', function () {
      stars[i].setAttribute('aria-pressed', String(stars[i].getAttribute('aria-pressed') !== 'true')); touch();
    });
    cmps[i].addEventListener('click', function () {
      var k = rows[i].querySelector(isLevelA() && rows[i].querySelector('.ko-a') ? '.ko-a' : '.ko');
      if (k) k.hidden = false;
      gaEvent('line_compare', { lang: lang, day: day });
    });
  });
  // 쓰기를 켠 동안 아직 안 쓴 문장을 누르면 해석을 여는 대신 쓰는 칸으로 간다(이미 열린 해석은 닫을 수 있다)
  $('passage').addEventListener('click', function (e) {
    if (root.classList.contains('lw-off') || String(getSelection())) return;
    var el = e.target.closest('.en, .en-a, .chunks, .chunks-a'), r = el && el.closest('.sent'), i = rows.indexOf(r);
    if (i < 0 || has(i)) return;
    var k = r.querySelector(isLevelA() && r.querySelector('.ko-a') ? '.ko-a' : '.ko');
    if (k && !k.hidden) return;
    e.stopPropagation(); go(i);
  }, true);
  sw.addEventListener('click', function () { save(); setOn(root.classList.contains('lw-off'), true); });
  // 학습 방법은 쓰는 칸을 비추므로 잠시 켠다(저장한 설정은 그대로)
  if ($('howto')) $('howto').addEventListener('click', function () { setOn(true); }, true);
  window.addEventListener('pagehide', save);
  document.addEventListener('visibilitychange', function () { if (document.hidden) save(); });
  new MutationObserver(function () {
    if (id !== lang + '/' + day + '/' + pos()) { save(); fill(); }  // 기초/중급을 바꾸면 그 수준에 쓴 글로
  }).observe(root, { attributes: true, attributeFilter: ['class'] });

  // AI 에게 물어보기(M13, M14, M21)
  var ASK = {
    fix: ['문장별로 고쳐 받기', '잘 잡은 것, 틀린 부분과 이유, 더 자연스러운 해석', '내 해석을 문장 번호별로 원문과 대조해 피드백해 주세요.\n1) 잘 잡은 것: 한두 줄, 사실만.\n2) 짚을 것: 틀렸거나 놓친 부분, 올바른 해석, 이유를 번호로 정리.\n3) 오늘 하나만 가져간다면: 핵심 패턴 하나.'],
    habit: ['반복되는 실수 찾기', '자주 틀리는 습관 3가지와 예시, 다음에 연습할 것', '내 해석을 원문과 대조해 반복되는 실수 습관을 최대 3가지 찾아 주세요. 습관마다 내 해석에서 예시를 들고, 다음에 무엇을 연습하면 좋을지 알려 주세요. 근거가 부족하면 억지로 채우지 마세요.'],
    quiz: ['복습 문제 받기', '내가 틀린 부분으로 짧은 해석 문제 5개', '내 해석에서 틀렸거나 어색한 부분을 먼저 짧게 짚고, 그 부분을 연습할 짧은 해석 문제 5개를 같은 난이도로 내 주세요. 정답은 내가 답한 뒤에 알려 주세요.']
  };
  // 범위마다 [{t, d, list:[{n, e, v, st}]}]
  function pick(range) {
    var all = load(), out = [], since = Date.now() - 7 * 864e5;
    Object.keys(all).sort().forEach(function (k) {
      var d = all[k], p = k.split('/');
      if (!d || !d.s || p[0] !== lang || (range === 'today' && k !== id) || (range === 'week' && !(d.u >= since))) return;
      var list = Object.keys(d.s).map(Number).sort(function (a, b) { return a - b; }).map(function (i) {
        return { n: i + 1, e: d.s[i].e, v: d.s[i].v, st: d.s[i].st };
      }).filter(function (x) { return range === 'star' ? x.st : x.v; });
      if (list.length) out.push({ t: d.t, d: p[1], list: list });
    });
    return out;
  }
  function size(range) { return pick(range).reduce(function (n, d) { return n + d.list.length; }, 0); }
  function compose(range, ask) {
    var who = HEAD.split('입니다.')[0] + '입니다.';
    var body = pick(range).map(function (d) {
      return '[지문] ' + d.t + ' (' + d.d + ')\n\n' + d.list.map(function (x) {
        return x.n + '. ' + x.e + '\n내 해석: ' + (x.v || '(아직 못 씀)') + (x.st ? ' (헷갈림)' : '');
      }).join('\n\n');
    }).join('\n\n');
    return [who + ' 아래는 읽은 문장과 내가 쓴 해석입니다.', body,
      '[요청]\n' + ASK[ask][2] + '\n' + WEAK + '\n칭찬은 과하지 않게, 한국어 존댓말로 답해 주세요.'].join('\n\n');
  }
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
  }
  document.addEventListener('keydown', function (e) {
    if (!sheet) return;
    if (e.key === 'Escape') return close();
    if (e.key !== 'Tab') return;
    var f = [].slice.call(sheet.querySelectorAll('button, input:not(:disabled), textarea')), a = document.activeElement;
    if (e.shiftKey && (a === f[0] || a === sheet)) { e.preventDefault(); f[f.length - 1].focus(); }
    else if (!e.shiftKey && a === f[f.length - 1]) { e.preventDefault(); f[0].focus(); }
  });
  var sel = { range: 'today', ask: 'fix' };
  function askSheet() {
    save();
    var n = { today: size('today'), week: size('week'), star: size('star') };
    if (!n[sel.range]) sel.range = n.today ? 'today' : n.week ? 'week' : 'star';
    function seg(k, t) {
      return '<label><input type="radio" name="lw-r" value="' + k + '"' + (sel.range === k ? ' checked' : '') + (n[k] ? '' : ' disabled') + '>' + t + '<small>' + n[k] + '문장</small></label>';
    }
    open('<h3>AI에게 물어보기</h3><p>원문과 내 해석을 질문과 함께 복사해요. 평소 쓰는 AI 채팅에 붙여 넣으면 돼요.</p>' +
      '<fieldset><legend>범위</legend><div class="lw-seg">' + seg('today', '이 지문') + seg('week', '최근 7일') + seg('star', '헷갈림') + '</div></fieldset>' +
      '<fieldset><legend>무엇을 물어볼까요</legend>' + Object.keys(ASK).map(function (k) {
        return '<label class="lw-rad"><input type="radio" name="lw-a" value="' + k + '"' + (sel.ask === k ? ' checked' : '') + '><span><b>' + ASK[k][0] + '</b><span>' + ASK[k][1] + '</span></span></label>';
      }).join('') + '</fieldset><p>안 쓴 문장은 빼고 보내요. 헷갈림은 안 쓴 문장도 보내요.</p>' +
      '<div class="lw-row"><button class="lw-btn line" type="button" data-x="view">미리 보기</button><button class="lw-btn" type="button" data-x="copy">복사하기</button></div>', 'AI에게 물어보기');
    sheet.addEventListener('change', function (e) { sel[e.target.name === 'lw-r' ? 'range' : 'ask'] = e.target.value; });
    sheet.querySelector('[data-x=view]').addEventListener('click', function () { textSheet(false); });
    sheet.querySelector('[data-x=copy]').addEventListener('click', copy);
  }
  function textSheet(failed) {
    var title = failed ? '자동 복사가 안 됐어요' : '미리 보기';
    open('<h3>' + title + '</h3><p>' + (failed ? '브라우저가 복사를 막았어요. 아래 글을 길게 눌러 전체 선택한 뒤 복사해 주세요.' : '이대로 복사돼요.') + '</p>' +
      '<textarea class="lw-area" readonly aria-label="복사할 글">' + esc(compose(sel.range, sel.ask)) + '</textarea>' +
      '<div class="lw-row"><button class="lw-btn line" type="button" data-x="back">' + (failed ? '닫기' : '뒤로') + '</button><button class="lw-btn" type="button" data-x="copy">' + (failed ? '다시 시도' : '복사하기') + '</button></div>', title);
    if (failed) { var a = sheet.querySelector('textarea'); a.focus(); a.select(); }
    sheet.querySelector('[data-x=back]').addEventListener('click', failed ? close : askSheet);
    sheet.querySelector('[data-x=copy]').addEventListener('click', copy);
  }
  function copy() {
    var text = compose(sel.range, sel.ask);
    function done() {
      gaEvent('feedback_copy', { lang: lang, day: day, range: sel.range, ask: sel.ask });
      close();
      var t = document.createElement('div'); t.className = 'lw-toast'; t.setAttribute('role', 'status');
      t.innerHTML = '<b>복사했어요</b>평소 쓰는 AI 채팅에 붙여 넣으세요.';
      document.body.appendChild(t); setTimeout(function () { t.remove(); }, 3500);
    }
    function old() {
      var ta = document.createElement('textarea'), ok = false;
      ta.value = text; ta.readOnly = true; ta.style.cssText = 'position:fixed;top:0;left:0;opacity:0';
      (sheet || document.body).appendChild(ta); ta.select();
      try { ok = document.execCommand('copy'); } catch (e) {}
      ta.remove();
      if (ok) done(); else textSheet(true);
    }
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done, old); else old();
  }
  $('lw-ask').addEventListener('click', function () {
    save();
    if (!count() && !size('week') && !size('star')) return go(0);
    askSheet();
  });

  setOn(!root.classList.contains('lw-off'));
  fill();
})();
