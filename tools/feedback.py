"""의견 보내기(이슈 #21, 시안 design/feedback-links F01, F02): 하단 링크 바로 위의 '기능 건의', '버그 제보' 메일 버튼.

독해한입은 무료라 운영자 메일로 바로 받는다. 버튼은 메일 앱을 열고 제목과 본문 양식을 미리 채운다.
JS 가 없어도 열리고, JS 가 있으면 누르는 순간 버그 제보 본문에 페이지 주소, 기기와 브라우저, 화면 크기를 넣는다.
지문, 목록, 복습 페이지 모두 apply() 한 번으로 넣고 바꾼다(여러 번 돌려도 같다).
"""
import html
import re
from urllib.parse import quote

import langs

MAIL = "hello@dokhaehanip.com"
IDEA_SUBJECT = f"[{langs.BRAND}] 기능 건의"
BUG_SUBJECT = f"[{langs.BRAND}] 버그 제보"

IDEA_ICON = ('<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 18h6M10 21h4M12 3a6 6 0 0 0-3.6 10.8c.6.5 1 1.2 1 2V16h5.2v-.2'
             'c0-.8.4-1.5 1-2A6 6 0 0 0 12 3z"/></svg>')
BUG_ICON = ('<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="7" y="8" width="10" height="12" rx="5"/>'
            '<path d="M9 8a3 3 0 0 1 6 0M3 13h4M17 13h4M4 7l3 2M20 7l-3 2M4 19l3-2M20 19l-3-2M12 11v8"/></svg>')

MARK_CSS = ("  /* fb */\n", "  /* /fb */\n")
CSS = (
    "  .fb { max-width: 560px; margin: 0 auto; padding: 20px 20px 4px; box-sizing: border-box; }\n"
    "  .fb-q { margin: 0; font-size: 15px; font-weight: 700; color: #191f28; }\n"
    "  .fb-d { margin: 3px 0 0; font-size: 13px; color: #6b7684; }\n"
    "  .fb-row { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }\n"
    "  .fb-btn { display: inline-flex; align-items: center; gap: 6px; height: 44px; padding: 0 16px; box-sizing: border-box; border-radius: 22px;"
    " background: #fff; border: 1px solid #e5e8eb; font-size: 14px; font-weight: 600; color: #191f28; text-decoration: none;"
    " -webkit-tap-highlight-color: transparent; }\n"
    "  .fb-btn:hover { background: #f9fafb; }\n"
    "  .fb-btn svg { width: 17px; height: 17px; flex: none; fill: none; stroke: #4e5968; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }\n"
    "  .fb + .site-footer { margin-top: 16px; padding-top: 16px; border-top: 1px solid #e5e8eb; }\n"
)


def mailto(subject, body):
    # 줄바꿈은 CRLF 로 보낸다(메일 앱마다 %0A 만 쓰면 한 줄로 붙는 곳이 있다)
    return f"mailto:{MAIL}?subject={quote(subject, safe='')}&body={quote(body.replace(chr(10), chr(13) + chr(10)), safe='')}"


def idea_body(lang=None):
    tail = f"\n\n\n----\n보던 언어: {langs.get(lang)['name']}" if lang else ""
    return "어떤 기능이 있으면 좋을까요?\n\n\n왜 필요한가요? (어떤 때 불편했는지)" + tail


def bug_body(url="", device="", size=""):
    return (f"무슨 일이 있었나요?\n(예: 음성이 안 나와요, 글자가 겹쳐 보여요)\n\n\n----\n"
            f"페이지: {url}\n기기: {device}\n화면 크기: {size}")


def block_html(lang=None, url=""):
    idea = html.escape(mailto(IDEA_SUBJECT, idea_body(lang)))
    bug = html.escape(mailto(BUG_SUBJECT, bug_body(url)))
    return ('<!-- fb -->\n<section class="fb" aria-label="의견 보내기"><p class="fb-q">독해한입에 바라는 점이 있나요?</p>'
            '<p class="fb-d">메일 앱이 열려요. 운영자가 직접 읽고 답장해요.</p><div class="fb-row">'
            f'<a class="fb-btn" data-fb="idea" href="{idea}">{IDEA_ICON}기능 건의</a>'
            f'<a class="fb-btn" data-fb="bug" href="{bug}">{BUG_ICON}버그 제보</a></div></section>\n<!-- /fb -->\n')


# 누르는 순간 버그 제보 본문의 '페이지, 기기, 화면 크기' 세 줄을 채운다. 기능 건의는 그대로 둔다
SCRIPT = """<script id="fb-js">
(function () {
  function device() {
    var u = navigator.userAgent, d = 'Windows', b = 'Safari';
    if (/iPhone/.test(u)) d = 'iPhone';
    else if (/iPad/.test(u) || (/Macintosh/.test(u) && navigator.maxTouchPoints > 1)) d = 'iPad';
    else if (/Android/.test(u)) d = 'Android';
    else if (/Macintosh/.test(u)) d = 'Mac';
    else if (!/Windows/.test(u)) d = '기타';
    if (/KAKAOTALK/i.test(u)) b = '카카오톡';
    else if (/NAVER/.test(u)) b = '네이버';
    else if (/SamsungBrowser/.test(u)) b = 'Samsung Internet';
    else if (/Edg/.test(u)) b = 'Edge';
    else if (/FxiOS|Firefox/.test(u)) b = 'Firefox';
    else if (/CriOS|Chrome/.test(u)) b = 'Chrome';
    return d + ', ' + b;
  }
  var links = document.querySelectorAll('.fb-btn');
  for (var i = 0; i < links.length; i++) links[i].addEventListener('click', function () {
    var type = this.getAttribute('data-fb');
    if (type === 'bug') {
      var body = '무슨 일이 있었나요?\\n(예: 음성이 안 나와요, 글자가 겹쳐 보여요)\\n\\n\\n----\\n페이지: ' + location.href +
        '\\n기기: ' + device() + '\\n화면 크기: ' + window.innerWidth + ' x ' + window.innerHeight;
      this.href = this.href.split('&body=')[0] + '&body=' + encodeURIComponent(body.replace(/\\n/g, '\\r\\n'));
    }
    try { if (typeof gtag === 'function') gtag('event', 'feedback', { type: type }); } catch (e) {}
  });
})();
</script>
"""

_CSS_RE = re.compile(re.escape(MARK_CSS[0]) + r".*?" + re.escape(MARK_CSS[1]), re.S)
_HTML_RE = re.compile(r"<!-- fb -->\n.*?<!-- /fb -->\n", re.S)
_JS_RE = re.compile(r'<script id="fb-js">.*?</script>\n', re.S)


def apply(page, lang=None, url=""):
    """하단 링크(.site-footer) 바로 위에 블록을 넣는다. 예전 블록은 지우고 다시 넣어 여러 번 돌려도 같다.
    하단 링크가 없는 페이지는 그대로 둔다."""
    if '<footer class="site-footer">' not in page:
        return page
    page = _JS_RE.sub("", _HTML_RE.sub("", _CSS_RE.sub("", page)))
    # 하단 링크 CSS 가 들어 있는 <style> 끝에 넣는다(없으면 첫 <style> 끝)
    at = page.find("</style>", max(page.find(".site-footer {"), 0))
    if at >= 0:
        page = page[:at] + MARK_CSS[0] + CSS + MARK_CSS[1] + page[at:]
    page = page.replace('<footer class="site-footer">', block_html(lang, url) + '<footer class="site-footer">', 1)
    return page.replace("</body>", SCRIPT + "</body>", 1)
