"""지문 페이지 구역 도달 측정(이슈 #24, 문법 섹션 0단계): 체크 포인트를 실제로 읽는지 GA 로 잰다.

- section_view: 지문, 단어, 체크 포인트, 학습 가이드, 구독 카드가 화면에 충분히 보이면 페이지마다 한 번씩
- points_read: 체크 포인트 카드가 화면에 모두 합쳐 8초 넘게 보이면 한 번
화면은 바꾸지 않는다. patch_page 에서 apply() 로 넣고, 여러 번 돌려도 같다.
"""
import re

SCRIPT = """<script id="track-js">
(function () {
  if (!('IntersectionObserver' in window)) return;
  var p = location.pathname.split('/'), base = { lang: p[1] || '', day: p[2] || '' };
  function ga(name, extra) {
    var o = {}, k;
    for (k in base) o[k] = base[k];
    for (k in extra) o[k] = extra[k];
    try { if (typeof gtag === 'function') gtag('event', name, o); } catch (e) {}
  }
  function card(sel) { var e = document.querySelector(sel); return e && (e.closest('.card') || e); }
  var parts = [['passage', '#passage'], ['words', '#step-words'], ['points', '#step-points'], ['guide', '.card.guide'], ['subscribe', '#subscribe']];
  var seen = {}, pts = card('#step-points'), ms = 0, since = 0, read = false, inView = false;
  // 긴 카드는 절반이 한 화면에 안 들어오므로, 카드 절반과 화면 40% 중 작은 쪽만큼 보이면 본 것으로 친다
  function enough(en) { return en.isIntersecting && en.intersectionRect.height >= Math.min(en.boundingClientRect.height * 0.5, innerHeight * 0.4); }
  // 체크 포인트가 보이는 동안의 시간을 더한다. 다른 탭으로 가 있는 동안은 세지 않는다
  function tick() {
    var now = Date.now();
    if (since) ms += now - since;
    since = inView && !document.hidden ? now : 0;
    if (!read && ms >= 8000) { read = true; ga('points_read', {}); }
  }
  var io = new IntersectionObserver(function (list) {
    list.forEach(function (en) {
      var name = en.target.getAttribute('data-track');
      if (enough(en) && !seen[name]) { seen[name] = 1; ga('section_view', { section: name }); }
      if (en.target === pts) { inView = enough(en); tick(); }
    });
  }, { threshold: [0, 0.1, 0.25, 0.5, 0.75, 1] });
  parts.forEach(function (x) { var e = card(x[1]); if (e) { e.setAttribute('data-track', x[0]); io.observe(e); } });
  setInterval(function () { if (since) tick(); }, 1000);
  document.addEventListener('visibilitychange', tick);
})();
</script>
"""

_JS_RE = re.compile(r'<script id="track-js">.*?</script>\n', re.S)


def apply(page):
    """지문 페이지(#passage 가 있는 페이지)의 </body> 앞에 측정 스크립트를 넣는다. 예전 것은 지우고 다시 넣는다."""
    if 'id="passage"' not in page:
        return page
    page = _JS_RE.sub("", page)
    return page.replace("</body>", SCRIPT + "</body>", 1)
