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

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://read.wspace.ai.kr"
SUBSCRIBE = "https://buttondown.com/api/emails/embed-subscribe/english-reading"
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
    # level-note 기본 숨김 — :has() 또는 JS data-show 로 표시
    "  .sub .level-note { flex-basis: 100%; display: none; }\n"
    "  .sub .levels:has(input[value='a']:checked) ~ .level-note,.sub .level-note[data-show] { display: block; }\n"
)


# wspace 전체 공통 하단. 애드센스 심사에서 정책 페이지로 가는 길이 모든 페이지에 있어야 한다.
FOOTER_CSS = (".site-footer { max-width: 560px; margin: 0 auto; padding: 8px 20px 40px; font-size: 13px; color: #8b95a1; "
              "display: flex; flex-wrap: wrap; gap: 6px 16px; } .site-footer a { color: #4e5968; text-decoration: none; }\n")
FOOTER_HTML = ('<footer class="site-footer"><a href="https://www.wspace.ai.kr/">wspace 홈</a>'
               '<a href="https://www.wspace.ai.kr/about/">소개</a><a href="https://www.wspace.ai.kr/privacy/">개인정보처리방침</a>'
               '<a href="https://www.wspace.ai.kr/contact/">연락처</a></footer>\n')


def intro_html(lang):
    L = langs.get(lang)
    return (f'    <p class="intro">{L["intro"]} 듣고, 해석하고, AI에게 피드백을 받아 보세요. '
            '<a href="#subscribe">메일로 받기</a><a href="../../">다른 언어</a></p>\n')


def _sub_script(lang):
    """구독 칸 인라인 스크립트.
    - GA subscribe 이벤트: levels=True 언어(en, de)는 level 파라미터 포함, 그 외는 생략.
    - :has() 미지원 브라우저 fallback: 라디오 change 시 data-checked/data-show 속성으로 CSS 선택 상태와 기초 노트를 제어한다.
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
        f'      // :has() 미지원 브라우저 fallback — data-checked / data-show 속성으로 CSS 를 보조한다\n'
        f'      var opts=sec.querySelectorAll(".lvopt");\n'
        f'      var note=sec.querySelector(".level-note");\n'
        f'      if(opts.length){{var update=function(){{\n'
        f'        opts.forEach(function(o){{\n'
        f'          var r=o.querySelector("input[type=\\"radio\\"]");\n'
        f'          if(r&&r.checked){{o.setAttribute("data-checked","");}}else{{o.removeAttribute("data-checked");}}\n'
        f'        }});\n'
        f'        if(note){{\n'
        f'          var a=sec.querySelector("input[name=\\"metadata__level\\"][value=\\"a\\"]:checked");\n'
        f'          if(a){{note.setAttribute("data-show","");}}else{{note.removeAttribute("data-show");}}\n'
        f'        }}\n'
        f'      }};update();\n'
        f'      opts.forEach(function(o){{var r=o.querySelector("input[type=\\"radio\\"]");if(r)r.addEventListener("change",update);}});\n'
        f'      }}\n'
        f'    }})();</script>\n'
    )


# 수준 선택 카드의 언어별 문구: (기초 범위, 기초 설명, 중급 범위, 중급 설명, 기초 선택 시 안내)
# 기초 지문이 매일 있는 언어(de, ja)는 "기초 지문은 준비 중" 안내를 넣지 않는다.
LEVEL_CHOICES = {
    "en": ("A2~B1", "짧고 쉬운 문장. 영어 읽기를 다시 시작한다면",
           "B1~B2", "뉴스 기사에 가까운 문장. 긴 문장도 읽어 보고 싶다면",
           '      <p class="note level-note">기초 지문은 준비 중이에요. 준비되면 기초 지문으로 보내 드려요. 그전에는 중급 지문이 가요.</p>\n'),
    "de": ("A2~B1", "짧고 쉬운 문장. 독일어 읽기를 막 시작했다면",
           "B1~B2", "조금 긴 문장과 B2 문법도 읽어 보고 싶다면", ""),
    "ja": ("N4~N5", "짧고 쉬운 문장. 일본어 읽기를 막 시작했다면",
           "N3", "조금 긴 문장과 N3 문법도 읽어 보고 싶다면", ""),
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
        range_a, desc_a, range_b, desc_b, level_note = LEVEL_CHOICES.get(lang, LEVEL_CHOICES["en"])
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
            + level_note
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
    d = dt.date.fromisoformat(day)
    return f"{d.month}월 {d.day}일 {DAYS[d.weekday()]}요일"


def patch_page(lang, day):
    L = langs.get(lang)
    path = ROOT / lang / day / "index.html"
    page = path.read_text(encoding="utf-8")
    url = f"{SITE}/{lang}/{day}/"
    if 'property="og:image"' not in page:
        title = html.escape(f"오늘은 {topic_of(lang, day)} 이야기예요 | {L['site']}")
        desc = f"{L['level']} 학습자를 위한 하루 한 단락 {L['name']} 읽기. 문장별 음성, 주요 단어, 모범 해석."
        meta = (
            f'<meta name="description" content="{desc}">\n'
            f'<meta property="og:type" content="article">\n'
            f'<meta property="og:site_name" content="{L["site"]}">\n'
            f'<meta property="og:title" content="{title}">\n'
            f'<meta property="og:description" content="{desc}">\n'
            f'<meta property="og:url" content="{url}">\n'
            f'<meta property="og:image" content="{url}thumb.png">\n'
            f'<meta property="og:image:width" content="1200">\n'
            f'<meta property="og:image:height" content="630">\n'
            f'<meta name="twitter:card" content="summary_large_image">\n'
        )
        page = page.replace("<link rel=\"stylesheet\"", meta + "<link rel=\"stylesheet\"", 1)
    if 'class="thumb"' not in page:
        page = page.replace(
            "  .gnb {",
            "  .top { position: relative; }\n  .thumb { position: absolute; top: 18px; right: 18px; width: 76px; height: 76px; object-fit: cover; object-position: 100% 50%; }\n  .gnb {",
            1,
        )
        page = page.replace(
            '<div class="date">',
            f'<img class="thumb" src="thumb.png" width="76" height="76" alt="">\n    <div class="date">',
            1,
        )
    if 'class="site-footer"' not in page:
        page = page.replace("  .gnb {", "  " + FOOTER_CSS + "  .site-footer { padding-bottom: 32px; }\n  .gnb {", 1)
        page = page.replace("</main>", "</main>\n" + FOOTER_HTML, 1)
        page = page.replace("<link rel=\"stylesheet\"", f'<link rel="canonical" href="{url}">\n<link rel="stylesheet"', 1)
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
            page = page.replace("\n  </div>\n\n  <section class=\"card\" id=\"passage\">", "\n" + intro_html(lang) + "  </div>\n\n  <section class=\"card\" id=\"passage\">", 1)
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
                "  .sub .level-note { flex-basis: 100%; display: none; }\n"
                "  .sub .levels:has(input[value='a']:checked) ~ .level-note,.sub .level-note[data-show] { display: block; }\n"
            )
            page = page.replace("  .sub .note {", SUB_EXTRA + "  .sub .note {", 1)
    if "#passage .chunks-a {" not in page:
        for old, new in LEVEL_A_CSS:
            page = page.replace(old, new, 1)
    page = vote.apply(page, lang, day)  # 오늘 분야 배지와 주제 반응 카드(#13)
    page = drill.apply(page, lang, day)  # 단어 암기 반복과 복습 띠(#16)
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
                                (ROOT / lang / "archive", "../", "../../", "지난 지문")):
        groups, month = [], None
        for e in entries:
            if e["month"] != month:
                if month is not None:
                    groups.append("    </div>\n  </section>")
                month = e["month"]
                groups.append(f'  <section class="month">\n    <h2>{month}</h2>\n    <div class="card">')
            groups.append(
                f'      <a class="item" href="{p}{e["day"]}/" data-cat="{e["cat"]}" data-q="{html.escape(e["q"])}">'
                f'<img src="{p}{e["day"]}/thumb.png" width="56" height="56" alt="" loading="lazy">'
                f'<span><span class="d">{e["label"]}<span class="c">{e["cat_label"]}</span></span>'
                f'<span class="t">{html.escape(e["topic"])}</span></span></a>'
            )
        groups.append("    </div>\n  </section>")
        review = (f'  <a class="review" href="{p}review/{reviews[0]}/"><span>이번 주 단어 복습</span><span>→</span></a>\n' if reviews else "")
        page = (ARCHIVE.replace("__REVIEW__", review).replace("__OG_IMAGE__", f"{SITE}/{lang}/{latest}/thumb.png")
                .replace("__TITLE__", title).replace("__ARCHIVE__", f"{p}archive/" if p == "./" else "./").replace("__TODAY__", f"{p}{latest}/").replace("__HOME__", home)
                .replace("__SITE__", L["site"]).replace("__INTRO__", L["intro"]).replace("__SEARCH_EXAMPLE__", L["search_example"])
                .replace("__CHIPS__", chips).replace("__SUB_CSS__", SUB_CSS).replace("__INTRO_CSS__", INTRO_CSS)
                .replace("__SUB_HTML__", sub_html(lang)).replace("__GROUPS__", "\n".join(groups))
                .replace("__CANONICAL__", f"{SITE}/{lang}/").replace("__FOOTER_CSS__", "  " + FOOTER_CSS).replace("__FOOTER__", FOOTER_HTML))
        if L.get("noindex", False):
            page = page.replace('<link rel="stylesheet"', '<meta name="robots" content="noindex">\n<link rel="stylesheet"', 1)
        out.mkdir(parents=True, exist_ok=True)
        (out / "index.html").write_text(page, encoding="utf-8")


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
        "q": f"{topic} {thumb.CATS[cat][0]} {words}".lower(),
    }


def rebuild_root():
    """사이트 첫 화면이 읽는 latest.json 을 만든다. 첫 화면(index.html)은 landing 정적 빌드로 따로 배포한다.

    noindex 언어는 latest.json 의 langs/recent 에서 제외한다(검색엔진 숨김 운영 중).

    모양: {"date", "words_total"(올라간 지문 전체의 주요 단어 수),
           "langs": {code: {"count", "latest", "topic", "sentences"(앞 4문장, 원문 표기 그대로),
                            "chips", "answer"(1번 모범 해석), "words"}},
           "recent"(두 언어 최근 7일, 최대 14편. 첫 화면의 이번 주 달력과 주제 띠에 씀)}
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
        data["date"] = max(data["date"], days[0])
        for d in days:
            f = ROOT / "content" / code / f"{d}.json"
            if f.exists():
                data["words_total"] += len(json.loads(f.read_text(encoding="utf-8")).get("words", []))
        recent += [{"lang": code, "day": d, "topic": entry(code, d)["topic"]} for d in days[:7]]
    order = list(langs.LANGS)
    data["recent"] = sorted(recent, key=lambda r: (r["day"], -order.index(r["lang"])), reverse=True)[:14]
    (ROOT / "latest.json").write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    write_sitemap()


def write_sitemap():
    """검색엔진용 사이트맵과 robots.txt. 언어 목록, 날짜 페이지, 주간 복습을 모두 싣는다.

    noindex 언어는 사이트맵에서 제외한다.
    """
    urls = [f"{SITE}/"]
    for code in langs.LANGS:
        L = langs.LANGS[code]
        if L.get("noindex", False):
            continue  # 숨김 운영 중인 언어는 사이트맵에서 제외
        days = days_of(code)
        if not days:
            continue
        urls.append(f"{SITE}/{code}/")
        urls += [f"{SITE}/{code}/{d}/" for d in days]
        rdir = ROOT / code / "review"
        if rdir.exists():
            urls += [f"{SITE}/{code}/review/{r.name}/" for r in sorted(rdir.iterdir()) if r.is_dir()]
    body = "".join(f"  <url><loc>{u}</loc></url>\n" for u in urls)
    (ROOT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n'
                                      '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + body + "</urlset>\n", encoding="utf-8")
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n", encoding="utf-8")


# 지난 지문 페이지. 검색과 분야 필터, 30개씩 더 보기를 브라우저에서 처리한다(스크립트가 없어도 전체 목록은 보인다).
ARCHIVE = r"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light only"><title>__TITLE__ | __SITE__</title>
<meta property="og:title" content="지난 지문 | __SITE__"><meta property="og:image" content="__OG_IMAGE__">
<meta name="twitter:card" content="summary_large_image">
<link rel="canonical" href="__CANONICAL__">
<link rel="icon" href="/icon.svg" type="image/svg+xml"><link rel="apple-touch-icon" href="/apple-icon.png">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/pretendard/1.3.9/static/pretendard.min.css">
<style>
  :root { --bg: #f2f4f6; --ink: #191f28; --sub: #4e5968; --muted: #8b95a1; --blue: #3182f6; }
  body { margin: 0; background: #f2f4f6; color: #191f28; font-family: Pretendard, -apple-system, "Apple SD Gothic Neo", sans-serif; letter-spacing: -0.01em; word-break: keep-all; }
  main { max-width: 560px; margin: 0 auto; padding: 28px 12px 40px; }
  h1 { font-size: 26px; font-weight: 800; margin: 0 8px 16px; letter-spacing: -0.03em; }
  /* 소프트 UI: 날짜 페이지와 같은 떠 있는 흰 바, 흰 카드의 아주 옅은 그림자 */
  .gnb { position: sticky; top: 12px; z-index: 20; display: flex; justify-content: space-between; align-items: center; height: 56px; margin: -16px 0 20px; padding: 0 10px 0 18px; border-radius: 16px; background: rgba(255,255,255,.96); -webkit-backdrop-filter: saturate(180%) blur(10px); backdrop-filter: saturate(180%) blur(10px); box-shadow: 0 2px 10px rgba(16,24,40,.06); }
  .gnb .brand { font-size: 16px; font-weight: 800; letter-spacing: -0.03em; color: #191f28; text-decoration: none; }
  .gnb nav { display: flex; gap: 4px; }
  .gnb nav a { font-size: 14px; font-weight: 600; color: #4e5968; text-decoration: none; padding: 8px 12px; border-radius: 10px; }
  .gnb nav a:hover { background: #f2f4f6; }
  .gnb nav a.cta { color: #3182f6; background: #e8f3ff; }
  .gnb nav a.cta:hover { background: #d6e8ff; }
  .back { display: inline-block; margin: 0 8px 12px; font-size: 14px; font-weight: 600; color: #3182f6; text-decoration: none; }
  .search { display: block; width: 100%; box-sizing: border-box; height: 48px; border: 1.5px solid transparent; border-radius: 12px; background: #fff; box-shadow: 0 2px 10px rgba(16,24,40,.06);
            padding: 0 16px; font: 400 16px Pretendard, -apple-system, sans-serif; color: #191f28; outline: 0; }
  .search:focus { border-color: #3182f6; }
  .chips { display: flex; gap: 6px; overflow-x: auto; margin: 0 -12px; padding: 12px 12px 8px; scrollbar-width: none; }
  .chips::-webkit-scrollbar { display: none; }
  .chip { flex: none; height: 34px; padding: 0 14px; border: 0; border-radius: 999px; background: #fff; color: #4e5968;
          font: 600 14px Pretendard, -apple-system, sans-serif; cursor: pointer; }
  .chip[aria-pressed="true"] { background: #3182f6; color: #fff; }
  .month h2 { font-size: 15px; font-weight: 700; color: #4e5968; margin: 20px 8px 8px; }
  .card { background: #fff; border-radius: 20px; padding: 4px 20px; box-shadow: 0 4px 18px rgba(16,24,40,.07); }
  [id] { scroll-margin-top: 84px; }
  .item { display: flex; align-items: center; gap: 14px; padding: 14px 0; border-top: 1px solid #f2f4f6; color: inherit; text-decoration: none; }
  .item.first { border-top: 0; }
  .item img { flex: none; width: 56px; height: 56px; object-fit: cover; object-position: 100% 50%; }
  .d { display: block; font-size: 14px; color: #8b95a1; font-weight: 600; }
  .c { margin-left: 8px; font-size: 12px; color: #3182f6; }
  .t { display: block; font-size: 17px; font-weight: 700; color: #191f28; margin-top: 2px; }
  .empty { text-align: center; color: #8b95a1; font-size: 15px; padding: 40px 0; }
  .more { display: block; width: 100%; height: 52px; margin-top: 16px; border: 0; border-radius: 12px; background: #e8f3ff; color: #3182f6;
          font: 700 16px Pretendard, -apple-system, sans-serif; cursor: pointer; }
  [hidden] { display: none !important; }
  .review { display: flex; justify-content: space-between; align-items: center; margin: 0 0 12px; padding: 14px 18px; border-radius: 16px; background: #e8f3ff; color: #3182f6; font-size: 15px; font-weight: 700; text-decoration: none; }
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
<body><main>
  <header class="gnb">
    <a class="brand" href="/">매일 외국어 읽기</a>
    <nav aria-label="사이트 메뉴"><a href="__ARCHIVE__">지난 지문</a><a class="cta" href="/#subscribe">메일로 받기</a></nav>
  </header>
  <a class="back" href="__TODAY__">오늘의 지문 바로 가기 →</a>
  <h1>__TITLE__</h1>
  <p class="intro" style="margin: -8px 8px 14px">__INTRO__ <a href="#subscribe">메일로 받기</a> <a href="__HOME__">다른 언어</a></p>
__REVIEW__  <input class="search" id="q" type="search" placeholder="주제나 단어로 찾기 (예: __SEARCH_EXAMPLE__)" aria-label="지난 지문 검색" autocomplete="off">
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
</body></html>
"""


if __name__ == "__main__":
    lang, day = sys.argv[1], sys.argv[2]
    langs.get(lang)
    content = ROOT / "content" / lang / f"{day}.json"
    cat = sys.argv[3] if len(sys.argv) > 3 else (json.loads(content.read_text(encoding="utf-8"))["category"] if content.exists() else None)
    thumb.build(lang, day, cat)
    patch_page(lang, day)
    rebuild_lists(lang)
    rebuild_root()
    print(f"{SITE}/{lang}/{day}/")
