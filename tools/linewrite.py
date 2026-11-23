"""문장마다 내 해석 쓰기(시안 design/mine-notes M11~M14, M21, M24, M25).

지문 아래 한 칸이던 '내 해석'을 문장 아래 칸으로 바꾸고, 모아서 AI 에게 물을 글을 복사한다.
동작은 assets/linewrite.js, 쓴 글은 이 기기(localStorage 'mine:v1')에만 남는다.
템플릿은 그대로 두고 patch_page 에서 apply() 로 넣는다. 새 페이지와 지난 페이지가 같은 길로 지나가고,
여러 번 돌려도 같다. linewrite.js 를 고치면 VERSION 을 올린다.
"""
import re

VERSION = "1"

CSS = """  /* linewrite-css */
  .lw-bar { display: flex; align-items: center; gap: 8px; width: 100%; border: 0; text-align: left; font: inherit; font-size: 14px; font-weight: 700; cursor: pointer; background: var(--blue-soft); color: var(--blue); border-radius: 12px; padding: 10px 12px; margin: 0 0 14px; min-height: 44px; }
  .lw-bar svg, .lw-btn svg { width: 18px; height: 18px; flex: none; }
  .lw-bar span { flex: 1; }
  .lw-bar i { width: 40px; height: 24px; border-radius: 12px; background: var(--blue); position: relative; flex: none; }
  .lw-bar i::after { content: ""; position: absolute; top: 3px; left: 19px; width: 18px; height: 18px; border-radius: 50%; background: #fff; box-shadow: 0 1px 3px rgba(16,24,40,.2); }
  html.lw-off .lw-bar i { background: #6b7684; }
  html.lw-off .lw-bar i::after { left: 3px; }
  html.lw-off .lw, html.lw-off .lw-dock { display: none; }
  html:not(.lw-off) #passage .say { display: flex; flex-direction: column; }
  .lw { order: 1; margin-top: 8px; }
  .lw-box { position: relative; }
  .lw textarea { display: block; width: 100%; min-height: 44px; resize: none; overflow: hidden; field-sizing: content; box-sizing: border-box; border: 1px solid #d5dae0; border-radius: 10px; background: #fff; padding: 9px 44px 9px 11px; font: inherit; font-size: 16px; line-height: 1.5; color: var(--ink); scroll-margin: 190px 0 90px; }
  .lw textarea::placeholder { color: var(--muted); }
  .lw textarea:focus { outline: 0; border-color: var(--blue); box-shadow: 0 0 0 3px var(--blue-soft); }
  .lw-star { position: absolute; right: 0; top: 0; width: 44px; height: 44px; border: 0; background: none; padding: 0; cursor: pointer; color: var(--muted); display: grid; place-items: center; }
  .lw-star svg { width: 18px; height: 18px; fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linejoin: round; }
  .lw-star[aria-pressed=true] { color: #e0a100; }
  .lw-star[aria-pressed=true] svg { fill: currentColor; }
  .lw-cmp { border: 0; background: none; padding: 8px 0; font: inherit; font-size: 13px; font-weight: 600; color: var(--blue); cursor: pointer; }
  html:not(.lw-off) #passage .say > .ko, html:not(.lw-off) #passage .say > .ko-a { order: 2; margin-top: 8px; background: #e8f7f1; border-radius: 10px; padding: 8px 11px; color: var(--ink); }
  html:not(.lw-off) #passage .say > .ko::before, html:not(.lw-off) #passage .say > .ko-a::before { content: "모범 해석"; display: block; font-size: 12px; font-weight: 700; color: #0b7a53; }
  html:not(.level-a) .say:has(> .ko:not([hidden])) .lw-cmp, html.level-a .say:has(> .ko-a:not([hidden])) .lw-cmp { display: none; }
  html:not(.lw-off) .sent:has(textarea:focus) .say > .en, html:not(.lw-off) .sent:has(textarea:focus) .say > .en-a, html:not(.lw-off) .sent:has(textarea:focus) .say > .chunks, html:not(.lw-off) .sent:has(textarea:focus) .say > .chunks-a { position: sticky; top: 57px; z-index: 5; background: var(--card); padding-bottom: 6px; }
  .lw-dock { position: sticky; bottom: calc(12px + env(safe-area-inset-bottom)); z-index: 20; margin: 18px -8px -8px; background: #fff; border-radius: var(--card-r); box-shadow: 0 6px 24px rgba(16,24,40,.14); padding: 10px 10px 10px 16px; display: flex; align-items: center; gap: 10px; }
  .lw-dock > div { flex: 1; min-width: 0; font-size: 13px; color: var(--sub); line-height: 1.35; }
  .lw-dock b { display: block; font-size: 15px; color: var(--ink); }
  .lw-dock .ok { color: #0b7a53; }
  .lw-dock .bad { color: #d92d3a; }
  body.pbar-vis .lw-dock { bottom: calc(86px + env(safe-area-inset-bottom)); }
  body.lw-typing .lw-dock, body.lw-typing .pbar { display: none; }
  .lw-btn { border: 0; border-radius: 12px; background: var(--blue); color: #fff; font: inherit; font-size: 15px; font-weight: 700; min-height: 44px; padding: 10px 14px; display: inline-flex; align-items: center; justify-content: center; gap: 6px; white-space: nowrap; cursor: pointer; }
  .lw-btn.line { background: #fff; color: var(--ink); box-shadow: inset 0 0 0 1.5px #e2e6ea; }
  .lw-btn:disabled { opacity: .4; cursor: default; }
  .lw-acc { position: fixed; left: 0; right: 0; bottom: 0; z-index: 45; display: none; justify-content: space-between; align-items: center; gap: 8px; background: #fff; border-top: 1px solid #e2e6ea; padding: 6px 12px; font-size: 13px; color: var(--sub); }
  body.lw-typing .lw-acc { display: flex; }
  .lw-dim { position: fixed; inset: 0; z-index: 70; background: rgba(15,20,30,.45); }
  .lw-sheet { outline: 0; position: fixed; left: 0; right: 0; bottom: 0; z-index: 71; max-width: 560px; max-height: 92vh; overflow-y: auto; margin: 0 auto; box-sizing: border-box; background: #fff; border-radius: 22px 22px 0 0; padding: 22px 18px calc(22px + env(safe-area-inset-bottom)); }
  .lw-sheet h3 { font-size: 19px; margin: 0 0 4px; }
  .lw-sheet p { font-size: 14px; color: var(--sub); margin: 0 0 14px; line-height: 1.55; }
  .lw-sheet fieldset { border: 0; margin: 0 0 14px; padding: 0; min-width: 0; }
  .lw-sheet legend { font-size: 13px; font-weight: 700; color: var(--sub); padding: 0; margin: 0 0 8px; }
  .lw-sheet label { cursor: pointer; }
  .lw-sheet input { accent-color: var(--blue); width: 18px; height: 18px; margin: 1px 0 0; flex: none; }
  .lw-seg { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; }
  .lw-seg label { text-align: center; border: 1.5px solid #e2e6ea; border-radius: 12px; padding: 8px 2px; font-size: 14px; font-weight: 600; color: var(--sub); }
  .lw-seg input { position: absolute; opacity: 0; width: 1px; height: 1px; }
  .lw-seg small { display: block; font-size: 12px; font-weight: 500; }
  .lw-rad { display: flex; gap: 10px; padding: 11px 12px; border: 1.5px solid #e2e6ea; border-radius: 12px; margin-bottom: 8px; }
  .lw-rad b { display: block; font-size: 15px; }
  .lw-rad span span { font-size: 13px; color: var(--sub); }
  .lw-sheet label:has(input:checked) { border-color: var(--blue); background: var(--blue-soft); color: var(--ink); }
  .lw-sheet label:has(input:focus-visible) { outline: 2px solid var(--blue); outline-offset: 2px; }
  .lw-sheet label:has(input:disabled) { opacity: .45; cursor: default; }
  .lw-row { display: flex; gap: 8px; }
  .lw-row > * { flex: 1; }
  .lw-area { width: 100%; height: 40vh; box-sizing: border-box; border: 0; border-radius: 12px; background: var(--bg); padding: 12px; font: inherit; font-size: 14px; line-height: 1.6; color: var(--ink); margin: 0 0 12px; resize: none; }
  .lw-toast { position: fixed; left: 12px; right: 12px; bottom: calc(96px + env(safe-area-inset-bottom)); z-index: 72; max-width: 536px; margin: 0 auto; box-sizing: border-box; background: var(--ink); color: #fff; border-radius: 16px; padding: 12px 16px; font-size: 14px; line-height: 1.45; }
  .lw-toast b { display: block; font-size: 15px; }
  /* /linewrite-css */
"""

_PEN = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 20l1-4L16 5l3 3L8 19z"/></svg>'
_CHAT = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 5h16v11H10l-4 4v-4H4z"/></svg>'
_STAR = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3.5l2.6 5.4 5.9.8-4.3 4.1 1 5.9-5.2-2.8-5.2 2.8 1-5.9-4.3-4.1 5.9-.8z"/></svg>'

BAR = (
    "    <!-- lw-bar --><script>try{if(localStorage.getItem('mine:on')==='0')document.documentElement.classList.add('lw-off')}catch(e){}</script>"
    f'<button class="lw-bar" id="lw-sw" type="button" role="switch" aria-checked="true">{_PEN}<span>문장마다 해석 쓰기</span><i></i></button><!-- /lw-bar -->\n'
)
DOCK = (
    '    <!-- lw-dock --><div class="lw-dock" id="lw-dock"><div><b id="lw-n"></b><span id="lw-st" role="status"></span></div>'
    f'<button class="lw-btn" id="lw-ask" type="button">{_CHAT}AI에게 물어보기</button></div><!-- /lw-dock -->\n'
)


def field(n):
    return (
        f'<!-- lw --><div class="lw"><div class="lw-box"><textarea rows="1" maxlength="1000" enterkeyhint="next" spellcheck="false" aria-label="{n}번 문장 내 해석" placeholder="내 말로 적어 보세요"></textarea>'
        f'<button class="lw-star" type="button" aria-pressed="false" aria-label="{n}번 문장 헷갈림 표시">{_STAR}</button></div>'
        '<button class="lw-cmp" type="button" hidden>모범 해석과 맞춰 보기</button></div><!-- /lw -->'
    )


SCRIPT = f'<script id="linewrite-js" src="/assets/linewrite.js?v={VERSION}" defer></script>\n'

_CSS_RE = re.compile(r"  /\* linewrite-css \*/\n.*?  /\* /linewrite-css \*/\n", re.S)
_OLD_CSS = re.compile(r"  \.mine \{ margin-top: 24px; \}\n.*?  \.mine-hint \{[^\n]*\n", re.S)
_OLD_BLOCK = re.compile(r'    <div class="mine">.*?\n    </div>\n', re.S)
_DOCK_RE = re.compile(r"    <!-- lw-dock -->.*?<!-- /lw-dock -->\n", re.S)
_BAR_RE = re.compile(r"    <!-- lw-bar -->.*?<!-- /lw-bar -->\n", re.S)
_FIELD_RE = re.compile(r"<!-- lw -->.*?<!-- /lw -->", re.S)
_SENT_RE = re.compile(r'^(    <div class="sent">.*)(</div></div>)$', re.M)
_SCRIPT_RE = re.compile(r'<script id="linewrite-js"[^>]*></script>\n')
_OLD_JS = re.compile(r"  copyMine\.addEventListener\('click', function \(\) \{\n.*?\n  \}\);\n", re.S)
_OLD_VAR = "  var mine = document.getElementById('mine'), copyMine = document.getElementById('copymine');\n"
TEXTS = (
    ("['#mine', '해석을 보기 전에", "['#passage .lw-box', '해석을 보기 전에"),
    ("['#copymine', 'AI 피드백이란?', '누르면 지문, 내 해석, 첨삭 요청이", "['#lw-ask', 'AI 피드백이란?', '누르고 복사하면 지문, 내 해석, 첨삭 요청이"),
    ("지문 아래 '내 해석' 칸에 적어 보세요. 다 쓰면 'AI 피드백 요청문 복사'를 눌러", "문장 아래 칸에 적어 보세요. 다 쓰면 'AI에게 물어보기'에서 복사해"),
)


def apply(page):
    """지문 페이지에 문장별 쓰기를 넣는다. 이미 있으면 지금 내용으로 바꾼다."""
    if not (_OLD_BLOCK.search(page) or _DOCK_RE.search(page)) or not _SENT_RE.search(page):
        return page
    page = (_CSS_RE if _CSS_RE.search(page) else _OLD_CSS).sub(lambda m: CSS, page, count=1)
    page = (_DOCK_RE if _DOCK_RE.search(page) else _OLD_BLOCK).sub(lambda m: DOCK, page, count=1)
    page = _FIELD_RE.sub("", _BAR_RE.sub("", page))
    n = 0

    def put(m):
        nonlocal n
        n += 1
        return (BAR if n == 1 else "") + m.group(1) + field(n) + m.group(2)

    page = _SENT_RE.sub(put, page)
    page = _OLD_JS.sub("", page.replace(_OLD_VAR, "", 1), count=1)
    for old, new in TEXTS:
        page = page.replace(old, new, 1)
    return _SCRIPT_RE.sub("", page).replace("</body>", SCRIPT + "</body>", 1)
