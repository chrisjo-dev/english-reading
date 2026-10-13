"""한 언어의 새 날짜 폴더를 사이트에 붙인다. 같은 날짜로 여러 번 돌려도 결과가 같다.

사용: python3 tools/publish.py en 2026-10-12 [분야]  (분야를 생략하면 content JSON 의 category)
1. 썸네일(<언어>/<날짜>/thumb.png) 생성
2. 날짜 페이지에 OG 태그, 상단 썸네일, 소개 문구, 구독 칸 삽입
3. 그 언어의 지난 지문(<언어>/archive/), 언어 첫 화면(<언어>/), 사이트 첫 화면(언어 선택)을 다시 생성
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

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://read.wspace.ai.kr"
SUBSCRIBE = "https://buttondown.com/api/emails/embed-subscribe/english-reading"
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
DAYS = "월화수목금토일"

# 처음 온 사람을 위한 한 줄 소개와 구독 칸. 날짜 페이지와 지난 지문 페이지에 같이 쓴다(색은 각 페이지의 CSS 변수).
INTRO_CSS = ("  .intro { margin: 14px 0 0; font-size: 14px; line-height: 1.6; color: var(--sub); }\n"
             "  .intro a { color: var(--blue); font-weight: 600; text-decoration: none; margin-right: 6px; }\n")
SUB_CSS = (
    "  .sub { scroll-margin-top: 16px; }\n"
    "  .sub h2 { margin-bottom: 4px; }\n  .sub p { margin: 0 0 14px; font-size: 15px; color: var(--sub); }\n"
    "  .sub form { display: flex; gap: 8px; }\n"
    "  .sub input { flex: 1; min-width: 0; height: 48px; border: 1.5px solid transparent; border-radius: 12px; background: var(--bg);"
    " padding: 0 14px; font: 400 16px Pretendard, -apple-system, sans-serif; color: var(--ink); outline: 0; }\n"
    "  .sub input:focus { border-color: var(--blue); background: #fff; }\n"
    "  .sub button { flex: none; height: 48px; padding: 0 18px; border: 0; border-radius: 12px; background: var(--blue); color: #fff;"
    " font: 700 15px Pretendard, -apple-system, sans-serif; cursor: pointer; }\n"
    "  .sub .note { margin: 10px 0 0; font-size: 13px; line-height: 1.6; color: var(--muted); }\n"
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


def sub_html(lang):
    """구독 칸. 숨은 입력값 metadata__lang 으로 구독자의 언어를 Buttondown 에 저장해 언어별로 보낸다."""
    L = langs.get(lang)
    return (
        '  <section class="card sub" id="subscribe">\n'
        f"    <h2>매일 아침 {L['name']} 지문 받기</h2>\n"
        f"    <p>새 {L['name']} 지문이 올라오면 아침에 메일로 보내 드려요.</p>\n"
        f'    <form action="{SUBSCRIBE}" method="post" target="_blank">\n'
        f'      <input type="hidden" name="metadata__lang" value="{lang}">\n'
        '      <input type="email" name="email" required placeholder="이메일 주소" autocomplete="email" aria-label="이메일 주소">\n'
        '      <button type="submit">구독하기</button>\n'
        "    </form>\n"
        "    <p class=\"note\">지금은 이메일 주소 하나로 한 언어만 구독할 수 있어요. 두 언어를 받으려면 서로 다른 이메일로 구독해 주세요.</p>\n"
        "    <p class=\"note\">구독하면 영문 확인 메일(Confirm your subscription)이 가요. 메일 속 버튼을 눌러야 구독이 끝나요. 메일이 안 보이면 스팸함도 확인해 주세요.</p>\n"
        '    <p class="note">이메일은 뉴스레터 발송에만 쓰이고, 언제든 메일 하단에서 수신거부할 수 있어요.</p>\n'
        "  </section>\n"
    )


def days_of(lang):
    d = ROOT / lang
    return sorted((p.name for p in d.iterdir() if DATE_RE.fullmatch(p.name) and (p / "index.html").exists()), reverse=True) if d.exists() else []


def topic_of(lang, day):
    page = (ROOT / lang / day / "index.html").read_text(encoding="utf-8")
    return html.unescape(re.search(r"<h1>.*?<em>(.*?)</em>", page, re.S).group(1).strip())


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
            "  .nav {",
            "  .top { position: relative; }\n  .thumb { position: absolute; top: 18px; right: 18px; width: 76px; height: 76px; object-fit: cover; object-position: 100% 50%; }\n  .nav {",
            1,
        )
        page = page.replace(
            '<div class="date">',
            f'<img class="thumb" src="thumb.png" width="76" height="76" alt="">\n    <div class="date">',
            1,
        )
    if 'class="site-footer"' not in page:
        page = page.replace("  .nav {", "  " + FOOTER_CSS + "  .site-footer { padding-bottom: 110px; }\n  .nav {", 1)
        page = page.replace("</main>", "</main>\n" + FOOTER_HTML, 1)
        page = page.replace("<link rel=\"stylesheet\"", f'<link rel="canonical" href="{url}">\n<link rel="stylesheet"', 1)
    if 'class="card sub"' not in page:
        page = page.replace("  .nav {", SUB_CSS + "  .intro {", 1)
        page = page.replace("  .intro {", INTRO_CSS + "  .nav {", 1)
        page = page.replace("</main>", sub_html(lang) + "</main>", 1)
        page = page.replace("\n  </div>\n\n  <section class=\"card\" id=\"passage\">", "\n" + intro_html(lang) + "  </div>\n\n  <section class=\"card\" id=\"passage\">", 1)
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
                .replace("__TITLE__", title).replace("__TODAY__", f"{p}{latest}/").replace("__HOME__", home)
                .replace("__SITE__", L["site"]).replace("__INTRO__", L["intro"]).replace("__SEARCH_EXAMPLE__", L["search_example"])
                .replace("__CHIPS__", chips).replace("__SUB_CSS__", SUB_CSS).replace("__INTRO_CSS__", INTRO_CSS)
                .replace("__SUB_HTML__", sub_html(lang)).replace("__GROUPS__", "\n".join(groups))
                .replace("__CANONICAL__", f"{SITE}/{lang}/").replace("__FOOTER_CSS__", "  " + FOOTER_CSS).replace("__FOOTER__", FOOTER_HTML))
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
    """사이트 첫 화면(언어 선택)을 만든다."""
    cards = []
    for code, L in langs.LANGS.items():
        days = days_of(code)
        if not days:
            continue
        cards.append(
            f'  <a class="lang" href="./{code}/"><img src="./{code}/{days[0]}/thumb.png" alt="" width="1200" height="630">'
            f'<span class="name">{L["name"]} <span class="lv">{L["level"]}</span></span>'
            f'<span class="today">지문 {len(days)}개, 오늘: {html.escape(topic_of(code, days[0]))} →</span></a>'
        )
    page = (ROOT_PAGE.replace("__CARDS__", "\n".join(cards)).replace("__SITE__", SITE)
            .replace("__FOOTER_CSS__", "  " + FOOTER_CSS).replace("__FOOTER__", FOOTER_HTML))
    (ROOT / "index.html").write_text(page, encoding="utf-8")
    write_sitemap()


def write_sitemap():
    """검색엔진용 사이트맵과 robots.txt. 언어 목록, 날짜 페이지, 주간 복습을 모두 싣는다."""
    urls = [f"{SITE}/"]
    for code in langs.LANGS:
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


ROOT_PAGE = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light only"><title>매일 외국어 읽기</title>
<meta name="description" content="매일 아침 새로 올라오는 외국어 읽기. 문장별 음성, 주요 단어, 모범 해석.">
<meta property="og:title" content="매일 외국어 읽기"><meta name="twitter:card" content="summary_large_image">
<link rel="canonical" href="__SITE__/">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/pretendard/1.3.9/static/pretendard.min.css">
<style>
  body { margin: 0; background: #f2f4f6; color: #191f28; font-family: Pretendard, -apple-system, "Apple SD Gothic Neo", sans-serif; letter-spacing: -0.01em; word-break: keep-all; }
  main { max-width: 560px; margin: 0 auto; padding: 36px 12px 40px; }
  h1 { font-size: 26px; font-weight: 800; margin: 0 8px 6px; letter-spacing: -0.03em; }
  .lead { margin: 0 8px 20px; font-size: 15px; line-height: 1.6; color: #4e5968; }
  .lang { display: block; background: #fff; border-radius: 20px; overflow: hidden; color: inherit; text-decoration: none; margin-bottom: 12px; }
  .lang img { display: block; width: 100%; height: auto; }
  .name { display: block; padding: 16px 20px 2px; font-size: 20px; font-weight: 800; }
  .lv { margin-left: 6px; font-size: 13px; font-weight: 700; color: #3182f6; }
  .today { display: block; padding: 0 20px 18px; font-size: 15px; color: #4e5968; }
__FOOTER_CSS__</style></head>
<body><main>
  <h1>매일 외국어 읽기</h1>
  <p class="lead">매일 아침 짧은 지문 하나. 듣고, 해석하고, AI에게 피드백을 받아 보세요. 배우는 언어를 고르세요.</p>
__CARDS__
</main>
__FOOTER__</body></html>
"""


# 지난 지문 페이지. 검색과 분야 필터, 30개씩 더 보기를 브라우저에서 처리한다(스크립트가 없어도 전체 목록은 보인다).
ARCHIVE = r"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light only"><title>__TITLE__ | __SITE__</title>
<meta property="og:title" content="지난 지문 | __SITE__"><meta property="og:image" content="__OG_IMAGE__">
<meta name="twitter:card" content="summary_large_image">
<link rel="canonical" href="__CANONICAL__">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/pretendard/1.3.9/static/pretendard.min.css">
<style>
  :root { --bg: #f2f4f6; --ink: #191f28; --sub: #4e5968; --muted: #8b95a1; --blue: #3182f6; }
  body { margin: 0; background: #f2f4f6; color: #191f28; font-family: Pretendard, -apple-system, "Apple SD Gothic Neo", sans-serif; letter-spacing: -0.01em; word-break: keep-all; }
  main { max-width: 560px; margin: 0 auto; padding: 28px 12px 40px; }
  h1 { font-size: 26px; font-weight: 800; margin: 0 8px 16px; letter-spacing: -0.03em; }
  .back { display: inline-block; margin: 0 8px 12px; font-size: 14px; font-weight: 600; color: #3182f6; text-decoration: none; }
  .search { display: block; width: 100%; box-sizing: border-box; height: 48px; border: 1.5px solid transparent; border-radius: 14px; background: #fff;
            padding: 0 16px; font: 400 16px Pretendard, -apple-system, sans-serif; color: #191f28; outline: 0; }
  .search:focus { border-color: #3182f6; }
  .chips { display: flex; gap: 6px; overflow-x: auto; padding: 10px 0 4px; scrollbar-width: none; }
  .chips::-webkit-scrollbar { display: none; }
  .chip { flex: none; height: 34px; padding: 0 14px; border: 0; border-radius: 10px; background: #fff; color: #4e5968;
          font: 600 14px Pretendard, -apple-system, sans-serif; cursor: pointer; }
  .chip[aria-pressed="true"] { background: #3182f6; color: #fff; }
  .month h2 { font-size: 15px; font-weight: 700; color: #4e5968; margin: 20px 8px 8px; }
  .card { background: #fff; border-radius: 20px; padding: 4px 20px; }
  .item { display: flex; align-items: center; gap: 14px; padding: 14px 0; border-top: 1px solid #f2f4f6; color: inherit; text-decoration: none; }
  .item.first { border-top: 0; }
  .item img { flex: none; width: 56px; height: 56px; object-fit: cover; object-position: 100% 50%; }
  .d { display: block; font-size: 14px; color: #8b95a1; font-weight: 600; }
  .c { margin-left: 8px; font-size: 12px; color: #3182f6; }
  .t { display: block; font-size: 17px; font-weight: 700; color: #191f28; margin-top: 2px; }
  .empty { text-align: center; color: #8b95a1; font-size: 15px; padding: 40px 0; }
  .more { display: block; width: 100%; height: 52px; margin-top: 16px; border: 0; border-radius: 14px; background: #e8f3ff; color: #3182f6;
          font: 700 16px Pretendard, -apple-system, sans-serif; cursor: pointer; }
  [hidden] { display: none !important; }
  .review { display: flex; justify-content: space-between; align-items: center; margin: 0 0 12px; padding: 14px 18px; border-radius: 16px; background: #e8f3ff; color: #3182f6; font-size: 15px; font-weight: 700; text-decoration: none; }
  .sub-wrap { margin-top: 28px; }
  .sub-wrap .card { padding: 22px 20px; }
  .sub-wrap h2 { font-size: 20px; font-weight: 700; margin: 0 0 4px; }
__SUB_CSS____INTRO_CSS____FOOTER_CSS__</style></head>
<body><main>
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
