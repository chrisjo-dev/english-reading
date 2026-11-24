// 문장마다 내 해석 쓰기(시안 design/mine-notes M11~M14, M21, M24, M25). 쓴 글은 이 기기에만 남는다.
// 지문 페이지 인라인 스크립트의 rows, sentenceText, isLevelA, gaEvent 와 assets/mine.js(기록, 물어보기 시트)를 쓴다.
(function () {
  var M = window.mineNotes, ON = 'mine:on', root = document.documentElement;
  var dock = document.getElementById('lw-dock'), sw = document.getElementById('lw-sw');
  if (!M || !dock || !sw || typeof rows === 'undefined') return;
  var tas = rows.map(function (r) { return r.querySelector('.lw textarea'); });
  var stars = rows.map(function (r) { return r.querySelector('.lw-star'); });
  var cmps = rows.map(function (r) { return r.querySelector('.lw-cmp'); });
  var path = location.pathname.split('/'), lang = path[1], day = path[2];
  var topic = document.querySelector('h1 em').textContent;
  var id, timer = 0, dirty = false, started = false, state = '', ens = [], chV = {}, chS = {};
  var $ = function (x) { return document.getElementById(x); };
  var hintEl = $('hinttext'), hint0 = hintEl ? hintEl.textContent : '';

  function pos() { return isLevelA() ? 'a' : 'b'; }
  function has(i) { return !!tas[i].value.trim(); }
  function count() { return tas.filter(function (_, i) { return has(i); }).length; }
  function grow(t) { t.style.height = 'auto'; t.style.height = (t.scrollHeight + 2) + 'px'; }
  // 다른 탭이나 노트에서 고친 것을 지우지 않게, 저장할 때마다 새로 읽어 이 탭에서 바꾼 글과 별표만 얹는다
  function save() {
    clearTimeout(timer); timer = 0;
    if (!dirty) return;
    var d = M.load()[id], s = (d && d.s) || {};
    function at(i) { return s[i] || (s[i] = { v: '', st: false, e: ens[i] }); }
    Object.keys(chV).forEach(function (i) { var x = at(i); x.v = tas[i].value.trim(); x.e = ens[i]; });
    Object.keys(chS).forEach(function (i) { at(i).st = stars[i].getAttribute('aria-pressed') === 'true'; });
    if (M.put(id, { t: topic, u: Date.now(), m: d && d.m, n: rows.length, s: s })) { dirty = false; chV = {}; chS = {}; state = 'ok'; }
    else state = 'bad';
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
    ens = rows.map(sentenceText);  // 수준을 바꾼 뒤 저장돼도 쓸 때의 원문이 남게 미리 담아 둔다
    var d = M.load()[id], s = (d && d.s) || {};
    tas.forEach(function (t, i) {
      t.value = (s[i] && s[i].v) || '';
      stars[i].setAttribute('aria-pressed', String(!!(s[i] && s[i].st)));
      grow(t);
    });
    dirty = false; chV = {}; chS = {}; state = d ? 'ok' : ''; paint();
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
      grow(t); chV[i] = 1; touch();
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
      stars[i].setAttribute('aria-pressed', String(stars[i].getAttribute('aria-pressed') !== 'true')); chS[i] = 1; touch();
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

  // 노트나 다른 탭에서 고친 것을 받는다(쓰는 중이면 그대로 둔다)
  function refill() { if (!dirty && tas.indexOf(document.activeElement) < 0) fill(); }
  window.addEventListener('storage', function (e) { if (e.key === 'mine:v1') refill(); });
  window.addEventListener('pageshow', function (e) { if (e.persisted) refill(); });

  $('lw-ask').addEventListener('click', function () {
    save();
    if (!count() && !M.size({ lang: lang, week: true }) && !M.size({ lang: lang, star: true })) return go(0);
    M.askSheet({ lang: lang, id: id });
  });

  setOn(!root.classList.contains('lw-off'));
  fill();
})();
