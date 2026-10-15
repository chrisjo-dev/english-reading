"""그 주(오늘 포함 7일)의 주요 단어를 모아 복습 페이지 <언어>/review/YYYY-MM-DD/index.html 을 만든다.

사용: python3 tools/weekly.py en 2026-10-18          # 페이지 생성
      python3 tools/weekly.py en 2026-10-18 --email  # 메일 제목과 본문 JSON 출력
날짜는 복습을 보내는 날(보통 일요일)이고, 그날부터 6일 전까지의 content JSON 을 모은다.
"""
import datetime as dt
import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import langs  # noqa: E402
from render import ruby  # noqa: E402
from publish import FOOTER_CSS, FOOTER_HTML  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://read.wspace.ai.kr"
DAYS = "월화수목금토일"


def collect(lang, end):
    end_d = dt.date.fromisoformat(end)
    out = []
    for i in range(6, -1, -1):
        d = (end_d - dt.timedelta(days=i)).isoformat()
        f = ROOT / "content" / lang / f"{d}.json"
        if f.exists():
            c = json.loads(f.read_text(encoding="utf-8"))
            out.append({"day": d, "topic": c["topic"], "words": c["words"]})
    return out


def span(end):
    e = dt.date.fromisoformat(end)
    s = e - dt.timedelta(days=6)
    return f"{s.month}월 {s.day}일~{e.month}월 {e.day}일"


def plain(word):
    """메일용: {漢字|かんじ} 를 漢字(かんじ) 로."""
    return re.sub(r"\{([^{}|]+)\|([^{}|]+)\}", r"\1(\2)", word)


def short(day):
    d = dt.date.fromisoformat(day)
    return f"{d.month}/{d.day}({DAYS[d.weekday()]})"


def build_page(lang, end):
    L = langs.get(lang)
    days = collect(lang, end)
    if not days:
        raise SystemExit(f"{end} 까지 7일 동안 올라온 지문이 없어 복습을 만들지 않음")
    total = sum(len(x["words"]) for x in days)
    groups = []
    for x in days:
        cards = "".join(
            f'<button class="w" type="button" aria-expanded="false"><span class="en">{ruby(html.escape(w))}</span>'
            f'<span class="ko">{html.escape(m)}</span></button>'
            for w, m in x["words"]
        )
        groups.append(
            f'  <section class="day">\n    <h2>{short(x["day"])} <a href="../../{x["day"]}/">{html.escape(x["topic"])}</a></h2>\n'
            f'    <div class="grid">{cards}</div>\n  </section>'
        )
    page = PAGE.replace("__SITE__", L["site"]).replace("__HEAD_EXTRA__", L["head_extra"]).replace("__SPAN__", span(end)).replace("__TOTAL__", str(total)).replace("__COUNT__", str(len(days)))
    page = page.replace("__GROUPS__", "\n".join(groups)).replace("__URL__", f"{SITE}/{lang}/review/{end}/")
    page = page.replace("__FOOTER_CSS__", "  " + FOOTER_CSS).replace("__FOOTER__", FOOTER_HTML)
    page = page.replace("__OG_IMAGE__", f"{SITE}/{lang}/{days[-1]['day']}/thumb.png")
    out = ROOT / lang / "review" / end / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    return out


def build_email(lang, end):
    L = langs.get(lang)
    days = collect(lang, end)
    url = f"{SITE}/{lang}/review/{end}/"
    font = "-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo','Noto Sans KR','Malgun Gothic','Hiragino Sans','Noto Sans JP',sans-serif"
    rows = "".join(
        f'<tr><td style="padding:10px 0;border-top:1px solid #f2f4f6;font-size:13px;font-weight:700;color:#8b95a1;white-space:nowrap;vertical-align:top;">{short(x["day"])}</td>'
        f'<td style="padding:10px 0 10px 12px;border-top:1px solid #f2f4f6;font-size:16px;line-height:1.6;color:#191f28;">'
        f'{", ".join(html.escape(plain(w)) for w, _ in x["words"])}</td></tr>'
        for x in days
    )
    total = sum(len(x["words"]) for x in days)
    body = f"""<!-- buttondown-editor-mode: plaintext -->
<div style="background:#f2f4f6;padding:16px 0;font-family:{font};word-break:keep-all;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;margin:0 auto;">
<tr><td style="background:#ffffff;border-radius:20px;padding:22px 20px;">
  <p style="margin:0;font-size:14px;font-weight:600;color:#8b95a1;">{span(end)}</p>
  <h1 style="margin:6px 0 8px;font-size:24px;line-height:1.35;font-weight:800;color:#191f28;">이번 주 <span style="color:#3182f6;">단어 {total}개</span> 복습해요</h1>
  <p style="margin:0 0 14px;font-size:15px;line-height:1.6;color:#4e5968;">뜻이 바로 떠오르는지 먼저 확인해 보세요. 버튼을 누르면 단어 카드를 눌러 뜻을 하나씩 확인할 수 있어요.</p>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">{rows}</table>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:18px;"><tr>
    <td align="center" style="background:#3182f6;border-radius:14px;">
      <a href="{url}" style="display:block;padding:16px 12px;font-size:16px;font-weight:700;color:#ffffff;text-decoration:none;">뜻 가리고 복습하기</a>
    </td></tr></table>
</td></tr>
<tr><td style="padding:16px 8px 0;font-size:13px;color:#8b95a1;text-align:center;">
  <a href="{SITE}/{lang}/archive/" style="color:#4e5968;">지난 지문 모아 보기</a>
  <p style="margin:12px 0 0;font-size:12px;line-height:1.6;color:#8b95a1;">매일 아침 {L["level"]} {L["name"]} 지문을, 일요일에는 한 주 단어 복습을 보내 드려요.<br>
  더 받지 않으려면 <a href="{{{{ unsubscribe_url }}}}" style="color:#8b95a1;">수신거부</a>를 눌러 주세요.</p>
</td></tr>
</table>
</div>"""
    return {"subject": f"이번 주 단어 {total}개 복습 ({span(end)}) | {L['site']}", "body": body, "url": url}


# 복습 페이지. 단어 카드를 누르면 뜻이 보인다. 날짜 페이지와 같은 색과 글꼴을 쓴다.
PAGE = r"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light only"><title>이번 주 단어 복습 | __SITE__</title>
<meta name="description" content="__SPAN__ 동안 나온 주요 단어 __TOTAL__개를 뜻을 가리고 복습해요.">
<meta property="og:title" content="이번 주 단어 복습 (__SPAN__) | __SITE__">
<meta property="og:url" content="__URL__"><meta property="og:image" content="__OG_IMAGE__"><meta name="twitter:card" content="summary_large_image">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/pretendard/1.3.9/static/pretendard.min.css">
__HEAD_EXTRA__
<style>
  body { margin: 0; background: #f2f4f6; color: #191f28; font-family: Pretendard, -apple-system, "Apple SD Gothic Neo", sans-serif; letter-spacing: -0.01em; word-break: keep-all; }
  main { max-width: 560px; margin: 0 auto; padding: 28px 12px 40px; }
  .back { display: inline-block; margin: 0 8px 12px; font-size: 14px; font-weight: 600; color: #3182f6; text-decoration: none; }
  .head { background: #fff; border-radius: 20px; padding: 22px 20px; }
  .span { font-size: 14px; font-weight: 600; color: #8b95a1; }
  h1 { font-size: 26px; font-weight: 800; line-height: 1.35; margin: 6px 0 8px; letter-spacing: -0.03em; }
  h1 em { font-style: normal; color: #3182f6; }
  .lead { margin: 0 0 16px; font-size: 15px; line-height: 1.6; color: #4e5968; }
  .toggle { width: 100%; height: 48px; border: 0; border-radius: 14px; background: #e8f3ff; color: #3182f6; font: 700 15px Pretendard, -apple-system, sans-serif; cursor: pointer; }
  .day { margin-top: 20px; }
  .day h2 { font-size: 15px; font-weight: 700; color: #4e5968; margin: 0 8px 8px; }
  .day h2 a { color: #191f28; text-decoration: none; margin-left: 4px; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
  .w { display: flex; flex-direction: column; justify-content: center; gap: 4px; min-height: 76px; padding: 12px 14px; border: 0; border-radius: 16px;
       background: #fff; text-align: left; cursor: pointer; font-family: inherit; color: inherit; }
  .w .en { font-size: 17px; font-weight: 700; letter-spacing: 0; overflow-wrap: anywhere; }
  .w .ko { font-size: 14px; line-height: 1.5; color: #4e5968; visibility: hidden; }
  .w[aria-expanded="true"] { background: #e8f3ff; }
  .w[aria-expanded="true"] .ko { visibility: visible; }
__FOOTER_CSS__</style>
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-2339195232447097"
     crossorigin="anonymous"></script>
<script async src="https://www.googletagmanager.com/gtag/js?id=G-43L9WRDB2N"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}gtag('js',new Date());gtag('config','G-43L9WRDB2N',{anonymize_ip:true});</script>
<script>(function(c,l,a,r,i,t,y){c[a]=c[a]||function(){(c[a].q=c[a].q||[]).push(arguments)};t=l.createElement(r);t.async=1;t.src="https://www.clarity.ms/tag/"+i;y=l.getElementsByTagName(r)[0];y.parentNode.insertBefore(t,y);})(window,document,"clarity","script","yxuphaowch");</script>
</head>
<body><main>
  <a class="back" href="../../archive/">← 지난 지문</a>
  <div class="head">
    <div class="span">__SPAN__</div>
    <h1>이번 주 <em>단어 __TOTAL__개</em> 복습</h1>
    <p class="lead">__COUNT__일 동안 나온 주요 단어예요. 뜻을 먼저 떠올려 보고, 카드를 눌러 확인하세요.</p>
    <button class="toggle" id="all" type="button">뜻 모두 보기</button>
  </div>
__GROUPS__
</main>
__FOOTER__<script>
  var cards = [].slice.call(document.querySelectorAll('.w')), all = document.getElementById('all'), open = false;
  cards.forEach(function (c) {
    c.addEventListener('click', function () { c.setAttribute('aria-expanded', String(c.getAttribute('aria-expanded') !== 'true')); });
  });
  all.addEventListener('click', function () {
    open = !open;
    cards.forEach(function (c) { c.setAttribute('aria-expanded', String(open)); });
    all.textContent = open ? '뜻 모두 가리기' : '뜻 모두 보기';
  });
</script>
</body></html>
"""


if __name__ == "__main__":
    if "--email" in sys.argv:
        json.dump(build_email(sys.argv[1], sys.argv[2]), sys.stdout, ensure_ascii=False)
    else:
        print(build_page(sys.argv[1], sys.argv[2]))
