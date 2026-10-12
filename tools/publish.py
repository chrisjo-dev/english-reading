"""새 날짜 폴더를 사이트에 붙인다. 같은 날짜로 여러 번 돌려도 결과가 같다.

사용: python3 tools/publish.py 2026-10-12 [분야]  (분야를 생략하면 content JSON 의 category)
1. 썸네일(thumb.png) 생성
2. 날짜 페이지에 OG 태그와 상단 썸네일 삽입
3. 첫 화면(index.html)과 지난 지문(archive/index.html)을 날짜 폴더 목록으로 다시 생성
"""
import datetime as dt
import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import thumb  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://chrisjo-dev.github.io/english-reading"
SUBSCRIBE = "https://buttondown.com/api/emails/embed-subscribe/english-reading"
DAYS = "월화수목금토일"


def topic_of(day):
    page = (ROOT / day / "index.html").read_text(encoding="utf-8")
    return html.unescape(re.search(r"<h1>.*?<em>(.*?)</em>", page, re.S).group(1).strip())


def label(day):
    d = dt.date.fromisoformat(day)
    return f"{d.month}월 {d.day}일 {DAYS[d.weekday()]}요일"


def patch_page(day):
    path = ROOT / day / "index.html"
    page = path.read_text(encoding="utf-8")
    if 'property="og:image"' not in page:
        title = html.escape(f"오늘은 {topic_of(day)} 이야기예요 | 매일 영어 읽기")
        desc = "CEFR B1~B2 학습자를 위한 하루 5문장 영어 읽기. 문장별 음성, 주요 단어, 모범 해석."
        meta = (
            f'<meta name="description" content="{desc}">\n'
            f'<meta property="og:type" content="article">\n'
            f'<meta property="og:site_name" content="매일 영어 읽기">\n'
            f'<meta property="og:title" content="{title}">\n'
            f'<meta property="og:description" content="{desc}">\n'
            f'<meta property="og:url" content="{SITE}/{day}/">\n'
            f'<meta property="og:image" content="{SITE}/{day}/thumb.png">\n'
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
    if 'class="card sub"' not in page:
        page = page.replace(
            "  .nav {",
            "  .sub h2 { margin-bottom: 4px; }\n  .sub p { margin: 0 0 14px; font-size: 15px; color: var(--sub); }\n"
            "  .sub form { display: flex; gap: 8px; }\n"
            "  .sub input { flex: 1; min-width: 0; height: 48px; border: 1.5px solid transparent; border-radius: 12px; background: var(--bg);"
            " padding: 0 14px; font: 400 16px Pretendard, -apple-system, sans-serif; color: var(--ink); outline: 0; }\n"
            "  .sub input:focus { border-color: var(--blue); background: #fff; }\n"
            "  .sub button { flex: none; height: 48px; padding: 0 18px; border: 0; border-radius: 12px; background: var(--blue); color: #fff;"
            " font: 700 15px Pretendard, -apple-system, sans-serif; cursor: pointer; }\n"
            "  .sub .note { margin: 10px 0 0; font-size: 13px; color: var(--muted); }\n  .nav {",
            1,
        )
        page = page.replace(
            "</main>",
            '  <section class="card sub">\n'
            "    <h2>매일 아침 메일로 받기</h2>\n"
            "    <p>새 지문이 올라오면 아침에 메일로 보내 드려요.</p>\n"
            f'    <form action="{SUBSCRIBE}" method="post" target="_blank">\n'
            '      <input type="email" name="email" required placeholder="이메일 주소" autocomplete="email" aria-label="이메일 주소">\n'
            '      <button type="submit">구독하기</button>\n'
            "    </form>\n"
            '    <p class="note">이메일은 뉴스레터 발송에만 쓰입니다. 언제든 메일 하단에서 수신거부할 수 있어요.</p>\n'
            "  </section>\n</main>",
            1,
        )
    path.write_text(page, encoding="utf-8")


def rebuild_lists():
    days = sorted((p.name for p in ROOT.iterdir() if re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.name)), reverse=True)
    latest = days[0]
    (ROOT / "index.html").write_text(
        '<!doctype html>\n<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'<title>매일 영어 읽기</title><meta http-equiv="refresh" content="0; url=./{latest}/">\n'
        f'<meta property="og:title" content="매일 영어 읽기"><meta property="og:image" content="{SITE}/{latest}/thumb.png">\n'
        f'<meta name="twitter:card" content="summary_large_image"></head>\n'
        f'<body><p><a href="./{latest}/">오늘의 지문으로 이동</a></p></body></html>\n',
        encoding="utf-8",
    )
    entries = [entry(d) for d in days]
    cats = [c for c in thumb.CATS if any(e["cat"] == c for e in entries)]
    chips = "".join(
        f'<button type="button" class="chip" data-cat="{c}" aria-pressed="false">{thumb.CATS[c][0]}</button>' for c in cats
    )
    groups, month = [], None
    for e in entries:
        if e["month"] != month:
            if month is not None:
                groups.append("    </div>\n  </section>")
            month = e["month"]
            groups.append(f'  <section class="month">\n    <h2>{month}</h2>\n    <div class="card">')
        groups.append(
            f'      <a class="item" href="../{e["day"]}/" data-cat="{e["cat"]}" data-q="{html.escape(e["q"])}">'
            f'<img src="../{e["day"]}/thumb.png" width="56" height="56" alt="" loading="lazy">'
            f'<span><span class="d">{e["label"]}<span class="c">{e["cat_label"]}</span></span>'
            f'<span class="t">{html.escape(e["topic"])}</span></span></a>'
        )
    groups.append("    </div>\n  </section>")
    page = (ARCHIVE.replace("__OG_IMAGE__", f"{SITE}/{latest}/thumb.png")
            .replace("__CHIPS__", chips).replace("__GROUPS__", "\n".join(groups)))
    (ROOT / "archive" / "index.html").write_text(page, encoding="utf-8")


def entry(day):
    """목록 한 줄에 필요한 값. content JSON 이 있으면 분야와 주요 단어까지 검색어에 넣는다."""
    d = dt.date.fromisoformat(day)
    content = ROOT / "content" / f"{day}.json"
    c = json.loads(content.read_text(encoding="utf-8")) if content.exists() else {}
    topic = c.get("topic") or topic_of(day)
    cat = c.get("category") or thumb.WEEKDAY[d.weekday()]
    words = " ".join(f"{w} {m}" for w, m in c.get("words", []))
    return {
        "day": day, "topic": topic, "cat": cat, "cat_label": thumb.CATS[cat][0],
        "label": label(day), "month": f"{d.year}년 {d.month}월",
        "q": f"{topic} {thumb.CATS[cat][0]} {words}".lower(),
    }


# 지난 지문 페이지. 검색과 분야 필터, 30개씩 더 보기를 브라우저에서 처리한다(스크립트가 없어도 전체 목록은 보인다).
ARCHIVE = r"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light only"><title>지난 지문 | 매일 영어 읽기</title>
<meta property="og:title" content="지난 지문 | 매일 영어 읽기"><meta property="og:image" content="__OG_IMAGE__">
<meta name="twitter:card" content="summary_large_image">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/pretendard/1.3.9/static/pretendard.min.css">
<style>
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
</style></head>
<body><main>
  <a class="back" href="../">← 오늘의 지문</a>
  <h1>지난 지문</h1>
  <input class="search" id="q" type="search" placeholder="주제나 단어로 찾기 (예: satellite, 핵시계)" aria-label="지난 지문 검색" autocomplete="off">
  <div class="chips" role="group" aria-label="분야"><button type="button" class="chip" data-cat="" aria-pressed="true">전체</button>__CHIPS__</div>
__GROUPS__
  <p class="empty" id="empty" hidden>찾는 지문이 없어요.</p>
  <button class="more" id="more" type="button" hidden>더 보기</button>
</main>
<script>
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
    day = sys.argv[1]
    content = ROOT / "content" / f"{day}.json"
    cat = sys.argv[2] if len(sys.argv) > 2 else (json.loads(content.read_text(encoding="utf-8"))["category"] if content.exists() else None)
    thumb.build(day, cat)
    patch_page(day)
    rebuild_lists()
    print(f"{SITE}/{day}/")
