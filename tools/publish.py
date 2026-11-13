"""한 언어의 새 날짜 폴더를 사이트에 붙인다. 같은 날짜로 여러 번 돌려도 결과가 같다.

사용: python3 tools/publish.py en 2026-10-12 [분야]  (분야를 생략하면 content JSON 의 category)
1. 썸네일(<언어>/<날짜>/thumb.png) 생성
2. 날짜 페이지에 OG 태그, 상단 썸네일, 소개 문구, 구독 칸 삽입
3. 그 언어의 지난 지문(<언어>/archive/), 언어 첫 화면(<언어>/), 사이트 첫 화면용 latest.json 을 다시 생성
"""
import datetime as dt
import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import langs  # noqa: E402
import thumb  # noqa: E402
import vote  # noqa: E402
import drill  # noqa: E402
import gnb  # noqa: E402
import feedback  # noqa: E402
import track  # noqa: E402
import seek  # noqa: E402
import migrate  # noqa: E402
from render import LEVEL_SEG, MADE_HTML, date_label, page_title  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SITE = langs.SITE
SUBSCRIBE = "https://buttondown.com/api/emails/embed-subscribe/dokhaehanip"
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
DAYS = "월화수목금토일"

# 처음 온 사람을 위한 한 줄 소개와 구독 칸. 날짜 페이지와 지난 지문 페이지에 같이 쓴다(색은 각 페이지의 CSS 변수).
INTRO_CSS = ("  .intro { margin: 14px 0 0; font-size: 14px; line-height: 1.6; color: var(--sub); }\n"
             "  .intro a { color: var(--blue); font-weight: 600; text-decoration: none; margin-right: 6px; }\n")
SUB_CSS = (
    "  .sub { scroll-margin-top: 84px; }\n"
    "  .sub h2 { margin-bottom: 4px; }\n  .sub p { margin: 0 0 14px; font-size: 15px; color: var(--sub); }\n"
    # form은 flex-wrap:wrap — levels/note/email+button 이 각각 한 줄씩 차지한다
    "  .sub form { display: flex; flex-wrap: wrap; gap: 8px; }\n"
    "  .sub input[type='email'] { flex: 1 1 auto; min-width: 0; height: 48px; border: 1.5px solid transparent; border-radius: 12px; background: var(--bg);"
    " padding: 0 14px; font: 400 16px Pretendard, -apple-system, sans-serif; color: var(--ink); outline: 0; }\n"
    "  .sub input[type='email']:focus { border-color: var(--blue); background: #fff; }\n"
    "  .sub button[type='submit'] { flex: none; height: 48px; padding: 0 18px; border: 0; border-radius: 12px; background: var(--blue); color: #fff;"
    " font: 700 15px Pretendard, -apple-system, sans-serif; cursor: pointer; }\n"
    "  .sub .note { margin: 10px 0 0; font-size: 13px; line-height: 1.6; color: var(--muted); }\n"
    "  .sub .levels { flex-basis: 100%; display: flex; flex-direction: column; gap: 8px; margin: 0; border: 0; padding: 0; }\n"
    "  .sub .levels legend { font-size: 14px; font-weight: 600; margin: 0 0 8px; padding: 0; }\n"
    "  .sub .lvopt { display: flex; flex-direction: column; gap: 3px; border: 1.5px solid #e2e6ea; border-radius: 10px;"
    " padding: 12px 14px; cursor: pointer; text-align: left; background: #f4f6f8; position: relative; width: 100%; box-sizing: border-box; }\n"
    "  .sub .lvopt input[type='radio'] { position: absolute; opacity: 0; width: 1px; height: 1px; pointer-events: none; }\n"
    # :has() 기반 선택 상태 (모던 브라우저)
    "  .sub .lvopt:has(input:checked),.sub .lvopt[data-checked] { background: #eff3fd; border-color: #2a52d4; }\n"
    "  .sub .lvopt .lv-t { font-size: 15px; font-weight: 700; display: flex; justify-content: space-between; align-items: center; }\n"
    "  .sub .lvopt .lv-r { font-size: 12px; color: var(--muted); }\n"
    "  .sub .lvopt .lv-d { font-size: 13px; color: var(--sub); margin-top: 2px; }\n"
    "  .sub .lvopt .lv-chk { width: 18px; height: 18px; border-radius: 50%; border: 1.5px solid #c5ccd6; flex: none;"
    " display: flex; align-items: center; justify-content: center; color: transparent; }\n"
    "  .sub .lvopt:has(input:checked) .lv-chk,.sub .lvopt[data-checked] .lv-chk { background: #2a52d4; border-color: #2a52d4; color: #fff; }\n"
)


# 모든 페이지 공통 하단: 독해한입 자체 안내 페이지 3개(시안 design/own-pages O02). 애드센스 심사에서 정책 페이지로 가는 길이 모든 페이지에 있어야 한다.
FOOTER_CSS = (".site-footer { max-width: 560px; margin: 0 auto; padding: 8px 20px 40px; font-size: 13px; color: #6b7684; "
              "display: flex; flex-wrap: wrap; gap: 6px 16px; } .site-footer a { color: #4e5968; text-decoration: none; }\n")
FOOTER_PAGES = (("/about/", "소개"), ("/privacy/", "개인정보처리방침"), ("/contact/", "연락처"))


def footer_links(cur=None):
    """하단 링크 줄. cur 는 지금 보고 있는 안내 페이지 주소(굵게, aria-current)."""
    return "".join(f'<a href="{h}"' + (' class="cur" aria-current="page"' if h == cur else "") + f'>{t}</a>' for h, t in FOOTER_PAGES)


FOOTER_HTML = f'<footer class="site-footer">{footer_links()}</footer>\n'
# 예전 하단 링크(www.wspace.ai.kr 로 나가던 4개). 지난 페이지에서 새 링크로 바꾼다
OLD_FOOTER_LINKS = ('<a href="https://www.wspace.ai.kr/">wspace 홈</a>'
                    '<a href="https://www.wspace.ai.kr/about/">소개</a><a href="https://www.wspace.ai.kr/privacy/">개인정보처리방침</a>'
                    '<a href="https://www.wspace.ai.kr/contact/">연락처</a>')


# 지문 페이지 첫 카드가 끝나는 자리. 소개 문단과 읽기 수준 세그먼트를 이 앞에 둔다
TOP_END = "\n  </div>\n\n  <section class=\"card\" id=\"passage\">"


def public_langs(current=None):
    """언어 전환에 보여 줄 언어: 공개(noindex 아님) 언어와, 지금 보고 있는 언어(비공개여도)."""
    return gnb.public_langs(current)


def intro_html(lang):
    L = langs.get(lang)
    # 메일로 받기는 위 메뉴(GNB)로 옮겼다(시안 A, 이슈 #20)
    return f'    <p class="intro">{L["intro"]} 듣고, 해석하고, AI에게 피드백을 받아 보세요.</p>\n'


def _sub_script(lang):
    """구독 칸 인라인 스크립트.
    - GA subscribe 이벤트: levels=True 언어(en, de)는 level 파라미터 포함, 그 외는 생략.
    - :has() 미지원 브라우저 fallback: 라디오 change 시 data-checked 속성으로 CSS 선택 상태를 제어한다.
    """
    if langs.LANGS[lang].get("levels", False):
        ga_event = (
            f'gtag("event","subscribe",{{lang:"{lang}",level:cl?cl.value:"b"}})'
        )
    else:
        ga_event = f'gtag("event","subscribe",{{lang:"{lang}"}})'
    return (
        f'    <script>(function(){{\n'
        f'      var sec=document.getElementById("subscribe");\n'
        f'      if(!sec)return;\n'
        f'      var f=sec.querySelector("form");\n'
        f'      // GA subscribe event (영어는 level 포함, 다른 언어는 생략)\n'
        f'      if(f)f.addEventListener("submit",function(){{\n'
        f'        var cl=f.querySelector(\'input[name="metadata__level"]:checked\');\n'
        f'        try{{if(typeof gtag==="function"){ga_event};}}catch(e){{}}\n'
        f'      }});\n'
        f'      // :has() 미지원 브라우저 fallback — data-checked 속성으로 CSS 를 보조한다\n'
        f'      var opts=sec.querySelectorAll(".lvopt");\n'
        f'      if(opts.length){{var update=function(){{\n'
        f'        opts.forEach(function(o){{\n'
        f'          var r=o.querySelector("input[type=\\"radio\\"]");\n'
        f'          if(r&&r.checked){{o.setAttribute("data-checked","");}}else{{o.removeAttribute("data-checked");}}\n'
        f'        }});\n'
        f'      }};update();\n'
        f'      opts.forEach(function(o){{var r=o.querySelector("input[type=\\"radio\\"]");if(r)r.addEventListener("change",update);}});\n'
        f'      }}\n'
        f'    }})();</script>\n'
    )


# 수준 선택 카드의 언어별 문구: (기초 범위, 기초 설명, 중급 범위, 중급 설명)
LEVEL_CHOICES = {
    "en": ("A2~B1", "짧고 쉬운 문장. 영어 읽기를 다시 시작한다면",
           "B1~B2", "뉴스 기사에 가까운 문장. 긴 문장도 읽어 보고 싶다면"),
    "de": ("A2~B1", "짧고 쉬운 문장. 독일어 읽기를 막 시작했다면",
           "B1~B2", "조금 긴 문장과 B2 문법도 읽어 보고 싶다면"),
    "ja": ("N4~N5", "짧고 쉬운 문장. 일본어 읽기를 막 시작했다면",
           "N3", "조금 긴 문장과 N3 문법도 읽어 보고 싶다면"),
}


def sub_html(lang):
    """구독 칸. 숨은 입력값 metadata__lang 으로 구독자의 언어를 Buttondown 에 저장해 언어별로 보낸다.
    levels=True 언어(en, de, ja)에는 수준 선택 라디오 카드(metadata__level: a=기초, b=중급)를 표시한다. 기본 선택은 중급.
    문구는 LEVEL_CHOICES. levels=False 언어는 수준 선택 없이 기존 형태를 유지한다.
    버전 마커: data-v="3" — patch_page 가 이 값으로 이전 카드를 교체한다.
    """
    L = langs.get(lang)
    level_html = ""
    if langs.LANGS[lang].get("levels", False):
        range_a, desc_a, range_b, desc_b = LEVEL_CHOICES.get(lang, LEVEL_CHOICES["en"])
        level_html = (
            '      <fieldset class="levels">\n'
            '        <legend>수준을 골라 주세요</legend>\n'
            '        <label class="lvopt">\n'
            '          <input type="radio" name="metadata__level" value="a">\n'
            '          <span class="lv-t">기초 <span class="lv-chk">&#10003;</span></span>\n'
            f'          <span class="lv-r">{range_a}</span>\n'
            f'          <span class="lv-d">{desc_a}</span>\n'
            '        </label>\n'
            '        <label class="lvopt">\n'
            '          <input type="radio" name="metadata__level" value="b" checked>\n'
            '          <span class="lv-t">중급 <span class="lv-chk">&#10003;</span></span>\n'
            f'          <span class="lv-r">{range_b}</span>\n'
            f'          <span class="lv-d">{desc_b}</span>\n'
            '        </label>\n'
            '      </fieldset>\n'
        )
    return (
        '  <section class="card sub" id="subscribe" data-v="3">\n'
        f"    <h2>매일 아침 {L['name']} 지문 받기</h2>\n"
        f"    <p>새 {L['name']} 지문이 올라오면 아침에 메일로 보내 드려요.</p>\n"
        f'    <form action="{SUBSCRIBE}" method="post" target="_blank">\n'
        f'      <input type="hidden" name="metadata__lang" value="{lang}">\n'
        + level_html +
        '      <input type="email" name="email" required placeholder="이메일 주소" autocomplete="email" aria-label="이메일 주소">\n'
        '      <button type="submit">구독하기</button>\n'
        "    </form>\n"
        "    <p class=\"note\">이미 구독 중이어도 같은 이메일로 다시 구독하면 수준과 언어가 바로 바뀌어요. 이메일 주소 하나로는 한 언어만 받을 수 있어요.</p>\n"
        "    <p class=\"note\">구독하면 영문 확인 메일(Confirm your subscription)이 가요. 메일 속 버튼을 눌러야 구독이 끝나요. 메일이 안 보이면 스팸함도 확인해 주세요.</p>\n"
        '    <p class="note">이메일은 뉴스레터 발송에만 쓰이고, 언제든 메일 하단에서 수신거부할 수 있어요.</p>\n'
        + _sub_script(lang) +
        "  </section>\n"
    )


def days_of(lang):
    d = ROOT / lang
    return sorted((p.name for p in d.iterdir() if DATE_RE.fullmatch(p.name) and (p / "index.html").exists()), reverse=True) if d.exists() else []


def topic_of(lang, day):
    page = (ROOT / lang / day / "index.html").read_text(encoding="utf-8")
    return html.unescape(re.search(r"<h1>.*?<em>(.*?)</em>", page, re.S).group(1).strip())


# 기초(.en-a/.ko-a/.chunks-a)가 중급과 같은 글꼴, 해석, 끊어 읽기 모양을 갖도록 template.html 과 같은 줄로 바꾼다.
# 이 줄이 생기기 전에 만든 지난 페이지용(바뀐 줄은 다시 맞지 않으므로 여러 번 돌려도 같다).
LEVEL_A_CSS = [
    ("  .en { font-size: 18px;", "  .en, .en-a { font-size: 18px;"),
    ("  .ko { font-size: 16px;", "  .ko, .ko-a { font-size: 16px;"),
    ("  #passage .ko { font-size: 14px;", "  #passage .ko, #passage .ko-a { font-size: 14px;"),
    ("  #passage .sent.playing .en {", "  #passage .sent.playing .en, #passage .sent.playing .en-a {"),
    ("  #passage .chunks { display: none; flex-wrap: wrap; gap: 6px 0; cursor: pointer; }\n",
     "  #passage .chunks { display: none; flex-wrap: wrap; gap: 6px 0; cursor: pointer; }\n"
     "  #passage .chunks-a { flex-wrap: wrap; gap: 6px 0; cursor: pointer; }\n"),
    ("  body.chunked #passage .say > .en { display: none; }",
     "  body.chunked #passage .say > .en, body.chunked #passage .say > .en-a { display: none; }"),
    ("  body.chunked #passage .say > .ko { display: none !important; }",
     "  body.chunked #passage .say > .ko, body.chunked #passage .say > .ko-a { display: none !important; }"),
]


def label(day):
    return date_label(day)


# 화면 날짜(시안 design/seo-ui S04): 예전 <div class="date">11월 12일 목요일</div> 를
# <time class="date" datetime="2026-11-12">2026년 11월 12일 목요일</time> 로. 분야 배지는 그대로 둔다(여러 번 돌려도 같다)
DATE_TAG_RE = re.compile(r'<(div|time) class="date"[^>]*>[^<]*?((?: ?<span class="cat[^"]*">[^<]*</span>)?)</\1>')
DATE_CSS_OLD = "  .date { font-size: 14px;"
DATE_CSS_NEW = "  .date { display: block; font-size: 14px;"
MADE_CSS = "  .made { font-size: 13px; color: var(--muted); margin: 4px 0 0; line-height: 1.6; }\n"
SRC_RE = re.compile(r'( *<p class="src">.*?</p>\n)', re.S)
# 출처 제목 끝 괄호 "(매체, YYYY-MM-DD)", "(매체)", "(꼭지 이름, 매체)"
SRC_TAIL_RE = re.compile(r"\(([^()]+)\)\s*$")
INTRO_SRC_RE = re.compile(r'(<p class="intro">[^<]*?예요\.)(?: 출처: [^<]*?)?( 듣고, 해석하고)')


def date_tag(page, day):
    return DATE_TAG_RE.sub(lambda m: f'<time class="date" datetime="{day}">{date_label(day)}{m.group(2)}</time>', page, count=1)


def source_phrase(c):
    """소개 문단에 덧붙일 출처 매체 한 마디(시안 S03 B): "출처: Live Science(2013년 1월 9일 기사)." 출처가 없거나 매체를 못 읽으면 빈 문자열."""
    m = SRC_TAIL_RE.search(((c.get("source") or {}).get("title") or ""))
    if not m:
        return ""
    parts = [p.strip() for p in m.group(1).split(",")]
    day = parts.pop() if len(parts) > 1 and DATE_RE.fullmatch(parts[-1]) else None
    medium = parts[-1]
    if not medium or medium.isdigit():
        return ""
    if day:
        d = dt.date.fromisoformat(day)
        return f" 출처: {medium}({d.year}년 {d.month}월 {d.day}일 기사)."
    return f" 출처: {medium}."


def intro_source(page, c):
    return INTRO_SRC_RE.sub(lambda m: m.group(1) + html.escape(source_phrase(c), quote=False) + m.group(2), page, count=1)


# 다른 날 지문 카드(시안 design/seo-ui S10 A): 구독 카드 바로 위. 같은 언어 이전, 다음 지문. 최신 지문의 다음 칸은 안내 문구
PN_RE = re.compile(r' *<nav class="card pn" [^>]*>.*?</nav>\n', re.S)
PN_CSS_RE = re.compile(r"  /\* pn-css \*/\n.*?  /\* /pn-css \*/\n", re.S)
PN_ARROW = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 6l6 6-6 6"/></svg>'
PN_CLOCK = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/></svg>'
PN_CSS = (
    "  /* pn-css */\n"
    "  .pn .pn-h { font-size: 17px; margin: 0 0 12px; }\n"
    "  .pn-i { display: flex; gap: 12px; align-items: center; padding: 12px 0; border-top: 1px solid #e5e8eb; color: inherit; text-decoration: none; }\n"
    "  .pn-h + .pn-i { border-top: 0; padding-top: 0; }\n"
    "  .pn-i img { width: 76px; height: 76px; border-radius: 12px; object-fit: cover; flex: none; background: var(--bg); }\n"
    "  .pn-t { display: flex; flex-direction: column; align-items: flex-start; gap: 3px; min-width: 0; }\n"
    "  .pn-d { font-size: 13px; font-weight: 600; color: var(--muted); }\n"
    "  .pn-d b { color: var(--sub); font-weight: 600; }\n"
    "  .pn-n { font-size: 16px; font-weight: 700; color: var(--ink); line-height: 1.4; }\n"
    "  .pn .cat { margin-left: 0; }\n"
    "  .pn-wait .pn-n { color: var(--muted); font-weight: 600; font-size: 15px; }\n"
    "  .pn-ic { width: 76px; height: 52px; border-radius: 12px; background: var(--bg); color: var(--muted); display: flex; align-items: center; justify-content: center; flex: none; }\n"
    "  .pn-all { display: flex; align-items: center; justify-content: center; gap: 2px; height: 48px; margin-top: 12px; border-radius: 12px; background: var(--bg); font-size: 15px; font-weight: 700; color: var(--sub); text-decoration: none; }\n"
    "  .pn svg { width: 16px; height: 16px; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; flex: none; }\n"
    "  .pn-ic svg { width: 22px; height: 22px; }\n"
    "  /* /pn-css */\n"
)


def neighbors(lang, day):
    """같은 언어에서 바로 앞, 뒤 날짜의 지문(페이지가 있는 날만). 없으면 None."""
    days = sorted(days_of(lang))
    if day not in days:
        return None, None
    i = days.index(day)
    return (days[i - 1] if i > 0 else None), (days[i + 1] if i + 1 < len(days) else None)


def pn_item(lang, d, kind):
    """이전/다음 지문 한 줄. 사진은 정사각 썸네일, 정사각 사진이 없으면 사진, 사진이 없는 날은 분야 일러스트 썸네일."""
    e = entry(lang, d)
    cf = ROOT / "content" / lang / f"{d}.json"
    c = json.loads(cf.read_text(encoding="utf-8")) if cf.exists() else {}
    name = c.get("title_ko") or e["topic"]
    folder = ROOT / lang / d
    src = next((f for f in ("thumb-sq.jpg", "photo.jpg", "thumb.png") if (folder / f).exists()), None)
    img = f'<img src="../{d}/{src}" width="76" height="76" alt="" loading="lazy" decoding="async">' if src else ""
    return (f'    <a class="pn-i" href="../{d}/">{img}<span class="pn-t"><span class="pn-d">{kind} <b>{date_label(d)}</b></span>'
            f'<span class="pn-n">{html.escape(name, quote=False)}</span><span class="cat cat-{e["cat"]}">{e["cat_label"]}</span></span></a>\n')


def pn_html(lang, day):
    L = langs.get(lang)
    prev, nxt = neighbors(lang, day)
    rows = pn_item(lang, prev, "이전 지문") if prev else ""
    if nxt:
        rows += pn_item(lang, nxt, "다음 지문")
    else:
        rows += (f'    <div class="pn-i pn-wait"><span class="pn-ic">{PN_CLOCK}</span><span class="pn-t"><span class="pn-d">다음 지문</span>'
                 f'<span class="pn-n">내일 아침에 새 {L["name"]} 지문이 올라와요</span></span></div>\n')
    return ('  <nav class="card pn" aria-label="이전, 다음 지문">\n    <h2 class="pn-h">다른 날 지문</h2>\n' + rows
            + f'    <a class="pn-all" href="../archive/">{L["name"]} 지난 지문 전체 보기{PN_ARROW}</a>\n  </nav>\n')


def apply_pn(page, lang, day):
    """다른 날 지문 카드를 구독 카드 바로 위(없으면 </main> 앞)에 넣는다. 있던 카드는 이웃 날짜에 맞춰 다시 만든다(여러 번 돌려도 같다)."""
    page = PN_RE.sub("", page, count=1)
    # CSS 는 있던 자리에서 바꾼다(지우고 다시 넣으면 다른 블록과 순서가 바뀌어 매번 결과가 달라진다)
    if PN_CSS_RE.search(page):
        page = PN_CSS_RE.sub(lambda m: PN_CSS, page, count=1)
    else:
        page = page.replace("  .gnb {", PN_CSS + "  .gnb {", 1)
    nav = pn_html(lang, day)
    anchor = '  <section class="card sub"' if '  <section class="card sub"' in page else "</main>"
    return page.replace(anchor, nav + anchor, 1)


LEVEL_HEAD_OLD = "<script>try{var _ql=new URLSearchParams(location.search).get('level');if(!_ql)_ql=localStorage.getItem('read_level');if(_ql==='a')document.documentElement.classList.add('level-a')}catch(e){}</script>"
LEVEL_HEAD_NEW = "<script>try{var _lc=location.pathname.split('/')[1]||'en';var _ql=new URLSearchParams(location.search).get('level');if(!_ql){_ql=localStorage.getItem('read_level:'+_lc);if(!_ql&&_lc==='en'){var _old=localStorage.getItem('read_level');if(_old){_ql=_old;localStorage.setItem('read_level:en',_old);localStorage.removeItem('read_level');}}}if(_ql==='a')document.documentElement.classList.add('level-a')}catch(e){}</script>"


# AI 피드백 안내에서 특정 AI 서비스 이름을 빼고 '평소 쓰는 AI 채팅'으로 부른다(예전 페이지 갱신용)
MODEL_NAMES = (("ChatGPT나 Claude 같은 AI 채팅에", "평소 쓰는 AI 채팅에"), ("AI 채팅(ChatGPT, Claude 등)에", "AI 채팅에"))


# 글자색은 접근성 대비 기준(tests/test_a11y_b1_contrast.py)에 맞춰 하단 링크 줄과 같은 #6b7684
CREDIT_CSS = "  .site-footer .credit { flex-basis: 100%; font-size: 12px; color: #6b7684; }\n"


def credit_to_footer(page, lang):
    """음성 크레딧(이용 조건으로 표기해야 함)을 듣기 안내 줄 끝에서 하단 링크 줄 아래로 옮긴다(design/ja-credit J01).
    크레딧이 없는 언어나 하단 링크가 없는 페이지는 그대로 둔다. 여러 번 돌려도 같다."""
    credit = langs.LANGS.get(lang, {}).get("credit")
    if not credit or '<footer class="site-footer">' not in page:
        return page
    text = html.escape(credit)
    page = page.replace(f" {text}</p>", "</p>").replace(f" {credit}</p>", "</p>")
    span = f'<span class="credit">{text}</span>'
    if span not in page:
        at = page.index('<footer class="site-footer">')
        end = page.index("</footer>", at)
        page = page[:end] + span + page[end:]
    if CREDIT_CSS not in page:
        at = page.find("</style>", max(page.find(".site-footer {"), 0))
        page = page[:at] + CREDIT_CSS + page[at:]
    return page


def edu_level(label):
    """수준 표기에 체계 이름을 붙인다: "B1~B2" -> "CEFR B1~B2", "JLPT N3" 은 그대로, "기초 N4~N5" -> "JLPT N4~N5"."""
    v = label.replace("기초", "").strip()
    return v if v.startswith(("JLPT", "CEFR")) else (f"JLPT {v}" if v.startswith("N") else f"CEFR {v}")


ORG_ID = f"{SITE}/#organization"
WEBSITE_ID = f"{SITE}/#website"


def site_nodes():
    """운영 주체(Organization)와 사이트(WebSite) 노드. 랜딩(layout.tsx)과 같은 @id, 이름, 로고, sameAs 를 짧게 다시 정의해
    지문, 목록, 복습 페이지 안에서도 publisher, isPartOf 가 풀리게 한다(설명 같은 전체 정의는 랜딩에)."""
    return [
        {"@type": "Organization", "@id": ORG_ID, "name": langs.BRAND, "alternateName": langs.ALT_NAMES, "url": f"{SITE}/",
         "logo": {"@type": "ImageObject", "url": f"{SITE}/assets/brand/icon-512.png", "width": 512, "height": 512},
         "sameAs": langs.SAME_AS},
        {"@type": "WebSite", "@id": WEBSITE_ID, "name": langs.BRAND_ROOT, "url": f"{SITE}/", "publisher": {"@id": ORG_ID}},
    ]


def ld_script(nodes):
    """<script id="ld"> 블록. </script> 로 블록이 끊기지 않게 "</" 를 막는다."""
    data = json.dumps({"@context": "https://schema.org", "@graph": nodes}, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return f'<script type="application/ld+json" id="ld">{data}</script>\n'


def crumbs_ld(*pairs):
    """BreadcrumbList: (이름, 주소) 쌍을 순서대로."""
    return {"@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": i, "name": n, "item": u} for i, (n, u) in enumerate(pairs, 1)]}


def reading_ld(lang, day, c, topic, desc):
    """지문 날짜 페이지 구조화 데이터: Article + LearningResource 와 BreadcrumbList, 운영 주체와 사이트 노드.
    값은 content JSON 에 실제로 있는 것만 쓴다(출처가 없는 날은 isBasedOn 을 넣지 않는다)."""
    L = langs.get(lang)
    url = f"{SITE}/{lang}/{day}/"
    org = {"@id": ORG_ID}
    levels = [edu_level(langs.level_on(lang, day))]
    if (c.get("levels") or {}).get("a"):
        levels.append(edu_level(L.get("level_a_label", "기초 A2~B1")))
    images = [f"{url}{f}" for f in ("photo.jpg", "thumb.png") if (ROOT / lang / day / f).exists()]
    summary = c.get("summary_ko")
    summary = summary.strip() if isinstance(summary, str) else ""
    article = {
        "@type": ["Article", "LearningResource"],
        "@id": f"{url}#reading",
        "mainEntityOfPage": url,
        "url": url,
        "headline": topic,
        "alternativeHeadline": re.sub(r"\{([^{}|]+)\|[^{}|]+\}", r"\1", c["headline"]).replace("**", "") if c.get("headline") else None,
        "description": desc,
        # 화면 맨 위 요약(content 의 선택 필드 summary_ko, 시안 S03 B)이 있는 날만
        "abstract": summary or None,
        "datePublished": day,
        "dateModified": day,
        "inLanguage": lang,
        "image": images or None,
        "keywords": c.get("keywords") or None,
        "articleSection": thumb.CATS[c["category"]][0] if c.get("category") in thumb.CATS else None,
        "learningResourceType": "reading passage",
        "educationalLevel": levels if len(levels) > 1 else levels[0],
        "teaches": f"{L['name']} 독해",
        "isAccessibleForFree": True,
        "isBasedOn": ({"@type": "CreativeWork", "name": c["source"]["title"], "url": c["source"]["url"]}
                      if (c.get("source") or {}).get("url") else None),
        "author": org,
        "publisher": org,
        "isPartOf": {"@id": WEBSITE_ID},
    }
    d = dt.date.fromisoformat(day)
    crumbs = crumbs_ld((langs.BRAND, f"{SITE}/"), (f"{L['name']} 지문", f"{SITE}/{lang}/"), (f"{d.year}년 {d.month}월 {d.day}일", url))
    return ld_script([{k: v for k, v in article.items() if v is not None}, crumbs, *site_nodes()])


LD_RE = re.compile(r'<script type="application/ld\+json" id="ld">.*?</script>\n', re.S)
# 새 지문 피드 자동 발견. 지문 페이지(template.html 과 patch_page)와 목록 페이지(ARCHIVE)에 같은 줄을 둔다
ICON_LINKS = '<link rel="apple-touch-icon" href="/apple-icon.png">\n'
RSS_LINK = f'<link rel="alternate" type="application/rss+xml" title="{langs.BRAND}" href="/rss.xml">\n'
PRECONNECT = '<link rel="preconnect" href="https://cdnjs.cloudflare.com" crossorigin>\n'
# 일본어는 Google Fonts(Noto Sans JP) CSS 와 글꼴 파일 서버에도 미리 연결한다
PRECONNECT_JA = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
                 '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n')


def patch_page(lang, day):
    L = langs.get(lang)
    path = ROOT / lang / day / "index.html"
    page = path.read_text(encoding="utf-8")
    url = f"{SITE}/{lang}/{day}/"
    cfile = ROOT / "content" / lang / f"{day}.json"
    c = json.loads(cfile.read_text(encoding="utf-8")) if cfile.exists() else {}
    page = date_tag(page, day)
    if DATE_CSS_NEW not in page:
        page = page.replace(DATE_CSS_OLD, DATE_CSS_NEW, 1)
    # 주제를 포함한 메타 설명 (새 페이지/기존 페이지 공통으로 계산). 주제는 content 의 title_ko(h1 과 같은 값)를 먼저 쓴다
    try:
        m_topic = re.search(r"<h1>.*?<em>(.*?)</em>", page, re.S)
        topic_text = c.get("title_ko") or (html.unescape(m_topic.group(1).strip()) if m_topic else topic_of(lang, day))
    except Exception:
        topic_text = ""
    new_desc = f"{langs.level_on(lang, day)} {L['name']} 읽기 — {topic_text}. 문장별 음성과 모범 해석으로 하루 한 단락을 공부해요."
    if 'property="og:image"' not in page:
        title = html.escape(page_title(lang, day, topic_text), quote=True)
        desc_esc = html.escape(new_desc, quote=True)
        meta = (
            f'<meta name="description" content="{desc_esc}">\n'
            f'<meta property="og:type" content="article">\n'
            f'<meta property="og:site_name" content="{L["site"]}">\n'
            f'<meta property="og:title" content="{title}">\n'
            f'<meta property="og:description" content="{desc_esc}">\n'
            f'<meta property="og:url" content="{url}">\n'
            f'<meta property="og:image" content="{url}thumb.png">\n'
            f'<meta property="og:image:width" content="1200">\n'
            f'<meta property="og:image:height" content="630">\n'
            f'<meta name="twitter:card" content="summary_large_image">\n'
        )
        page = page.replace("<link rel=\"stylesheet\"", meta + "<link rel=\"stylesheet\"", 1)
    else:
        # 기존 페이지: 주제를 포함한 메타 설명으로 갱신 (멱등)
        desc_esc = html.escape(new_desc, quote=True)
        page = re.sub(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{desc_esc}">', page, count=1)
        page = re.sub(r'<meta property="og:description" content="[^"]*">', f'<meta property="og:description" content="{desc_esc}">', page, count=1)
    photo = (ROOT / lang / day / "photo.jpg").exists()
    if photo and 'class="hero"' not in page:
        # 사진이 있는 날은 OG 썸네일(글씨, 그림자가 든 thumb.png) 대신 글 없는 사진을 카드 맨 위 배너로(시안 design/article-thumb P1)
        page = re.sub(r'<img class="thumb"[^>]*>\n\s*', "", page, count=1)
        page = page.replace(
            "  .gnb {",
            "  .top { position: relative; }\n  .top .hero { margin: -28px -20px 20px; aspect-ratio: 40 / 21; overflow: hidden; border-radius: var(--card-r) var(--card-r) 0 0; background: var(--bg); }\n"
            "  .top .hero img { display: block; width: 100%; height: 100%; object-fit: cover; }\n  .gnb {",
            1,
        )
        page = page.replace('<time class="date"', '<div class="hero"><img src="photo.jpg" width="1200" height="630" alt=""></div>\n    <time class="date"', 1)
    if not photo and 'class="thumb"' not in page and 'class="hero"' not in page:
        page = page.replace(
            "  .gnb {",
            "  .top { position: relative; }\n  .thumb { position: absolute; top: 18px; right: 18px; width: 76px; height: 76px; object-fit: cover; object-position: 100% 50%; }\n  .gnb {",
            1,
        )
        page = page.replace(
            '<time class="date"',
            f'<img class="thumb" src="thumb.png" width="76" height="76" alt="">\n    <time class="date"',
            1,
        )
    # 제목과 og:title: 주제, 언어와 수준, 연도(render.page_title). 예전 "○○ 읽기, 10월 20일" 제목도 이 문구로 바꾼다
    title_esc = html.escape(page_title(lang, day, topic_text), quote=True)
    page = re.sub(r"<title>[^<]*</title>", lambda m: f"<title>{title_esc}</title>", page, count=1)
    page = re.sub(r'<meta property="og:title" content="[^"]*">', lambda m: f'<meta property="og:title" content="{title_esc}">', page, count=1)
    # og:site_name 을 전체 브랜드+서비스명으로 교체
    page = re.sub(
        r'(<meta property="og:site_name" content=")[^"]+(")',
        rf'\1{html.escape(L["site"])}\2',
        page, count=1,
    )
    # favicon: icon.svg → icon-32.png (이미 교체됐으면 건드리지 않는다)
    if 'href="/icon-32.png"' not in page:
        page = page.replace(
            '<link rel="icon" href="/icon.svg" type="image/svg+xml">',
            '<link rel="icon" href="/icon-32.png" sizes="32x32" type="image/png">',
            1,
        )
    # 공개로 바뀐 언어(독일어, 2026-10-30)의 지난 페이지에서 검색엔진 숨김을 걷는다
    if not L.get("noindex", False):
        page = page.replace('<meta name="robots" content="noindex">\n', "", 1)
    # 다른 언어 지난 지문 알약 줄(이슈 #19)과 예전 '다른 언어' 링크는 위 메뉴 언어 시트로 옮겼다(시안 A, 이슈 #20)
    page = page.replace('<a href="../../">다른 언어</a>', "", 1)
    page = re.sub(r'[ \t]*<p class="lang-row">.*?</p>\n', "", page, count=1)
    page = re.sub(r'<a class="lang-go" href="[^"]*">[^<]*</a>', "", page)
    page = re.sub(r"  \.intro a\.lang-go \{[^}]*\}\n", "", page)
    # 소개 문단 끝 '메일로 받기'도 위 메뉴로 옮겼다
    page = re.sub(r'(<p class="intro">[^<]*?) ?<a href="#subscribe">메일로 받기</a>(</p>)', r"\1\2", page, count=1)
    # 주소(og:url, og:image, canonical)를 지금 SITE 로 맞춘다(도메인 변경 반영, 멱등)
    page = re.sub(r'<meta property="og:url" content="[^"]*">', lambda m: f'<meta property="og:url" content="{url}">', page, count=1)
    page = re.sub(r'(<meta property="og:image" content=")https?://[^/"]+/', lambda m: f"{m.group(1)}{SITE}/", page, count=1)
    page = re.sub(r'<link rel="canonical" href="[^"]*">', lambda m: f'<link rel="canonical" href="{url}">', page, count=1)
    # 구독 폼 주소도 지금 Buttondown 계정 주소로 맞춘다(계정 이름을 바꾼 뒤 지난 페이지 반영)
    page = re.sub(r'https://buttondown\.com/api/emails/embed-subscribe/[A-Za-z0-9_-]+', SUBSCRIBE, page)
    if 'class="site-footer"' not in page:
        page = page.replace("  .gnb {", "  " + FOOTER_CSS + "  .site-footer { padding-bottom: 32px; }\n  .gnb {", 1)
        page = page.replace("</main>", "</main>\n" + FOOTER_HTML, 1)
        page = page.replace("<link rel=\"stylesheet\"", f'<link rel="canonical" href="{url}">\n<link rel="stylesheet"', 1)
    page = page.replace(OLD_FOOTER_LINKS, footer_links(), 1)
    L_pub = langs.LANGS.get(lang, {})
    if 'class="card sub"' not in page:
        # 카드가 없는 경우: email=False 언어는 구독 카드를 삽입하지 않는다(숨김 운영 중).
        # noindex 여부와 무관하게 email=True 면 카드를 삽입한다(de: noindex=True, email=True).
        if not L_pub.get("email", True):
            pass
        else:
            page = page.replace("  .gnb {", SUB_CSS + "  .intro {", 1)
            page = page.replace("  .intro {", INTRO_CSS + "  .gnb {", 1)
            page = page.replace("</main>", sub_html(lang) + "</main>", 1)
            page = page.replace(TOP_END, "\n" + intro_html(lang) + TOP_END[1:], 1)
    elif 'data-v="3"' not in page or (L_pub.get("levels") and not re.search(r'<input[^>]+name="metadata__level"', page)):
        # 수준 선택이 새로 생긴 언어(ja, 2026-10-29)의 지난 페이지 카드도 같은 방식으로 바꾼다.
        # 이전 버전 카드가 있는 경우: 카드 HTML만 교체하고 수준 선택 CSS를 추가한다
        page = re.sub(
            r'<section class="card sub"[^>]*id="subscribe"[^>]*>.*?</section>',
            sub_html(lang).strip(),
            page,
            count=1,
            flags=re.S,
        )
        # 수준 선택 CSS가 없으면 기존 .sub .note 앞에 추가하고, .sub form 에 flex-wrap 도 반영한다
        if ".sub .levels {" not in page:
            # flex-wrap 이 없는 이전 form CSS 도 교체 (→ 좁은 화면에서 이메일 입력란이 보이도록)
            page = page.replace(
                "  .sub form { display: flex; gap: 8px; }\n",
                "  .sub form { display: flex; flex-wrap: wrap; gap: 8px; }\n",
                1,
            )
            page = page.replace(
                "  .sub input { flex: 1;",
                "  .sub input[type='email'] { flex: 1 1 auto;",
                1,
            )
            SUB_EXTRA = (
                "  .sub .levels { flex-basis: 100%; display: flex; flex-direction: column; gap: 8px; margin: 0; border: 0; padding: 0; }\n"
                "  .sub .levels legend { font-size: 14px; font-weight: 600; margin: 0 0 8px; padding: 0; }\n"
                "  .sub .lvopt { display: flex; flex-direction: column; gap: 3px; border: 1.5px solid #e2e6ea; border-radius: 10px;"
                " padding: 12px 14px; cursor: pointer; text-align: left; background: #f4f6f8; position: relative; width: 100%; box-sizing: border-box; }\n"
                "  .sub .lvopt input[type='radio'] { position: absolute; opacity: 0; width: 1px; height: 1px; pointer-events: none; }\n"
                "  .sub .lvopt:has(input:checked),.sub .lvopt[data-checked] { background: #eff3fd; border-color: #2a52d4; }\n"
                "  .sub .lvopt .lv-t { font-size: 15px; font-weight: 700; display: flex; justify-content: space-between; align-items: center; }\n"
                "  .sub .lvopt .lv-r { font-size: 12px; color: var(--muted); }\n"
                "  .sub .lvopt .lv-d { font-size: 13px; color: var(--sub); margin-top: 2px; }\n"
                "  .sub .lvopt .lv-chk { width: 18px; height: 18px; border-radius: 50%; border: 1.5px solid #c5ccd6; flex: none;"
                " display: flex; align-items: center; justify-content: center; color: transparent; }\n"
                "  .sub .lvopt:has(input:checked) .lv-chk,.sub .lvopt[data-checked] .lv-chk { background: #2a52d4; border-color: #2a52d4; color: #fff; }\n"
            )
            page = page.replace("  .sub .note {", SUB_EXTRA + "  .sub .note {", 1)
    page = intro_source(page, c)
    # AI 초안 표기(시안 S06 A, 링크 없이): 출처 줄 바로 아래 회색 한 줄
    if 'class="made"' not in page:
        page = SRC_RE.sub(lambda m: m.group(1) + MADE_HTML, page, count=1)
    if ".made {" not in page:
        page = page.replace("  .src a {", MADE_CSS + "  .src a {", 1)
    # 영어 기초 지문이 매일 나오므로 지난 페이지의 "기초 지문은 준비 중" 안내를 지운다(이슈 #27)
    page = re.sub(r' *<p class="note level-note">.*?</p>\n', "", page, count=1)
    if "#passage .chunks-a {" not in page:
        for old, new in LEVEL_A_CSS:
            page = page.replace(old, new, 1)
    page = vote.apply(page, lang, day)  # 오늘 분야 배지와 주제 반응 카드(#13)
    page = apply_pn(page, lang, day)
    # 수준 설정을 언어별로 저장한다(read_level:en 등). 템플릿만 바꾸면 지난 페이지에는 옛 공용 키가 남아 언어끼리 섞였다
    page = page.replace(LEVEL_HEAD_OLD, LEVEL_HEAD_NEW, 1)
    page = page.replace("localStorage.setItem('read_level', lp);", "localStorage.setItem('read_level:' + _gaLang, lp);")
    page = page.replace("localStorage.setItem('read_level', to);", "localStorage.setItem('read_level:' + _gaLang, to);")
    page = drill.apply(page, lang, day)  # 단어 암기 반복과 복습 띠(#16)
    # a11y-b1-contrast: 대비 상향, .no 버튼 B1 크기 (모든 기존 페이지 멱등 반영)
    page = page.replace("color: #8b95a1; display: flex; flex-wrap: wrap; gap: 6px 16px; } .site-footer",
                        "color: #6b7684; display: flex; flex-wrap: wrap; gap: 6px 16px; } .site-footer")
    page = page.replace("--muted: #8b95a1", "--muted: #6b7684", 1)
    page = page.replace("--blue: #3182f6", "--blue: #1b64da", 1)
    page = page.replace("--blue-press: #1b64da", "--blue-press: #1550b8", 1)
    page = page.replace(
        ".no { flex: none; width: 24px; height: 24px; margin-top: 4px; border-radius: 8px;\n"
        "        background: var(--bg); color: var(--sub); font-size: 13px; font-weight: 700;\n"
        "        display: grid; place-items: center; }",
        ".no { flex: none; width: 32px; height: 32px; margin-top: 0; border-radius: 10px;\n"
        "        background: var(--bg); color: var(--sub); font-size: 13px; font-weight: 700;\n"
        "        display: grid; place-items: center; position: relative; }\n"
        "  .no::before { content: \'\'; position: absolute; inset: -6px; }",
        1,
    )
    # 읽기 수준: 예전 '기초로 보기' 링크를 카드 맨 아래 [기초|중급] 세그먼트로(시안 A G01). 저장 키 read_level:<언어> 는 그대로
    if 'id="to-level-a"' in page:
        page = re.sub(r'<p class="level-link" id="level-link">.*?</p>\n', "", page, count=1)
        page = page.replace(LEVEL_SEG, "", 1)
        page = page.replace(TOP_END, "\n" + LEVEL_SEG + TOP_END[1:], 1)
        page = page.replace("      toLevelA.hidden = isA;\n      toLevelB.hidden = !isA;\n",
                            "      // 켜진 쪽 모양은 CSS(html.level-a)가 정한다. 여기서는 화면 읽기 프로그램용 표시만 맞춘다\n"
                            "      toLevelA.setAttribute('aria-current', String(isA));\n"
                            "      toLevelB.setAttribute('aria-current', String(!isA));\n", 1)
    # 위 메뉴(시안 A): 화면 위에 붙은 흰 바, 언어 칩 시트, PC 언어 탭. 예전 떠 있는 바와 그 CSS 는 지운다
    mail = "#subscribe" if 'id="subscribe"' in page else f"/{lang}/#subscribe"
    for old, new in MODEL_NAMES:
        page = page.replace(old, new)
    page = gnb.apply(page, lang, mail, day=True)
    page = credit_to_footer(page, lang)
    # 의견 보내기(이슈 #21): 하단 링크 위 기능 건의, 버그 제보 버튼
    page = feedback.apply(page, lang, url)
    # 구역 도달 측정(이슈 #24, 문법 섹션 0단계)
    page = track.apply(page)
    # 재생바 이동(이슈 #26)
    page = seek.apply(page)
    # 구조화 데이터(JSON-LD): 있으면 통째로 바꾸고 없으면 첫 stylesheet 앞에 넣는다(지난 페이지 백필, 도메인 변경 반영)
    ld = reading_ld(lang, day, c, topic_text, new_desc)
    if LD_RE.search(page):
        page = LD_RE.sub(lambda m: ld, page, count=1)
    else:
        page = page.replace('<link rel="stylesheet"', ld + '<link rel="stylesheet"', 1)
    if 'type="application/rss+xml"' not in page:
        page = page.replace(ICON_LINKS, ICON_LINKS + RSS_LINK, 1)
    # 글꼴 CDN 미리 연결과 첫 화면 사진 우선 로딩(LCP)
    if 'href="https://cdnjs.cloudflare.com" crossorigin' not in page:
        page = page.replace('<link rel="stylesheet" href="https://cdnjs.cloudflare.com', PRECONNECT + '<link rel="stylesheet" href="https://cdnjs.cloudflare.com', 1)
    if lang == "ja" and PRECONNECT_JA not in page:
        page = page.replace('<link rel="stylesheet" href="https://fonts.googleapis.com', PRECONNECT_JA + '<link rel="stylesheet" href="https://fonts.googleapis.com', 1)
    page = page.replace('<div class="hero"><img src="photo.jpg" width="1200" height="630" alt="">',
                        '<div class="hero"><img src="photo.jpg" width="1200" height="630" alt="" fetchpriority="high">', 1)
    page = migrate.apply(page)  # 예전 주소의 학습 기록 받기
    path.write_text(page, encoding="utf-8")


def redirect(to, title):
    return ('<!doctype html>\n<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f'<title>{title}</title><meta http-equiv="refresh" content="0; url={to}"><link rel="canonical" href="{to}"></head>\n'
            f'<body><p><a href="{to}">{title}(으)로 이동</a></p></body></html>\n')


def rebuild_lists(lang):
    L = langs.get(lang)
    days = days_of(lang)
    latest = days[0]
    entries = [entry(lang, d) for d in days]
    rdir = ROOT / lang / "review"
    reviews = sorted((p.name for p in rdir.glob("*") if p.is_dir()), reverse=True) if rdir.exists() else []
    cats = [c for c in thumb.CATS if any(e["cat"] == c for e in entries)]
    chips = "".join(
        f'<button type="button" class="chip" data-cat="{c}" aria-pressed="false">{thumb.CATS[c][0]}</button>' for c in cats
    )
    for out, p, home, title in ((ROOT / lang, "./", "../", f"{L['name']} 지문"),
                                (ROOT / lang / "archive", "../", "../../", f"{L['name']} 지난 지문")):
        sub = "archive/" if p == "../" else ""
        tabs = "".join(f'<a href="/{c}/{sub}"' + (' class="on" aria-current="page"' if c == lang else "") + f'>{langs.LANGS[c]["name"]}</a>'
                       for c in public_langs(lang))
        groups, month = [], None
        for e in entries:
            if e["month"] != month:
                if month is not None:
                    groups.append("    </div>\n  </section>")
                month = e["month"]
                groups.append(f'  <section class="month">\n    <h2>{month}</h2>\n    <div class="card">')
            # 사진이 있는 날은 글 없는 사진을 둥근 네모로(시안 P4), 없는 날은 예전 일러스트 썸네일
            # thumb-sq.jpg(112×112 중앙 잘라낸 정사각 사진)가 있으면 우선 쓴다(용량이 더 작고 비율이 맞음)
            if (ROOT / lang / e["day"] / "thumb-sq.jpg").exists():
                img = f'<img class="ph" src="{p}{e["day"]}/thumb-sq.jpg" width="56" height="56" alt="" loading="lazy">'
            elif (ROOT / lang / e["day"] / "photo.jpg").exists():
                img = f'<img class="ph" src="{p}{e["day"]}/photo.jpg" width="56" height="56" alt="" loading="lazy">'
            else:
                img = f'<img src="{p}{e["day"]}/thumb.png" width="56" height="56" alt="" loading="lazy">'
            groups.append(
                f'      <a class="item" href="{p}{e["day"]}/" data-cat="{e["cat"]}" data-q="{html.escape(e["q"])}">'
                f'{img}'
                f'<span><span class="d">{e["label"]}<span class="c">{e["cat_label"]}</span></span>'
                f'<span class="t">{html.escape(e["topic"])}</span></span></a>'
            )
        groups.append("    </div>\n  </section>")
        review = (f'  <a class="review" href="{p}review/{reviews[0]}/"><span>이번 주 단어 복습</span><span>→</span></a>\n' if reviews else "")
        meta_desc_raw = f"{L['intro']} 지금까지 {len(entries)}편 수록."
        meta_desc = html.escape(meta_desc_raw, quote=True)
        # 지난 지문(/archive/)은 언어 첫 화면과 목록이 같아 canonical 을 언어 첫 화면으로 모은다(사이트맵에서도 뺀다)
        canonical = f"{SITE}/{lang}/"
        page_url = canonical if p == "./" else f"{SITE}/{lang}/archive/"
        ld = list_ld(lang, entries, meta_desc_raw)
        page = (ARCHIVE.replace("__REVIEW__", review).replace("__OG_IMAGE__", f"{SITE}/{lang}/{latest}/thumb.png")
                .replace("__TITLE__", title).replace("__ARCHIVE__", f"{p}archive/" if p == "./" else "./").replace("__TODAY__", f"{p}{latest}/").replace("__HOME__", home)
                .replace("__NAME__", L["name"]).replace("__GNB_CSS__", gnb.css_block()).replace("__BRAND__", langs.BRAND)
                .replace("__GNB__", gnb.header_html(lang, "#subscribe", on_archive=p == "../")).replace("__GNB_JS__", gnb.SCRIPT)
                .replace("__SITE__", L["site"]).replace("__INTRO__", L["intro"]).replace("__SEARCH_EXAMPLE__", L["search_example"])
                .replace("__CHIPS__", chips).replace("__LANGTABS__", tabs).replace("__SUB_CSS__", SUB_CSS).replace("__INTRO_CSS__", INTRO_CSS)
                .replace("__SUB_HTML__", sub_html(lang)).replace("__GROUPS__", "\n".join(groups))
                .replace("__META_DESC__", meta_desc).replace("__CANONICAL__", canonical).replace("__FOOTER_CSS__", "  " + FOOTER_CSS).replace("__FOOTER__", FOOTER_HTML)
                .replace("__LD__", ld).replace("__RSS__", RSS_LINK))
        page = feedback.apply(page, lang, page_url)
        page = migrate.apply(page)
        if L.get("noindex", False):
            page = page.replace('<link rel="stylesheet"', '<meta name="robots" content="noindex">\n<link rel="stylesheet"', 1)
        out.mkdir(parents=True, exist_ok=True)
        (out / "index.html").write_text(page, encoding="utf-8")


LIST_LD_SIZE = 30


def list_ld(lang, entries, desc):
    """언어 목록 페이지 구조화 데이터: CollectionPage + ItemList(최근 지문, 최신순) + BreadcrumbList.
    /archive/ 도 canonical 이 언어 첫 화면이라 @id, url 은 언어 첫 화면으로 같게 둔다."""
    L = langs.get(lang)
    url = f"{SITE}/{lang}/"
    recent = entries[:LIST_LD_SIZE]
    page = {
        "@type": "CollectionPage", "@id": f"{url}#page", "url": url, "name": f"{L['name']} 지문", "description": desc,
        "inLanguage": "ko-KR", "isPartOf": {"@id": WEBSITE_ID}, "publisher": {"@id": ORG_ID},
        "mainEntity": {
            "@type": "ItemList", "itemListOrder": "https://schema.org/ItemListOrderDescending", "numberOfItems": len(recent),
            "itemListElement": [{"@type": "ListItem", "position": i, "url": f"{url}{e['day']}/", "name": e["topic"]}
                                for i, e in enumerate(recent, 1)],
        },
    }
    return ld_script([page, crumbs_ld((langs.BRAND, f"{SITE}/"), (f"{L['name']} 지문", url)), *site_nodes()])


def entry(lang, day):
    """목록 한 줄에 필요한 값. content JSON 이 있으면 분야와 주요 단어까지 검색어에 넣는다."""
    d = dt.date.fromisoformat(day)
    content = ROOT / "content" / lang / f"{day}.json"
    c = json.loads(content.read_text(encoding="utf-8")) if content.exists() else {}
    topic = c.get("topic") or topic_of(lang, day)
    cat = c.get("category") or thumb.WEEKDAY[d.weekday()]
    plain = lambda t: re.sub(r"\{([^{}|]+)\|([^{}|]+)\}", r"\1 \2", t)  # 후리가나 표기는 한자와 읽기 둘 다 검색되게
    words = " ".join(f"{plain(w)} {m}" for w, m in c.get("words", []))
    return {
        "day": day, "topic": topic, "cat": cat, "cat_label": thumb.CATS[cat][0],
        "label": label(day), "month": f"{d.year}년 {d.month}월",
        # 날짜로도 찾게: "10월 20일", "10/20", "2026-10-20"
        "q": f"{topic} {thumb.CATS[cat][0]} {words} {label(day)} {d.month}/{d.day} {day}".lower(),
    }


def rebuild_root():
    """사이트 첫 화면이 읽는 latest.json 을 만든다. 첫 화면(index.html)은 landing 정적 빌드로 따로 배포한다.

    noindex 언어는 latest.json 의 langs/recent 에서 제외한다(검색엔진 숨김 운영 중).

    모양: {"date", "words_total"(올라간 지문 전체의 주요 단어 수),
           "langs": {code: {"count", "latest", "topic", "sentences"(앞 4문장, 원문 표기 그대로),
                            "chips", "answer"(1번 모범 해석), "words",
                            "review"(있을 때만: 가장 최근 주간 복습 {"day", "words", "desc"})}},
           "recent"(공개 언어마다 최근 7일. 첫 화면의 이번 주 달력과 주제 띠에 씀)}
    """
    data, recent = {"date": "", "words_total": 0, "langs": {}, "recent": []}, []
    for code in langs.LANGS:
        L = langs.LANGS[code]
        if L.get("noindex", False):
            continue  # 숨김 운영 중인 언어는 latest.json 에서 제외
        days = days_of(code)
        if not days:
            continue
        content = ROOT / "content" / code / f"{days[0]}.json"
        c = json.loads(content.read_text(encoding="utf-8")) if content.exists() else {}
        data["langs"][code] = {
            "count": len(days), "latest": days[0],
            "topic": c.get("topic") or topic_of(code, days[0]),
            "sentences": [s["en"] for s in c.get("sentences", [])[:4]],
            "chips": c.get("chips", []), "answer": (c.get("answers") or [""])[0], "words": c.get("words", []),
        }
        rv = gnb.latest_review(code)  # 위 메뉴 언어 시트의 '이번 주 단어 복습' 줄이 읽는다
        if rv:
            data["langs"][code]["review"] = {"day": rv[0], "words": rv[1], "desc": gnb.review_desc(code, rv[1])}
        data["date"] = max(data["date"], days[0])
        for d in days:
            f = ROOT / "content" / code / f"{d}.json"
            if f.exists():
                data["words_total"] += len(json.loads(f.read_text(encoding="utf-8")).get("words", []))
        recent += [{"lang": code, "day": d, "topic": entry(code, d)["topic"]} for d in days[:7]]
    order = list(langs.LANGS)
    data["recent"] = sorted(recent, key=lambda r: (r["day"], -order.index(r["lang"])), reverse=True)[:7 * len(data["langs"])]
    (ROOT / "latest.json").write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    try:  # 안내 페이지가 실패해도 지문 발행은 계속한다
        rebuild_info_pages()
    except Exception as e:
        print(f"::warning::안내 페이지 생성 실패: {type(e).__name__}: {e}")
    write_sitemap()


def root_lastmod(days):
    """첫 화면(/) 의 실제 변경일. 첫 화면 HTML 은 landing 빌드로만 바뀌고, 빌드할 때의 최신 영어 지문 날짜가 og:image 주소에 남는다.
    그 날짜를 쓰고, 찾지 못하면 가장 최근 지문 날짜를 쓴다(매일 오늘 날짜로 쓰면 바뀌지 않은 페이지가 바뀐 것처럼 보인다)."""
    f = ROOT / "index.html"
    m = re.search(r'property="og:image" content="[^"]*/(\d{4}-\d{2}-\d{2})/thumb\.png"', f.read_text(encoding="utf-8")) if f.exists() else None
    return m.group(1) if m else (max(days) if days else dt.date.today().isoformat())


def public_days():
    """공개 언어별 날짜 목록(최신순). noindex 언어는 뺀다."""
    return {code: days_of(code) for code, L in langs.LANGS.items() if not L.get("noindex", False) and days_of(code)}


def write_sitemap():
    """검색엔진용 사이트맵과 robots.txt, AI 안내(llms.txt), 새 지문 피드(rss.xml). 언어 목록, 날짜 페이지, 주간 복습을 싣는다.

    noindex 언어는 모두에서 제외한다. 지난 지문(/archive/)은 canonical 이 언어 첫 화면이라 사이트맵에 넣지 않는다.
    """
    by_lang = public_days()
    # (url, lastmod) 쌍의 목록
    entries = [(f"{SITE}/", root_lastmod([d[0] for d in by_lang.values()]))]
    for code, days in by_lang.items():
        entries.append((f"{SITE}/{code}/", days[0]))
        entries += [(f"{SITE}/{code}/{d}/", d) for d in days]
        rdir = ROOT / code / "review"
        if rdir.exists():
            entries += [(f"{SITE}/{code}/review/{r.name}/", r.name) for r in sorted(rdir.iterdir()) if r.is_dir()]
    entries += [(f"{SITE}{h}", INFO_DATE) for h, _ in FOOTER_PAGES]
    body = "".join(f"  <url><loc>{u}</loc><lastmod>{lm}</lastmod></url>\n" for u, lm in entries)
    (ROOT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n'
                                      '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + body + "</urlset>\n", encoding="utf-8")
    # 구글은 RSS 도 사이트맵으로 읽는다. llms.txt 는 정해진 지시어가 없어 주석으로만 알린다
    # Content-Signal: 검색, AI 답변 인용, AI 학습 모두 허용(운영자 결정, 2026-11-12)
    (ROOT / "robots.txt").write_text(f"User-agent: *\nContent-Signal: search=yes, ai-input=yes, ai-train=yes\nAllow: /\n\n"
                                     f"Sitemap: {SITE}/sitemap.xml\nSitemap: {SITE}/rss.xml\n"
                                     f"# llms.txt: {SITE}/llms.txt\n", encoding="utf-8")
    items = feed_items(by_lang)
    (ROOT / "rss.xml").write_text(rss_xml(items[:RSS_SIZE]), encoding="utf-8")
    (ROOT / "llms.txt").write_text(llms_txt(by_lang, items), encoding="utf-8")


# 안내 페이지(/about/, /privacy/, /contact/, 시안 design/own-pages O06, O07, O08). 지문 페이지 카드 결과 같은 위 메뉴를 쓴다.
# 시행일(개인정보처리방침)과 사이트맵 lastmod. 문구를 바꾸면 이 날짜도 바꾼다(매번 오늘 날짜로 쓰지 않아 다시 만들어도 같다)
INFO_DATE = "2026-11-13"
NUM = '<span class="num">{}</span>'
INFO_CSS = """  :root { --bg: #f2f4f6; --card: #ffffff; --ink: #191f28; --sub: #4e5968; --muted: #6b7684; --blue: #1b64da; --blue-soft: #e8f3ff; --edge: #e5e8eb;
           --card-r: 20px; --card-sh: 0 4px 18px rgba(16,24,40,.07); }
  * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
  html { -webkit-text-size-adjust: 100%; }
  body { margin: 0; background: var(--bg); color: var(--ink); font-family: Pretendard, -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", "Noto Sans KR", "Malgun Gothic", sans-serif;
         font-size: 16px; line-height: 1.6; letter-spacing: -0.01em; word-break: keep-all; overflow-wrap: anywhere; }
  main { max-width: 560px; margin: 0 auto; padding: 0 0 calc(24px + env(safe-area-inset-bottom)); }
  .top { background: var(--card); padding: 28px 20px 24px; border-radius: var(--card-r); margin: 12px 12px 0; box-shadow: var(--card-sh); }
  .date { display: block; font-size: 14px; font-weight: 600; color: var(--blue); }
  h1 { font-size: 26px; font-weight: 800; line-height: 1.35; margin: 6px 0 12px; letter-spacing: -0.03em; }
  h1 em { font-style: normal; color: var(--blue); }
  .card { background: var(--card); border-radius: var(--card-r); margin: 12px 12px 0; padding: 22px 20px; box-shadow: var(--card-sh); }
  [id], .card { scroll-margin-top: 84px; }
  .lead { margin: 0; font-size: 16px; color: var(--sub); line-height: 1.7; }
  .eff { margin: 2px 0 0; font-size: 14px; font-weight: 600; color: var(--muted); }
  .card h2 { margin: 0 0 10px; font-size: 19px; font-weight: 800; letter-spacing: -0.03em; line-height: 1.4; }
  .card p { margin: 0 0 10px; font-size: 15px; color: var(--sub); line-height: 1.7; }
  .card p:last-child { margin-bottom: 0; }
  .card p b { color: var(--ink); }
  .num { display: inline-flex; align-items: center; justify-content: center; width: 24px; height: 24px; margin-right: 8px; border-radius: 8px; background: var(--blue-soft); color: var(--blue); font-size: 13px; font-weight: 800; vertical-align: 2px; }
  ul.dots { margin: 0; padding: 0; list-style: none; }
  ul.dots li { position: relative; padding-left: 14px; margin: 0 0 6px; font-size: 15px; color: var(--sub); line-height: 1.65; }
  ul.dots li::before { content: ""; position: absolute; left: 2px; top: 10px; width: 5px; height: 5px; border-radius: 50%; background: #c5ccd6; }
  ul.dots li b { color: var(--ink); }
  .lv { width: 100%; border-collapse: collapse; font-size: 14px; }
  .lv th, .lv td { text-align: left; padding: 10px 0; border-top: 1px solid var(--edge); vertical-align: top; }
  .lv tr:first-child th, .lv tr:first-child td { border-top: 0; }
  .lv th { width: 74px; font-weight: 700; color: var(--ink); }
  .lv td { color: var(--sub); }
  .lv td span { display: inline-block; margin: 0 6px 4px 0; padding: 3px 9px; border-radius: 999px; background: var(--bg); font-size: 13px; font-weight: 600; color: var(--sub); }
  .lv td span.b { background: var(--blue-soft); color: var(--blue); }
  .row { padding: 14px 0; border-top: 1px solid var(--edge); }
  .row:first-of-type { border-top: 0; padding-top: 4px; }
  .row h3 { margin: 0 0 4px; font-size: 15px; font-weight: 700; color: var(--ink); }
  .row p { margin: 0; font-size: 14px; }
  .row .who { display: inline-block; margin-top: 6px; padding: 3px 9px; border-radius: 6px; background: var(--bg); font-size: 12px; font-weight: 600; color: var(--muted); }
  .keys { margin: 4px 0 0; padding: 0; list-style: none; }
  .keys li { display: flex; gap: 10px; padding: 9px 0; border-top: 1px solid var(--edge); font-size: 14px; color: var(--sub); }
  .keys li:first-child { border-top: 0; }
  .keys code { flex: none; width: 128px; font: 600 12px/1.6 ui-monospace, Menlo, monospace; color: var(--ink); overflow-wrap: anywhere; }
  a.ln { color: var(--blue); font-weight: 600; text-decoration: none; }
  .mailbox { display: flex; align-items: center; gap: 12px; padding: 16px; border-radius: 16px; background: var(--blue-soft); }
  .mailbox svg { width: 24px; height: 24px; flex: none; fill: none; stroke: var(--blue); stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }
  .mailbox b { display: block; font-size: 17px; color: var(--ink); letter-spacing: 0; }
  .mailbox span { font-size: 13px; color: var(--sub); }
  .btn { display: flex; align-items: center; justify-content: center; height: 52px; margin-top: 12px; border-radius: 14px; background: var(--blue); color: #fff; font-size: 16px; font-weight: 700; text-decoration: none; }
  .toc { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 14px; }
  .toc a { padding: 6px 11px; border-radius: 999px; background: var(--bg); font-size: 13px; font-weight: 600; color: var(--sub); text-decoration: none; }
  .site-footer a.cur { color: #191f28; font-weight: 700; }
"""
MAIL_ICON = '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="3"/><path d="M4 7l8 6 8-6"/></svg>'


def info_pages():
    """(폴더, 페이지 제목, 설명, 구조화 데이터 @type, 본문 HTML). 문구는 승인 시안 그대로."""
    mail = f'<a class="ln" href="mailto:{feedback.MAIL}">{feedback.MAIL}</a>'
    about = (
        '<div class="top"><div class="date">독해한입 소개</div><h1>매일 아침 <em>외국어 지문 한 편</em></h1>'
        '<p class="lead">독해한입은 한국인 학습자를 위해 매일 아침 영어, 일본어, 독일어 짧은 지문을 한 편씩 올리는 무료 읽기 사이트예요. 페이지에서 바로 읽고, 메일로도 받아 볼 수 있어요.</p></div>\n'
        f'<section class="card"><h2>{NUM.format(1)}누구를 위한 곳인가요</h2><p>출퇴근길처럼 짧은 틈에 외국어 글 한 편을 읽고, 듣고, 해석까지 확인하고 싶은 분을 위해 만들었어요. 회원 가입 없이 누구나 읽을 수 있어요.</p></section>\n'
        f'<section class="card"><h2>{NUM.format(2)}매일 무엇이 오나요</h2><table class="lv">'
        '<tr><th>영어</th><td><span class="b">중급 CEFR B1~B2</span><span>기초 A2~B1</span></td></tr>'
        '<tr><th>일본어</th><td><span class="b">중급 JLPT N3</span><span>기초 N4~N5</span></td></tr>'
        '<tr><th>독일어</th><td><span class="b">중급 CEFR B1~B2</span><span>기초 A2~B1</span></td></tr></table>'
        '<ul class="dots" style="margin-top:12px"><li>지문마다 <b>문장별 음성, 주요 단어, 체크 포인트, 모범 해석</b>이 함께 있어요.</li>'
        '<li>월, 수, 금은 최근 소식, 화, 목은 원리와 문화 설명, 토, 일은 생활 글이에요.</li>'
        '<li>일요일에는 한 주 단어를 모은 <b>주간 복습</b>이 와요.</li></ul></section>\n'
        f'<section class="card"><h2>{NUM.format(3)}어떻게 만드나요</h2><ul class="dots">'
        '<li><b>AI 도구가 초안을 써요.</b> 언어마다 정해 둔 작성 규칙(수준, 문장 길이, 표기, 요일별 글 유형)을 따라요.</li>'
        '<li><b>자동 검사를 통과해야 올라가요.</b> 길이와 표기, 형식, 최근 지문과 겹치는 소재와 단어를 검사하고, 오류가 나오면 고쳐서 다시 검사해요.</li>'
        '<li><b>기사 문장을 옮기지 않아요.</b> 소식과 설명 날에는 원문 기사나 자료를 열어 사실을 확인한 뒤 새로 쓰고, 출처를 페이지에 밝혀요. 기사 없이 쓴 글은 그렇다고 표시해요.</li>'
        '<li><b>음성은 합성 음성이에요.</b> 사람이 녹음하지 않고 음성 합성 프로그램으로 만들어요.</li>'
        '<li>틀린 내용을 발견하시면 <a class="ln" href="/contact/">연락처</a>로 알려 주세요. 확인한 뒤 고쳐요.</li></ul></section>\n'
    )
    d = dt.date.fromisoformat(INFO_DATE)
    privacy = (
        f'<div class="top"><div class="date">독해한입 안내</div><h1>개인정보처리방침</h1><p class="eff">시행일: {d.year}년 {d.month}월 {d.day}일</p>'
        '<p class="lead" style="margin-top:10px">독해한입(dokhaehanip.com)과 독해한입이 보내는 메일에 적용돼요. 회원 가입이 없고, 아래에 적은 경우가 아니면 개인정보를 모으지 않아요.</p>'
        '<nav class="toc" aria-label="목차"><a href="#collect">모으는 정보</a><a href="#storage">브라우저 저장값</a><a href="#cookies">쿠키와 광고</a>'
        '<a href="#retention">구독 해지</a><a href="#ask">문의</a></nav></div>\n'
        f'<section class="card" id="collect"><h2>{NUM.format(1)}모으는 정보와 쓰는 곳</h2>'
        '<div class="row"><h3>메일 구독</h3><p>구독 칸에 넣은 <b>이메일 주소</b>와 고른 <b>언어</b>, <b>지문 수준</b>(기초, 중급). 매일 아침 지문 메일과 일요일 주간 복습 메일을 보내는 데만 써요.</p><span class="who">맡긴 곳: Buttondown (미국, 메일 발송)</span></div>'
        '<div class="row"><h3>방문 통계</h3><p>방문 수, 유입 경로, 페이지 이용 흐름, 버튼 사용(주제 반응, 단어 외우기, 의견 보내기 등)을 익명 통계로 봐요. IP 주소는 익명 처리하고 이름이나 이메일과 연결하지 않아요.</p><span class="who">맡긴 곳: Google Analytics 4, Microsoft Clarity</span></div>'
        '<div class="row"><h3>광고</h3><p>Google AdSense 광고를 보여 줄 수 있어요. 아래 3번을 봐 주세요.</p><span class="who">맡긴 곳: Google AdSense</span></div>'
        '<div class="row"><h3>의견 메일</h3><p>기능 건의나 버그 제보 버튼은 메일 앱을 열어요. 버그 제보에는 누른 페이지 주소, 기기와 브라우저 이름, 화면 크기가 미리 채워지고, 보내기 전에 지울 수 있어요. 받은 메일은 답장과 수정에만 써요.</p></div>'
        '<div class="row"><h3>접속 기록</h3><p>사이트는 GitHub Pages로 제공돼요. GitHub는 보안과 운영을 위해 접속 IP 등을 기록할 수 있어요. 글꼴(cdnjs)을 불러올 때도 그 제공자에게 접속 정보가 전달될 수 있어요.</p><span class="who">제공: GitHub Pages, cdnjs</span></div></section>\n'
        f'<section class="card" id="storage"><h2>{NUM.format(2)}브라우저에 저장하는 값</h2><p>학습 기록과 설정은 이용자 기기의 브라우저 저장소(localStorage)에만 두고, 독해한입 서버로 보내지 않아요. 브라우저 사이트 데이터를 지우면 함께 사라져요.</p>'
        '<ul class="keys"><li><code>drill:v1</code><span>단어 외우기 복습 기록(다시 물을 날짜)</span></li><li><code>drill:pref</code><span>단어 외우기 방식(카드, 문제)</span></li>'
        '<li><code>read_level:언어</code><span>언어별로 고른 지문 수준</span></li><li><code>read_speed</code><span>음성 재생 속도</span></li>'
        '<li><code>vote:언어/날짜</code><span>오늘 주제 반응(좋아요, 별로예요). 반응 자체는 방문 통계로도 보내요</span></li>'
        "<li><code>lily.justListen</code><span>릴리 그림책 듣기 페이지의 '듣기만' 설정</span></li></ul></section>\n"
        f'<section class="card" id="cookies"><h2>{NUM.format(3)}쿠키와 광고</h2><p>Google을 포함한 제3자 광고 업체는 쿠키를 써서, 이 사이트와 다른 사이트를 방문한 기록을 바탕으로 광고를 보여 줄 수 있어요. 자세한 내용은 <a class="ln" href="https://policies.google.com/technologies/partner-sites">Google 파트너 사이트의 데이터 사용 방식</a>에 있어요.</p>'
        '<p>맞춤 광고는 <a class="ln" href="https://adssettings.google.com/">Google 광고 설정</a>에서, 제3자 업체 맞춤 광고 쿠키는 <a class="ln" href="https://www.aboutads.info/choices/">www.aboutads.info</a>에서 끌 수 있어요. Google Analytics 수집은 <a class="ln" href="https://tools.google.com/dlpage/gaoptout">수집 거부 부가 기능</a>으로 막을 수 있어요. 쿠키를 거부해도 읽기에는 문제가 없어요.</p></section>\n'
        f'<section class="card" id="retention"><h2>{NUM.format(4)}보관과 구독 해지</h2><ul class="dots"><li>이메일 주소는 수신거부하거나 삭제를 요청할 때까지 보관하고, 요청을 받으면 지체 없이 지워요.</li>'
        '<li>모든 메일 맨 아래 <b>수신거부</b> 링크를 누르면 바로 해지돼요.</li><li>내 정보 열람, 정정, 삭제, 처리 정지는 아래 메일로 요청해 주세요.</li>'
        '<li>만 14세 미만 아동의 개인정보는 알면서 모으지 않아요.</li><li>내용이 바뀌면 이 페이지에 새 시행일과 함께 알려요.</li></ul></section>\n'
        f'<section class="card" id="ask"><h2>{NUM.format(5)}문의</h2><p>개인정보 문의: {mail} (운영자)</p></section>\n'
    )
    buttons = (f'<div class="fb-row"><a class="fb-btn" data-fb="idea" href="{html.escape(feedback.mailto(feedback.IDEA_SUBJECT, feedback.idea_body()))}">{feedback.IDEA_ICON}기능 건의</a>'
               f'<a class="fb-btn" data-fb="bug" href="{html.escape(feedback.mailto(feedback.BUG_SUBJECT, feedback.bug_body(f"{SITE}/contact/")))}">{feedback.BUG_ICON}버그 제보</a></div>')
    contact = (
        '<div class="top"><div class="date">독해한입 안내</div><h1>연락처</h1><p class="lead">지문 오류 제보, 기능 의견, 구독과 개인정보 요청은 메일로 보내 주세요. 운영자가 직접 읽어요.</p></div>\n'
        f'<section class="card"><h2>이메일</h2><div class="mailbox">{MAIL_ICON}<div><b>{feedback.MAIL}</b><span>운영자</span></div></div>'
        f'<a class="btn" href="mailto:{feedback.MAIL}">메일 쓰기</a></section>\n'
        f'<section class="card"><h2>양식이 있는 메일로 보내기</h2><p>누르면 메일 앱이 열리고 제목과 본문 양식이 미리 채워져요. 버그 제보에는 페이지 주소, 기기, 화면 크기가 들어가요.</p>{buttons}</section>\n'
        '<section class="card"><h2>이런 내용을 보내 주세요</h2><ul class="dots"><li>지문, 해석, 단어 뜻에서 틀린 내용이나 이상한 음성</li><li>화면이 깨지거나 버튼이 안 눌리는 문제</li>'
        '<li>있으면 좋을 기능이나 읽고 싶은 주제</li><li>구독 해지가 안 되는 경우, 내 정보 삭제 요청</li><li>저작권 관련 문의</li></ul></section>\n'
        '<section class="card"><h2>답변</h2><p>보통 3일 안에 답장을 드려요. 메일 수신거부는 받은 메일 맨 아래 <b>수신거부</b> 링크로 바로 할 수 있어요.</p></section>\n'
    )
    return [
        ("about", f"{langs.BRAND} 소개", "독해한입은 매일 아침 영어, 일본어, 독일어 짧은 지문을 한 편씩 올리는 무료 읽기 사이트예요. 누구를 위해, 어떻게 만드는지 소개해요.", "AboutPage", about),
        ("privacy", "개인정보처리방침", "독해한입이 모으는 정보(메일 구독, 방문 통계, 광고)와 브라우저 저장값, 쿠키, 구독 해지 방법을 안내해요.", "WebPage", privacy),
        ("contact", "연락처", "지문 오류 제보, 기능 의견, 구독과 개인정보 요청은 메일로 보내 주세요. 운영자가 직접 읽어요.", "ContactPage", contact),
    ]


INFO = r"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="color-scheme" content="light only"><title>__TITLE__ | __BRAND__</title>
<meta name="description" content="__DESC__">
<meta property="og:type" content="website"><meta property="og:site_name" content="__BRAND__">
<meta property="og:title" content="__TITLE__ | __BRAND__"><meta property="og:description" content="__DESC__">
<meta property="og:url" content="__URL__"><meta property="og:image" content="__SITE__/assets/brand/icon-512.png">
<meta name="twitter:card" content="summary">
<link rel="canonical" href="__URL__">
<link rel="icon" href="/icon-32.png" sizes="32x32" type="image/png"><link rel="apple-touch-icon" href="/apple-icon.png">
__RSS____LD__<link rel="preconnect" href="https://cdnjs.cloudflare.com" crossorigin>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/pretendard/1.3.9/static/pretendard.min.css">
<style>
__INFO_CSS____GNB_CSS____FOOTER_CSS__</style>
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-2339195232447097"
     crossorigin="anonymous"></script>
<script async src="https://www.googletagmanager.com/gtag/js?id=G-43L9WRDB2N"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}gtag('js',new Date());gtag('config','G-43L9WRDB2N',{anonymize_ip:true});</script>
<script>(function(c,l,a,r,i,t,y){c[a]=c[a]||function(){(c[a].q=c[a].q||[]).push(arguments)};t=l.createElement(r);t.async=1;t.src="https://www.clarity.ms/tag/"+i;y=l.getElementsByTagName(r)[0];y.parentNode.insertBefore(t,y);})(window,document,"clarity","script","yxuphaowch");</script>
</head>
<body>
__GNB__<main>
__BODY__</main>
__FOOTER____GNB_JS__</body></html>
"""


def info_ld(folder, title, desc, kind):
    url = f"{SITE}/{folder}/"
    page = {"@type": kind, "@id": f"{url}#page", "url": url, "name": title, "description": desc, "inLanguage": "ko-KR",
            "dateModified": INFO_DATE, "isPartOf": {"@id": WEBSITE_ID}, "about": {"@id": ORG_ID}, "publisher": {"@id": ORG_ID}}
    return ld_script([page, crumbs_ld((langs.BRAND, f"{SITE}/"), (title, url)), *site_nodes()])


def rebuild_info_pages():
    """소개, 개인정보처리방침, 연락처 페이지를 만든다. 여러 번 돌려도 같다."""
    # 언어가 없는 페이지지만 '지난 지문'과 시트를 쓰려고 영어를 기본으로 두고, 언어 탭의 '지금 보는 중' 표시만 뺀다
    head = gnb.header_html("en", "/#subscribe").replace(' class="on" aria-current="page"', "", 1)
    for folder, title, desc, kind, body in info_pages():
        url = f"{SITE}/{folder}/"
        footer = f'<footer class="site-footer">{footer_links(f"/{folder}/")}</footer>\n'
        if folder == "contact":
            # 양식 메일 버튼이 본문 카드에 있어 아래 '바라는 점이 있나요?' 띠는 두지 않는다(시안 O08). 버튼 모양과 스크립트만 쓴다
            footer += feedback.SCRIPT
        page = (INFO.replace("__TITLE__", title).replace("__BRAND__", langs.BRAND).replace("__DESC__", html.escape(desc, quote=True))
                .replace("__URL__", url).replace("__SITE__", SITE).replace("__RSS__", RSS_LINK).replace("__LD__", info_ld(folder, title, desc, kind))
                .replace("__INFO_CSS__", INFO_CSS + (feedback.CSS if folder == "contact" else "")).replace("__GNB_CSS__", gnb.css_block())
                .replace("__FOOTER_CSS__", "  " + FOOTER_CSS).replace("__GNB__", head).replace("__BODY__", body)
                .replace("__FOOTER__", footer).replace("__GNB_JS__", gnb.SCRIPT))
        if folder != "contact":
            page = feedback.apply(page, None, url)
        page = migrate.apply(page)
        out = ROOT / folder
        out.mkdir(exist_ok=True)
        (out / "index.html").write_text(page, encoding="utf-8")


RSS_SIZE = 30


def feed_items(by_lang):
    """모든 공개 언어의 지문을 최신순으로: 날짜가 같으면 langs.LANGS 순서(en, ja, de)."""
    order = list(langs.LANGS)
    out = []
    for code, days in by_lang.items():
        L = langs.LANGS[code]
        for d in days[:RSS_SIZE]:
            cf = ROOT / "content" / code / f"{d}.json"
            c = json.loads(cf.read_text(encoding="utf-8")) if cf.exists() else {}
            topic = c.get("title_ko") or entry(code, d)["topic"]
            src = (c.get("source") or {}).get("title")
            # 피드 안에서는 사이트 이름이 반복되므로 페이지 제목 끝의 " | 독해한입" 을 뺀다
            title = page_title(code, d, topic).removesuffix(f" | {langs.BRAND}")
            out.append({"lang": code, "day": d, "topic": topic, "title": title,
                        "url": f"{SITE}/{code}/{d}/", "src": src,
                        "desc": f"{langs.level_on(code, d)} {L['name']} 읽기 — {topic}. 문장별 음성과 모범 해석으로 하루 한 단락을 공부해요."})
    return sorted(out, key=lambda r: (r["day"], -order.index(r["lang"])), reverse=True)


def rss_xml(items):
    """RSS 2.0. 발행 시각은 따로 기록하지 않아 화면 안내와 같은 그날 07:00(KST)로 적고, lastBuildDate 도 가장 새 지문 날짜로 둔다(매번 바뀌지 않게)."""
    from email.utils import format_datetime
    kst = dt.timezone(dt.timedelta(hours=9))
    when = lambda day: format_datetime(dt.datetime.combine(dt.date.fromisoformat(day), dt.time(7), kst))
    esc = lambda t: html.escape(t, quote=False)
    body = "".join(
        "  <item>\n"
        f"    <title>{esc(i['title'])}</title>\n    <link>{i['url']}</link>\n    <guid isPermaLink=\"true\">{i['url']}</guid>\n"
        f"    <pubDate>{when(i['day'])}</pubDate>\n    <category>{esc(langs.LANGS[i['lang']]['name'])}</category>\n"
        f"    <description>{esc(i['desc'])}</description>\n"
        "  </item>\n" for i in items)
    built = f"  <lastBuildDate>{when(items[0]['day'])}</lastBuildDate>\n" if items else ""
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n<channel>\n'
            f"  <title>{esc(langs.BRAND_ROOT)}</title>\n  <link>{SITE}/</link>\n"
            f'  <atom:link href="{SITE}/rss.xml" rel="self" type="application/rss+xml"/>\n'
            "  <description>매일 아침 새로 올라오는 영어, 일본어, 독일어 독해 지문</description>\n"
            f"  <language>ko</language>\n{built}{body}</channel>\n</rss>\n")


def llms_txt(by_lang, items):
    """AI 검색 안내(llms.txt). 사실만 적는다: 무엇을, 어떤 수준으로, 어떻게 만드는지와 주요 주소, 언어별 최근 지문."""
    # 다른 표기: 대소문자만 다른 이름과 사이트 이름에 이미 든 설명("매일 외국어 읽기")은 뺀다
    alt = [n for i, n in enumerate(langs.ALT_NAMES)
           if n.lower() not in [m.lower() for m in langs.ALT_NAMES[:i]] and n not in langs.BRAND_ROOT]
    lines = [
        f"# {langs.BRAND}", "",
        f"> {langs.BRAND}은 한국어 사용자를 위한 무료 외국어 독해 사이트이자 이메일 뉴스레터입니다. "
        "매일 아침 영어, 일본어, 독일어 짧은 지문을 한 편씩 올리고, 지문마다 문장별 음성, 주요 단어, 한국어 모범 해석, 문법 체크 포인트를 함께 둡니다. "
        "지문은 AI가 초안을 쓰고 자동 검사(화면 표기 오류, 출처 없는 구체적 수치, 최근 지문과의 겹침 등)를 거쳐 올라갑니다. 기사를 바탕으로 쓴 날은 원출처를 페이지에 밝힙니다.", "",
        f"- 다른 표기: {', '.join(alt)}",
        "- 이용료: 무료",
        "- 갱신: 매일 오전 7시 전후(KST)에 언어별 새 지문, 일요일에는 주간 단어 복습" + (f". 마지막 갱신 {items[0]['day']}" if items else ""),
        f"- 소개: {SITE}/about/, 연락처: {SITE}/contact/", "",
        "## 언어별 지문",
    ]
    for code in by_lang:
        L = langs.LANGS[code]
        lv = L["level"] + (f" ({L['level_a_label']})" if L.get("levels") and L.get("level_a_label") else
                          (" (기초 A2~B1)" if L.get("levels") else ""))
        lines.append(f"- [{L['name']} 지문 목록]({SITE}/{code}/): {lv} {L['name']} 읽기, 지금까지 {len(by_lang[code])}편")
    lines += ["", "## 최근 지문"]
    for code in by_lang:
        for i in [i for i in items if i["lang"] == code][:7]:
            src = f": 출처 {i['src']}" if i["src"] else ""
            lines.append(f"- [{langs.LANGS[code]['name']}, {i['day']}, {i['topic']}]({i['url']}){src}")
    reviews = [(code, gnb.latest_review(code)) for code in by_lang]
    reviews = [(code, rv) for code, rv in reviews if rv]
    if reviews:
        lines += ["", "## 주간 단어 복습"]
        lines += [f"- [{langs.LANGS[code]['name']} 주간 단어 복습, {rv[0]}]({SITE}/{code}/review/{rv[0]}/): 그 주 지문의 주요 단어 {rv[1]}개"
                  for code, rv in reviews]
    lines += ["", "## 이용 방법", f"- [첫 화면과 자주 묻는 질문]({SITE}/): 구독 방법, 수준 안내",
              "", "## Optional", f"- [사이트맵]({SITE}/sitemap.xml)", f"- [새 지문 피드(RSS)]({SITE}/rss.xml)",
              f"- [개인정보처리방침]({SITE}/privacy/)", ""]
    return "\n".join(lines)


# 지난 지문 페이지. 검색과 분야 필터, 30개씩 더 보기를 브라우저에서 처리한다(스크립트가 없어도 전체 목록은 보인다).
ARCHIVE = r"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light only"><title>__TITLE__ | __SITE__</title>
<meta name="description" content="__META_DESC__">
<meta property="og:type" content="website"><meta property="og:site_name" content="__SITE__">
<meta property="og:title" content="__TITLE__ | __BRAND__"><meta property="og:description" content="__META_DESC__">
<meta property="og:url" content="__CANONICAL__"><meta property="og:image" content="__OG_IMAGE__">
<meta name="twitter:card" content="summary_large_image">
<link rel="canonical" href="__CANONICAL__">
<link rel="icon" href="/icon-32.png" sizes="32x32" type="image/png"><link rel="apple-touch-icon" href="/apple-icon.png">
__RSS____LD__<link rel="preconnect" href="https://cdnjs.cloudflare.com" crossorigin>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/pretendard/1.3.9/static/pretendard.min.css">
<style>
  :root { --bg: #f2f4f6; --ink: #191f28; --sub: #4e5968; --muted: #6b7684; --blue: #1b64da; }
  body { margin: 0; background: #f2f4f6; color: #191f28; font-family: Pretendard, -apple-system, "Apple SD Gothic Neo", sans-serif; letter-spacing: -0.01em; word-break: keep-all; }
  main { max-width: 560px; margin: 0 auto; padding: 20px 12px 40px; }
  h1 { font-size: 26px; font-weight: 800; margin: 0 8px 16px; letter-spacing: -0.03em; }
__GNB_CSS__  .ltabs { display: flex; gap: 6px; margin: 0 0 16px; padding: 4px; border-radius: 14px; background: #e8ebef; }
  .ltabs a { flex: 1; text-align: center; font-size: 15px; font-weight: 700; color: var(--sub); padding: 10px 0; border-radius: 10px; text-decoration: none; }
  .ltabs a.on { background: #fff; color: var(--ink); box-shadow: 0 1px 4px rgba(16,24,40,.08); }
  .back { display: inline-block; margin: 0 8px 12px; font-size: 14px; font-weight: 600; color: #1b64da; text-decoration: none; }
  .search { display: block; width: 100%; box-sizing: border-box; height: 48px; border: 1.5px solid transparent; border-radius: 12px; background: #fff; box-shadow: 0 2px 10px rgba(16,24,40,.06);
            padding: 0 16px; font: 400 16px Pretendard, -apple-system, sans-serif; color: #191f28; outline: 0; }
  .search:focus { border-color: #1b64da; }
  .chips { display: flex; flex-wrap: wrap; gap: 6px; padding: 12px 0 8px; }
  .chips::-webkit-scrollbar { display: none; }
  .chip { flex: none; height: 34px; padding: 0 14px; border: 0; border-radius: 999px; background: #fff; color: #4e5968;
          font: 600 14px Pretendard, -apple-system, sans-serif; cursor: pointer; }
  .chip[aria-pressed="true"] { background: #1b64da; color: #fff; }
  .month h2 { font-size: 15px; font-weight: 700; color: #4e5968; margin: 20px 8px 8px; }
  .card { background: #fff; border-radius: 20px; padding: 4px 20px; box-shadow: 0 4px 18px rgba(16,24,40,.07); }
  [id] { scroll-margin-top: 84px; }
  .item { display: flex; align-items: center; gap: 14px; padding: 14px 0; border-top: 1px solid #f2f4f6; color: inherit; text-decoration: none; }
  .item.first { border-top: 0; }
  .item img { flex: none; width: 56px; height: 56px; object-fit: cover; object-position: 100% 50%; }
  .item img.ph { object-position: 50% 50%; border-radius: 14px; }
  .d { display: block; font-size: 14px; color: #6b7684; font-weight: 600; }
  .c { margin-left: 8px; font-size: 12px; color: #1b64da; }
  .t { display: block; font-size: 17px; font-weight: 700; color: #191f28; margin-top: 2px; }
  .empty { text-align: center; color: #6b7684; font-size: 15px; padding: 40px 0; }
  .more { display: block; width: 100%; height: 52px; margin-top: 16px; border: 0; border-radius: 12px; background: #e8f3ff; color: #1b64da;
          font: 700 16px Pretendard, -apple-system, sans-serif; cursor: pointer; }
  [hidden] { display: none !important; }
  .review { display: flex; justify-content: space-between; align-items: center; margin: 0 0 12px; padding: 14px 18px; border-radius: 16px; background: #e8f3ff; color: #1b64da; font-size: 15px; font-weight: 700; text-decoration: none; }
  .sub-wrap { margin-top: 28px; }
  .sub-wrap .card { padding: 22px 20px; }
  .sub-wrap h2 { font-size: 20px; font-weight: 700; margin: 0 0 4px; }
__SUB_CSS____INTRO_CSS____FOOTER_CSS__</style>
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-2339195232447097"
     crossorigin="anonymous"></script>
<script async src="https://www.googletagmanager.com/gtag/js?id=G-43L9WRDB2N"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}gtag('js',new Date());gtag('config','G-43L9WRDB2N',{anonymize_ip:true});</script>
<script>(function(c,l,a,r,i,t,y){c[a]=c[a]||function(){(c[a].q=c[a].q||[]).push(arguments)};t=l.createElement(r);t.async=1;t.src="https://www.clarity.ms/tag/"+i;y=l.getElementsByTagName(r)[0];y.parentNode.insertBefore(t,y);})(window,document,"clarity","script","yxuphaowch");</script>
</head>
<body>
__GNB__<main>
  <a class="back" href="__TODAY__">오늘의 지문 바로 가기 →</a>
  <h1>__TITLE__</h1>
  <nav class="ltabs" aria-label="언어">__LANGTABS__</nav>
  <p class="intro" style="margin: -8px 8px 14px">__INTRO__</p>
__REVIEW__  <input class="search" id="q" type="search" placeholder="날짜, 주제로 찾기 (예: 10월 20일, __SEARCH_EXAMPLE__)" aria-label="지난 지문 검색" autocomplete="off">
  <div class="chips" role="group" aria-label="분야"><button type="button" class="chip" data-cat="" aria-pressed="true">전체</button>__CHIPS__</div>
__GROUPS__
  <p class="empty" id="empty" hidden>찾는 지문이 없어요.</p>
  <button class="more" id="more" type="button" hidden>더 보기</button>
  <div class="sub-wrap">
__SUB_HTML__  </div>
</main>
__FOOTER__<script>
  var PAGE = 30, shown = PAGE, cat = '';
  var q = document.getElementById('q'), more = document.getElementById('more'), empty = document.getElementById('empty');
  var items = [].slice.call(document.querySelectorAll('.item'));
  var chips = [].slice.call(document.querySelectorAll('.chip'));
  var months = [].slice.call(document.querySelectorAll('.month'));
  function apply() {
    var words = q.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
    var searching = words.length > 0 || cat !== '';
    var matched = 0;
    items.forEach(function (el) {
      var ok = (!cat || el.dataset.cat === cat) && words.every(function (w) { return el.dataset.q.indexOf(w) !== -1; });
      if (ok) matched++;
      el.hidden = !ok || (!searching && matched > shown);
    });
    months.forEach(function (m) {
      var visible = [].filter.call(m.querySelectorAll('.item'), function (el) { return !el.hidden; });
      m.hidden = visible.length === 0;
      [].forEach.call(m.querySelectorAll('.item'), function (el) { el.classList.toggle('first', el === visible[0]); });
    });
    empty.hidden = matched > 0;
    more.hidden = searching || matched <= shown;
  }
  q.addEventListener('input', apply);
  chips.forEach(function (c) {
    c.addEventListener('click', function () {
      cat = c.dataset.cat;
      chips.forEach(function (x) { x.setAttribute('aria-pressed', String(x === c)); });
      apply();
    });
  });
  more.addEventListener('click', function () { shown += PAGE; apply(); });
  apply();
</script>
__GNB_JS__</body></html>
"""


def publish_day(lang, day, cat=None):
    """한 날짜를 사이트에 붙인다(맨 위 설명의 1~3). 분야를 생략하면 content JSON 의 category."""
    langs.get(lang)
    content = ROOT / "content" / lang / f"{day}.json"
    if cat is None and content.exists():
        cat = json.loads(content.read_text(encoding="utf-8"))["category"]
    thumb.build(lang, day, cat)
    patch_page(lang, day)
    # 바로 앞, 뒤 날짜 페이지의 '다른 날 지문' 카드도 새 지문에 맞춘다(전날 페이지의 "내일 아침에 올라와요"를 오늘 링크로)
    for d in neighbors(lang, day):
        if d:
            patch_page(lang, d)
    rebuild_lists(lang)
    rebuild_root()


if __name__ == "__main__":
    lang, day = sys.argv[1], sys.argv[2]
    publish_day(lang, day, sys.argv[3] if len(sys.argv) > 3 else None)
    print(f"{SITE}/{lang}/{day}/")
