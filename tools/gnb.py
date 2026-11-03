"""모든 페이지가 같이 쓰는 위 메뉴(GNB). 승인 시안 A(design/gnb-mobile G01, G02, G03, 2026-11-03).

- 휴대폰: 화면 위에 붙은 흰 바. 왼쪽 오리+독해한입(→ /), 오른쪽 언어 칩 "<언어> ▾"와 "메일로 받기".
  언어 칩을 누르면 아래 시트가 열린다(언어 3개, 언어별 지난 지문, 그 언어 이번 주 단어 복습). 햄버거 버튼은 없다.
- PC(768px 이상): 언어 세그먼트 탭 + "지난 지문" + "메일로 받기". 칩과 시트는 쓰지 않는다.
- 언어 링크는 처음에 언어 첫 화면(/<언어>/)을 가리키고, 스크립트가 /latest.json 을 읽어 그 언어 오늘 지문으로 바꾼다.
  지난 페이지를 매일 다시 만들지 않아도 "오늘 지문"이 맞게 된다.

랜딩(landing/, Next.js)은 같은 CSS(landing/src/app/gnb.css, 테스트가 이 파일의 CSS 와 같은지 본다)와 같은 마크업을 React 로 그린다.
"""
import datetime as dt
import html
import json
import re
from pathlib import Path

import langs

ROOT = Path(__file__).resolve().parent.parent

# 색은 페이지마다 CSS 변수가 달라 직접 쓴다. 파랑만 --gnb-blue 로 바꿀 수 있게 둔다(랜딩은 자기 강조색).
CSS = """.gnb { position: sticky; top: 0; z-index: 40; background: #fff; border-bottom: 1px solid #e5e8eb; font-family: Pretendard, -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", "Noto Sans KR", sans-serif; letter-spacing: -0.01em; line-height: normal; }
.gnb a, .gnb button { color: inherit; text-decoration: none; -webkit-tap-highlight-color: transparent; }
.gnb button { font: inherit; background: none; border: 0; padding: 0; margin: 0; cursor: pointer; }
.gnb svg, .gnb-sheet svg { width: 16px; height: 16px; flex: none; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
.gnb-in { display: flex; align-items: center; gap: 4px; height: 56px; padding: 0 12px 0 16px; }
.gnb-brand { display: flex; align-items: center; gap: 6px; height: 44px; margin-right: auto; flex: none; font-size: 17px; font-weight: 800; letter-spacing: -0.035em; color: #191f28; white-space: nowrap; }
.gnb-brand img { display: block; height: 26px; width: auto; }
/* 누르는 영역(44px)과 보이는 모양(36px)을 나눈다 */
.gnb-tap { display: inline-flex; align-items: center; justify-content: center; min-height: 44px; min-width: 44px; flex: none; }
.gnb-chip .gnb-pill { display: inline-flex; align-items: center; gap: 2px; height: 36px; padding: 0 8px 0 12px; border-radius: 999px; background: #f2f4f6; font-size: 14px; font-weight: 700; color: #191f28; white-space: nowrap; }
.gnb-chip .gnb-pill svg { color: #6b7684; }
.gnb-chip[aria-expanded="true"] .gnb-pill { background: #e8f3ff; color: var(--gnb-blue, #1b64da); }
.gnb-mail .gnb-pill { display: inline-flex; align-items: center; height: 36px; padding: 0 14px; border-radius: 10px; background: var(--gnb-blue, #1b64da); color: #fff; font-size: 14px; font-weight: 700; white-space: nowrap; }
.gnb-mail:hover .gnb-pill { filter: brightness(.92); }
.gnb-seg, .gnb-past { display: none; }
.gnb a:focus-visible, .gnb button:focus-visible, .gnb-sheet a:focus-visible { outline: 2px solid var(--gnb-blue, #1b64da); outline-offset: 2px; border-radius: 10px; }
@media (max-width: 350px) { .gnb-brand span { display: none; } }
@media (min-width: 768px) {
  .gnb-in { max-width: 760px; margin: 0 auto; height: 64px; gap: 8px; box-sizing: content-box; padding: 0 24px; }
  .gnb-brand { font-size: 18px; margin-right: 24px; }
  .gnb-brand img { height: 28px; }
  .gnb-chip { display: none; }
  /* 보이는 칸은 36px, 누르는 칸은 바 높이 44px 전체. 켜진 칸의 흰 알약은 ::before 로 그린다 */
  .gnb-seg { display: flex; width: 260px; height: 44px; padding: 0 4px; gap: 2px; border-radius: 12px; background: #f2f4f6; box-sizing: border-box; }
  .gnb-seg a { position: relative; z-index: 0; flex: 1 1 0; min-width: 0; display: flex; align-items: center; justify-content: center; padding: 0 16px; font-size: 14px; font-weight: 600; color: #6b7684; white-space: nowrap; }
  .gnb-seg a:hover { color: #191f28; }
  .gnb-seg a.on { color: #191f28; font-weight: 700; }
  .gnb-seg a.on::before { content: ""; position: absolute; z-index: -1; inset: 4px 0; border-radius: 9px; background: #fff; box-shadow: 0 1px 3px rgba(16,24,40,.10); }
  .gnb-past { display: inline-flex; align-items: center; height: 44px; padding: 0 12px; margin-left: auto; border-radius: 10px; font-size: 15px; font-weight: 600; color: #4e5968; white-space: nowrap; }
  .gnb-past:hover { background: #f2f4f6; }
  .gnb-past.on { color: #191f28; font-weight: 700; }
}
/* 언어 시트(휴대폰) */
.gnb-scrim { position: fixed; inset: 0; z-index: 60; background: rgba(16,24,40,.40); }
.gnb-sheet { position: fixed; left: 0; right: 0; bottom: 0; z-index: 61; max-width: 560px; margin: 0 auto; box-sizing: border-box; background: #fff; border-radius: 24px 24px 0 0;
             padding: 8px 16px calc(24px + env(safe-area-inset-bottom)); box-shadow: 0 -8px 30px rgba(16,24,40,.12); color: #191f28;
             font-family: Pretendard, -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", "Noto Sans KR", sans-serif; letter-spacing: -0.01em; line-height: normal; text-align: left; }
.gnb-scrim[hidden], .gnb-sheet[hidden] { display: none; }
html.gnb-lock, html.gnb-lock body { overflow: hidden; }
.gnb-sheet a { color: inherit; text-decoration: none; -webkit-tap-highlight-color: transparent; }
.gnb-sheet .gs-handle { width: 36px; height: 5px; border-radius: 3px; background: #e5e8eb; margin: 0 auto 14px; }
.gnb-sheet h2 { font-size: 20px; font-weight: 800; letter-spacing: -0.03em; padding: 0 4px; margin: 0; line-height: 1.4; }
.gnb-sheet .gs-hint { font-size: 14px; color: #6b7684; margin: 4px 4px 12px; line-height: 1.5; }
.gs-row { display: flex; align-items: center; gap: 12px; min-height: 68px; padding: 10px 8px 10px 12px; border-radius: 16px; box-sizing: border-box; }
.gs-row.on { background: #e8f3ff; }
.gs-badge { flex: none; width: 40px; height: 40px; border-radius: 12px; display: grid; place-items: center; background: #f2f4f6; font-size: 13px; font-weight: 800; color: #4e5968; letter-spacing: 0.02em; }
.gs-row.on .gs-badge { background: #fff; color: var(--gnb-blue, #1b64da); }
.gs-tx { flex: 1; min-width: 0; display: block; min-height: 44px; }
.gs-nm { display: flex; align-items: center; gap: 4px; font-size: 16px; font-weight: 700; }
.gs-row.on .gs-nm { color: var(--gnb-blue, #1b64da); }
.gs-ds { display: block; font-size: 13px; color: #6b7684; margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.gs-past { flex: none; display: inline-flex; align-items: center; gap: 2px; height: 44px; padding: 0 6px 0 12px; border-radius: 12px; font-size: 14px; font-weight: 600; color: #4e5968; white-space: nowrap; }
.gs-row.on .gs-past { color: var(--gnb-blue, #1b64da); }
.gnb-sheet hr { border: 0; height: 1px; background: #e5e8eb; margin: 8px 4px; }
.gs-review { display: flex; align-items: center; gap: 12px; min-height: 60px; padding: 8px 8px 8px 12px; border-radius: 16px; }
.gs-review[hidden] { display: none; }
.gs-review .gs-badge { color: var(--gnb-blue, #1b64da); background: #e8f3ff; }
.gs-review .gs-badge svg { width: 20px; height: 20px; }
.gs-review .gs-tx { display: block; }
.gs-review > svg { width: 20px; height: 20px; color: #6b7684; }
"""

# 지문 페이지에만 쓰는 것: 카드 안 "읽기 수준" 세그먼트, PC 첫 카드(글 왼쪽, 사진 오른쪽), PC 본문 폭.
DAY_CSS = """.lvl { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: 16px; padding-top: 14px; border-top: 1px solid #e5e8eb; }
.lvl .lb { font-size: 14px; font-weight: 600; color: var(--sub); white-space: nowrap; }
.lvl-seg { display: flex; flex: none; width: 152px; height: 44px; padding: 0 4px; gap: 2px; border-radius: 12px; background: var(--bg); box-sizing: border-box; }
.lvl-seg a { position: relative; z-index: 0; flex: 1 1 0; display: flex; align-items: center; justify-content: center; font-size: 14px; font-weight: 600; color: var(--muted); text-decoration: none; white-space: nowrap; }
html:not(.level-a) #to-level-b, html.level-a #to-level-a { color: var(--ink); font-weight: 700; }
html:not(.level-a) #to-level-b::before, html.level-a #to-level-a::before { content: ""; position: absolute; z-index: -1; inset: 4px 0; border-radius: 9px; background: #fff; box-shadow: 0 1px 3px rgba(16,24,40,.10); }
.top h1 { font-size: 24px; line-height: 1.36; letter-spacing: -0.035em; }
/* 오른쪽 위 76px 썸네일 자리는 사진 배너가 있는 날에는 필요 없다 */
.top:has(> .hero) h1 { padding-right: 0; }
@media (min-width: 768px) {
  body > main { max-width: 784px; }
  main .pbar { max-width: 760px; }
  .top { padding: 28px 28px 24px; margin-top: 24px; }
  .top h1 { font-size: 28px; }
  .top:has(> .hero) { position: relative; padding-right: 308px; min-height: 300px; }
  .top > .hero { position: absolute; top: 0; right: 0; bottom: 0; width: 280px; margin: 0; aspect-ratio: auto; border-radius: 0 var(--card-r) var(--card-r) 0; }
}
"""

ICON_DOWN = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>'
ICON_RIGHT = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 6l6 6-6 6"/></svg>'
ICON_CHECK = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>'
ICON_CARDS = '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3.5" y="6" width="13" height="15" rx="2.5"/><path d="M8 3h9.5A3 3 0 0 1 20.5 6v11"/></svg>'

# 언어가 정해지지 않은 페이지(랜딩)의 칩 문구
CHIP_ANY = "언어"


def public_langs(current=None):
    """메뉴에 보일 언어: 공개(noindex 아님) 언어와, 지금 보고 있는 언어(비공개여도)."""
    return [c for c in langs.LANGS if not langs.LANGS[c].get("noindex") or c == current]


def latest_review(lang):
    """그 언어의 가장 최근 주간 복습: (날짜, 단어 수). 없으면 None."""
    rdir = ROOT / lang / "review"
    days = sorted((p.name for p in rdir.iterdir() if p.is_dir() and (p / "index.html").exists()), reverse=True) if rdir.exists() else []
    if not days:
        return None
    end = dt.date.fromisoformat(days[0])
    n = 0
    for i in range(7):
        f = ROOT / "content" / lang / f"{(end - dt.timedelta(days=i)).isoformat()}.json"
        if f.exists():
            n += len(json.loads(f.read_text(encoding="utf-8")).get("words", []))
    return days[0], n


def review_desc(lang, words):
    return f"{langs.LANGS[lang]['name']} 단어 {words}개를 다시 봐요"


def header_html(lang=None, mail="#subscribe", on_archive=False):
    """위 메뉴 바와 언어 시트. lang=None 이면 언어가 정해지지 않은 페이지(랜딩)."""
    codes = public_langs(lang)
    chip = langs.LANGS[lang]["name"] if lang else CHIP_ANY
    chip_label = f"언어 고르기, 지금 {chip}" if lang else "언어 고르기"
    seg = "".join(
        f'<a href="/{c}/" data-today="{c}"' + (' class="on" aria-current="page"' if c == lang else "") + f'>{langs.LANGS[c]["name"]}</a>'
        for c in codes
    )
    past = (f'<a class="gnb-past{" on" if on_archive else ""}" href="/{lang}/archive/"' + (' aria-current="page"' if on_archive else "") + '>지난 지문</a>') if lang else ""
    rows = []
    for c in codes:
        L = langs.LANGS[c]
        on = c == lang
        rows.append(
            f'  <div class="gs-row{" on" if on else ""}"><span class="gs-badge" aria-hidden="true">{c.upper()}</span>'
            f'<a class="gs-tx" href="/{c}/" data-today="{c}"' + (' aria-current="true"' if on else "") + '>'
            f'<span class="gs-nm">{L["name"]}{ICON_CHECK if on else ""}</span>'
            f'<span class="gs-ds" data-ds="{c}" data-level="{html.escape(L["level"])}">{html.escape(L["level"])} {L["name"]} 읽기</span></a>'
            f'<a class="gs-past" href="/{c}/archive/" aria-label="{L["name"]} 지난 지문">지난 지문{ICON_RIGHT}</a></div>\n'
        )
    review = ""
    if lang:
        r = latest_review(lang)
        href, desc = (f"/{lang}/review/{r[0]}/", review_desc(lang, r[1])) if r else (f"/{lang}/archive/", "")
        review = (
            '  <hr>\n'
            f'  <a class="gs-review" id="gnb-review" data-lang="{lang}" href="{href}"' + ("" if r else " hidden") + '>'
            f'<span class="gs-badge" aria-hidden="true">{ICON_CARDS}</span>'
            f'<span class="gs-tx"><span class="gs-nm">이번 주 단어 복습</span><span class="gs-ds" id="gnb-review-ds">{desc}</span></span>{ICON_RIGHT}</a>\n'
        )
    return (
        "<!-- gnb -->\n"
        '<header class="gnb"><div class="gnb-in">'
        '<a class="gnb-brand" href="/"><img src="/assets/brand/duck-lying-64.png" alt="" width="40" height="26"><span>독해한입</span></a>'
        f'<nav class="gnb-seg" aria-label="언어">{seg}</nav>{past}'
        '<button class="gnb-tap gnb-chip" id="gnb-chip" type="button" aria-haspopup="dialog" aria-expanded="false" aria-controls="gnb-sheet"'
        f' aria-label="{chip_label}">'
        f'<span class="gnb-pill">{chip}{ICON_DOWN}</span></button>'
        f'<a class="gnb-tap gnb-mail" href="{mail}"><span class="gnb-pill">메일로 받기</span></a>'
        "</div></header>\n"
        '<div class="gnb-scrim" id="gnb-scrim" hidden></div>\n'
        '<div class="gnb-sheet" id="gnb-sheet" role="dialog" aria-modal="true" aria-labelledby="gnb-sheet-h" hidden>\n'
        '  <div class="gs-handle"></div>\n'
        '  <h2 id="gnb-sheet-h">어떤 언어를 읽을까요?</h2>\n'
        '  <p class="gs-hint">언어를 누르면 그 언어의 오늘 지문으로 가요</p>\n'
        + "".join(rows) + review +
        "</div>\n"
        "<!-- /gnb -->\n"
    )


# 시트 열고 닫기(바깥 누르기, ESC, 포커스 가두기와 되돌리기)와 /latest.json 으로 오늘 지문 링크 맞추기
SCRIPT = r"""<script id="gnb-js">(function(){
  var chip=document.getElementById('gnb-chip'),sheet=document.getElementById('gnb-sheet'),scrim=document.getElementById('gnb-scrim');
  if(!chip||!sheet||!scrim)return;
  var root=document.documentElement;
  function items(){return [].filter.call(sheet.querySelectorAll('a[href]'),function(a){return !a.hidden;});}
  function key(e){
    if(e.key==='Escape'){e.preventDefault();close();return;}
    if(e.key!=='Tab')return;
    var f=items();if(!f.length)return;
    var a=f[0],z=f[f.length-1];
    if(e.shiftKey&&document.activeElement===a){e.preventDefault();z.focus();}
    else if(!e.shiftKey&&document.activeElement===z){e.preventDefault();a.focus();}
    else if(!sheet.contains(document.activeElement)){e.preventDefault();a.focus();}
  }
  function open(){
    sheet.hidden=false;scrim.hidden=false;chip.setAttribute('aria-expanded','true');root.classList.add('gnb-lock');
    var cur=sheet.querySelector('.gs-row.on .gs-tx')||items()[0];if(cur)cur.focus();
    document.addEventListener('keydown',key);
    try{if(typeof gtag==='function')gtag('event','gnb_sheet_open',{lang:location.pathname.split('/')[1]||''});}catch(e){}
  }
  function close(){
    if(sheet.hidden)return;
    sheet.hidden=true;scrim.hidden=true;chip.setAttribute('aria-expanded','false');root.classList.remove('gnb-lock');
    document.removeEventListener('keydown',key);chip.focus();
  }
  chip.addEventListener('click',function(){sheet.hidden?open():close();});
  scrim.addEventListener('click',close);
  addEventListener('pageshow',function(){if(!sheet.hidden){sheet.hidden=true;scrim.hidden=true;chip.setAttribute('aria-expanded','false');root.classList.remove('gnb-lock');}});
  if(!window.fetch)return;
  fetch('/latest.json',{cache:'no-store'}).then(function(r){return r.ok?r.json():null;}).then(function(d){
    if(!d||!d.langs)return;
    [].forEach.call(document.querySelectorAll('[data-today]'),function(a){var x=d.langs[a.getAttribute('data-today')];if(x&&x.latest)a.href='/'+a.getAttribute('data-today')+'/'+x.latest+'/';});
    [].forEach.call(sheet.querySelectorAll('[data-ds]'),function(s){var x=d.langs[s.getAttribute('data-ds')];
      if(x&&x.topic)s.textContent=s.getAttribute('data-level')+', 오늘은 '+String(x.topic).replace(/\{([^{}|]+)\|[^{}|]+\}/g,'$1');});
    var rv=document.getElementById('gnb-review');
    if(rv){var x=d.langs[rv.getAttribute('data-lang')];
      if(x&&x.review&&x.review.day){rv.href='/'+rv.getAttribute('data-lang')+'/review/'+x.review.day+'/';
        document.getElementById('gnb-review-ds').textContent=x.review.desc||'';rv.hidden=false;}}
  }).catch(function(){});
})();</script>
"""

MARK_CSS = ("  /* gnb-a */\n", "  /* /gnb-a */\n")
MARK_DAY_CSS = ("  /* day-a */\n", "  /* /day-a */\n")


def css_block(day=False):
    """페이지 <style> 안에 넣는 블록. 첫 줄은 다른 패치들이 기준으로 쓰는 '  .gnb {' 로 시작한다(그 앞에 CSS 를 끼워 넣는다)."""
    body = "".join("  " + line + "\n" if line else "\n" for line in CSS.rstrip("\n").split("\n"))
    first, rest = body.split("\n", 1)
    out = first + "\n" + MARK_CSS[0] + rest + MARK_CSS[1]
    if day:
        out += MARK_DAY_CSS[0] + "".join("  " + line + "\n" for line in DAY_CSS.rstrip("\n").split("\n")) + MARK_DAY_CSS[1]
    return out


_BLOCK_RE = re.compile(r"  \.gnb \{[^\n]*\n  /\* gnb-a \*/\n.*?  /\* /gnb-a \*/\n(?:  /\* day-a \*/\n.*?  /\* /day-a \*/\n)?", re.S)
# 예전 위 메뉴 CSS: '.gnb {', '.gnb .brand ...', '.gnb nav ...' 줄과 좁은 화면 줄, 다른 언어 알약 줄
_LEGACY_RE = re.compile(r"^  (?:\.gnb[ {][^\n]*|/\* gnb-narrow \*/[^\n]*|a\.lang-go \{[^\n]*|\.lang-row[ {][^\n]*|\.level-link[ {][^\n]*)\n", re.M)


def apply_css(page, day=False):
    """새 블록으로 바꾼다. 예전 .gnb 줄은 지우고, 첫 줄이 있던 자리에 새 블록을 넣는다(여러 번 돌려도 같다)."""
    m = _BLOCK_RE.search(page)
    at = None
    if m:
        at = m.start()
        page = page[:m.start()] + page[m.end():]
    legacy = list(_LEGACY_RE.finditer(page))
    if legacy:
        first = legacy[0].start() if at is None else min(at, legacy[0].start())
        # 뒤에서부터 지워 앞 위치가 흔들리지 않게 한다. 지운 줄 중 first 앞의 것이 없으므로 first 는 그대로다
        for x in reversed(legacy):
            page = page[:x.start()] + page[x.end():]
        at = first
    if at is None:
        at = page.index("</style>")
    return page[:at] + css_block(day) + page[at:]


_HEADER_RE = re.compile(r"<!-- gnb -->\n.*?<!-- /gnb -->\n|[ \t]*<header class=\"gnb\">.*?</header>\n", re.S)


def apply_html(page, lang, mail="#subscribe", on_archive=False):
    """위 메뉴를 <main> 바로 앞(본문 밖, 화면 폭 전체)에 둔다. 예전 자리(main 안)의 메뉴는 지운다."""
    page = _HEADER_RE.sub("", page)
    return page.replace("<main>", header_html(lang, mail, on_archive) + "<main>", 1)


def apply_script(page):
    page = re.sub(r'<script id="gnb-js">.*?</script>\n', "", page, flags=re.S)
    return page.replace("</body>", SCRIPT + "</body>", 1)


def apply(page, lang, mail="#subscribe", on_archive=False, day=False):
    return apply_script(apply_html(apply_css(page, day), lang, mail, on_archive))
