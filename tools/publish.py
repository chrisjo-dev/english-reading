"""새 날짜 폴더를 사이트에 붙인다. 같은 날짜로 여러 번 돌려도 결과가 같다.

사용: python3 tools/publish.py 2026-10-12 [분야]
1. 썸네일(thumb.png) 생성
2. 날짜 페이지에 OG 태그와 상단 썸네일 삽입
3. 첫 화면(index.html)과 지난 지문(archive/index.html)을 날짜 폴더 목록으로 다시 생성
"""
import datetime as dt
import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import thumb  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://chrisjo-dev.github.io/english-reading"
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
    items = "\n".join(
        f'      <a class="item" href="../{d}/"><img src="../{d}/thumb.png" width="56" height="56" alt="" loading="lazy">'
        f'<span><span class="d">{label(d)}</span><span class="t">{html.escape(topic_of(d))}</span></span></a>'
        for d in days
    )
    (ROOT / "archive" / "index.html").write_text(f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light only"><title>지난 지문 | 매일 영어 읽기</title>
<meta property="og:title" content="지난 지문 | 매일 영어 읽기"><meta property="og:image" content="{SITE}/{latest}/thumb.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/pretendard/1.3.9/static/pretendard.min.css">
<style>
  body {{ margin: 0; background: #f2f4f6; color: #191f28; font-family: Pretendard, -apple-system, "Apple SD Gothic Neo", sans-serif; letter-spacing: -0.01em; }}
  main {{ max-width: 560px; margin: 0 auto; padding: 28px 12px 40px; }}
  h1 {{ font-size: 26px; font-weight: 800; margin: 0 8px 16px; letter-spacing: -0.03em; }}
  .card {{ background: #fff; border-radius: 20px; padding: 8px 20px; }}
  .item {{ display: flex; align-items: center; gap: 14px; padding: 14px 0; border-top: 1px solid #f2f4f6; color: inherit; text-decoration: none; }}
  .item:first-child {{ border-top: 0; }}
  .item img {{ flex: none; width: 56px; height: 56px; object-fit: cover; object-position: 100% 50%; }}
  .d {{ display: block; font-size: 14px; color: #8b95a1; font-weight: 600; }}
  .t {{ display: block; font-size: 17px; font-weight: 700; color: #191f28; margin-top: 2px; }}
</style></head>
<body><main>
  <h1>지난 지문</h1>
  <div class="card">
{items}
  </div>
</main></body></html>
""", encoding="utf-8")


if __name__ == "__main__":
    day = sys.argv[1]
    thumb.build(day, sys.argv[2] if len(sys.argv) > 2 else None)
    patch_page(day)
    rebuild_lists()
    print(f"{SITE}/{day}/")
