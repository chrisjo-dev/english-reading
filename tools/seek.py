"""재생바 이동(이슈 #26, 시안 design/player-seek S02, S03): 재생바를 끌거나 눌러 듣고 싶은 곳으로 옮긴다.

음성은 문장별 파일이고 전체 듣기 진행률은 문장을 같은 폭으로 나눈다. 그래서 위치에서 문장과
그 문장 안 비율을 구해 해당 파일로 간 뒤 이어서 재생한다. 끄는 동안은 화면만 움직이고 놓을 때 옮긴다.
템플릿은 그대로 두고 patch_page 에서 apply() 로 넣는다. 새 페이지와 지난 페이지가 같은 길로 지나가고,
여러 번 돌려도 같다.
"""
import re

CSS = """  /* seek-css */
  .pbar .seek { position: relative; height: 18px; margin-top: 2px; display: flex; align-items: center; cursor: pointer; touch-action: none; user-select: none; -webkit-user-select: none; -webkit-tap-highlight-color: transparent; outline: 0; }
  .pbar .seek::before { content: ''; position: absolute; left: 0; right: 0; top: -13px; bottom: -13px; }
  .pbar .seek-track { position: relative; width: 100%; height: 6px; border-radius: 3px; background: var(--bg); }
  .pbar .seek-track i { position: absolute; left: 0; top: 0; bottom: 0; width: 0; background: var(--blue); border-radius: 3px; transition: width .25s linear; }
  .pbar .seek-tick { position: absolute; top: 0; bottom: 0; width: 2px; margin-left: -1px; background: #fff; }
  .pbar .seek-knob { position: absolute; top: 50%; left: 0; width: 14px; height: 14px; margin: -7px 0 0 -7px; border-radius: 50%; background: var(--blue); border: 2px solid #fff; box-sizing: border-box; box-shadow: 0 1px 4px rgba(16,24,40,.3); transition: left .25s linear; }
  .pbar .seek-tip { position: absolute; left: 0; bottom: 26px; transform: translateX(-50%); display: none; background: var(--ink); color: #fff; font-size: 12px; font-weight: 700; padding: 5px 9px; border-radius: 8px; white-space: nowrap; pointer-events: none; }
  .pbar .seek:focus-visible .seek-knob { outline: 2px solid var(--blue); outline-offset: 2px; }
  .pbar .seek:not(.is-full) .seek-tick { display: none; }
  .pbar .seek.drag .seek-track i, .pbar .seek.drag .seek-knob { transition: none; }
  .pbar .seek.drag .seek-knob { width: 20px; height: 20px; margin: -10px 0 0 -10px; }
  .pbar .seek.is-full.drag .seek-tip { display: block; }
  .pbar .seek.is-off { pointer-events: none; cursor: default; }
  .pbar .seek.is-off .seek-knob { display: none; }
  /* /seek-css */
"""

MARKUP = (
    '<div class="seek" id="pbar-seek" role="slider" tabindex="0" aria-label="재생 위치" aria-valuemin="0"'
    ' aria-valuemax="100" aria-valuenow="0"><div class="seek-track" id="pbar-track"><i id="pbar-prog"></i>'
    '<b class="seek-knob" id="pbar-knob"></b></div><span class="seek-tip" id="pbar-tip" aria-hidden="true"></span>'
    '</div><!-- /seek -->'
)

JS = """  // seek-js
  var _seekI = 0, _seekOn = false, _seekDrag = false, _seekPos = 0, _seekFrom = 0;
  var seekEl = document.getElementById('pbar-seek'), seekTrack = document.getElementById('pbar-track');
  var seekKnob = document.getElementById('pbar-knob'), seekTip = document.getElementById('pbar-tip');
  rows.forEach(function (_, i) {
    if (!i) return;
    var tick = document.createElement('span');
    tick.className = 'seek-tick'; tick.style.left = (i / rows.length * 100) + '%';
    seekTrack.appendChild(tick);
  });
  function seekFull() { return _playMode === 'full' && rows.length > 0; }
  // 문장 경계 값이 부동소수 오차로 앞 문장이 되지 않게 조금 더해 내린다
  function seekSentence(pos) { return Math.min(rows.length - 1, Math.floor(pos * rows.length + 1e-6)); }
  function seekLabel(k) { pbarLabel.textContent = '전체 듣기 ' + (k + 1) + '/' + rows.length; }
  function seekShow(pos) {
    _seekPos = Math.min(1, Math.max(0, pos));
    var pct = (_seekPos * 100).toFixed(2) + '%';
    pbarProg.style.width = pct; seekKnob.style.left = pct;
    seekEl.setAttribute('aria-valuenow', String(Math.round(_seekPos * 100)));
    seekEl.setAttribute('aria-valuetext', seekFull()
      ? (seekSentence(_seekPos) + 1) + '번째 문장, 전체 ' + rows.length + '문장'
      : Math.round(_seekPos * 100) + '퍼센트');
  }
  function seekMode() {
    seekEl.classList.toggle('is-full', _playMode === 'full');
    seekEl.classList.toggle('is-off', _playMode === 'word');
    seekEl.setAttribute('tabindex', _playMode === 'word' ? '-1' : '0');
    if (_playMode === 'word') seekShow(0);
  }
  function seekGo(pos) {
    var full = seekFull(), k = full ? seekSentence(pos) : _seekI;
    var f = Math.min(0.98, Math.max(0, full ? pos * rows.length - k : pos));
    var play = _seekOn || !player.paused, src = isLevelA() ? (AUDIO_A[k] || null) : (AUDIO[k] || null);
    token++; var t = token;
    player.pause(); if (canSpeak) speechSynthesis.cancel();
    queue = full ? rows.map(function (_, i) { return i; }).slice(k + 1) : [];
    _fullI = k; _seekI = k; mark(k);
    if (full) seekLabel(k);
    seekShow(full ? (k + f) / rows.length : f);
    gaEvent('audio_seek', { lang: _gaLang, day: _gaDay });
    if (!src) {  // 내장 음성은 시간 이동이 안 되어 그 문장 처음부터 읽는다
      if (canSpeak) { queue.unshift(k); pbarSetPlaying(true); next(); } else stop();
      return;
    }
    function after() { if (t === token) setTimeout(function () { if (t === token) next(); }, queue.length ? 450 : 0); }
    function land() {
      if (t !== token) return;
      var d = player.duration;
      if (d && isFinite(d)) player.currentTime = d * f;
      if (play) player.play().catch(function () { if (t === token) stop(); });
    }
    player.onended = after;
    if (player.readyState >= 1 && player.src === new URL(src, location.href).href) { land(); return; }
    player.addEventListener('loadedmetadata', land, { once: true });
    player.src = src; player.playbackRate = rate;
  }
  function seekMove(e) {
    var r = seekTrack.getBoundingClientRect(), pos = Math.min(1, Math.max(0, (e.clientX - r.left) / r.width));
    seekShow(pos);
    if (seekFull()) {
      var k = seekSentence(pos);
      seekLabel(k); seekTip.textContent = (k + 1) + '번째 문장';
      seekTip.style.left = Math.min(r.width - 34, Math.max(34, pos * r.width)) + 'px';
    }
  }
  function seekEnd(go) {
    if (!_seekDrag) return;
    _seekDrag = false; seekEl.classList.remove('drag');
    if (go) { seekGo(_seekPos); return; }
    if (seekFull()) seekLabel(_fullI);
    seekShow(_seekFrom);
  }
  seekEl.addEventListener('pointerdown', function (e) {
    if (e.button) return;
    e.preventDefault(); seekEl.setPointerCapture(e.pointerId);
    _seekFrom = _seekPos; _seekDrag = true; seekEl.classList.add('drag'); seekMove(e);
  });
  seekEl.addEventListener('pointermove', function (e) { if (_seekDrag) seekMove(e); });
  seekEl.addEventListener('pointerup', function () { seekEnd(true); });
  seekEl.addEventListener('pointercancel', function () { seekEnd(false); });
  seekEl.addEventListener('keydown', function (e) {
    if (_playMode === 'word') return;
    var full = seekFull(), n = rows.length, k = full ? seekSentence(_seekPos) : 0;
    var d = player.duration, step = d && isFinite(d) ? 5 / d : 0.1, to = null;
    // 전체 듣기는 문장 단위, 문장 하나 듣기는 5초 단위. 왼쪽은 문장 앞쪽 1.5초가 지났으면 그 문장 처음으로
    var into = full && d && isFinite(d) ? (_seekPos * n - k) * d : 0;
    if (e.key === 'ArrowRight' || e.key === 'ArrowUp') to = full ? (k + 1 < n ? (k + 1) / n : null) : _seekPos + step;
    else if (e.key === 'ArrowLeft' || e.key === 'ArrowDown') to = full ? (into > 1.5 ? k : Math.max(0, k - 1)) / n : _seekPos - step;
    else if (e.key === 'Home') to = 0;
    else if (e.key === 'End') to = full ? (n - 1) / n : 1;
    else return;
    e.preventDefault();
    if (to !== null) seekGo(Math.min(1, Math.max(0, to)));
  });
  player.addEventListener('timeupdate', function () {
    var d = player.duration;
    if (_seekDrag || !d || !isFinite(d)) return;
    var r = player.currentTime / d;
    seekShow(seekFull() ? (_fullI + r) / rows.length : r);
  });
  player.addEventListener('ended', function () {
    if (!_seekDrag) seekShow(seekFull() && queue.length ? (_fullI + 1) / rows.length : 0);
  });
  // /seek-js
"""

# 옛 재생 스크립트 가운데 바꿀 곳. (옛 문구, 새 문구)
HOOKS = (
    ("var i = queue.shift(), t = token; mark(i);",
     "var i = queue.shift(), t = token; mark(i); _seekI = i; if (!_seekDrag) seekShow(_playMode === 'full' ? i / rows.length : 0);"),
    ("pbar.classList.add('vis'); document.body.classList.add('pbar-vis');",
     "pbar.classList.add('vis'); document.body.classList.add('pbar-vis'); seekMode();"),
    ("pbarPP.innerHTML = playing ? ICON_PAUSE : ICON_PLAY;",
     "pbarPP.innerHTML = playing ? ICON_PAUSE : ICON_PLAY; _seekOn = !!playing;"),
)

_OLD_MARKUP = '<div class="prog"><i id="pbar-prog"></i></div>'
_OLD_CSS = re.compile(r"  \.pbar \.prog \{[^\n]*\n  \.pbar \.prog i \{[^\n]*\n")
_OLD_JS = re.compile(r"  player\.addEventListener\('timeupdate', function \(\) \{\n.*?"
                     r"  player\.addEventListener\('ended', function \(\) \{ pbarProg\.style\.width = '0%'; \}\);\n", re.S)
_CSS_RE = re.compile(r"  /\* seek-css \*/\n.*?  /\* /seek-css \*/\n", re.S)
_JS_RE = re.compile(r"  // seek-js\n.*?  // /seek-js\n", re.S)
_MARKUP_RE = re.compile(r'<div class="seek" id="pbar-seek".*?<!-- /seek -->', re.S)


def apply(page):
    """재생바가 있는 지문 페이지에 이동 기능을 넣는다. 이미 있으면 지금 내용으로 바꾼다."""
    if 'id="pbar-prog"' not in page:
        return page
    page = _MARKUP_RE.sub(lambda m: MARKUP, page, count=1).replace(_OLD_MARKUP, MARKUP, 1)
    for pat in (_CSS_RE, _OLD_CSS):
        page = pat.sub(lambda m: CSS, page, count=1)
    for pat in (_JS_RE, _OLD_JS):
        page = pat.sub(lambda m: JS, page, count=1)
    for old, new in HOOKS:
        if new not in page:
            page = page.replace(old, new, 1)
    return page
