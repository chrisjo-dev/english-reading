"""지문 페이지의 오늘 분야 배지와 '오늘 주제 어땠어요?' 반응 카드(이슈 #13).

publish.patch_page 가 새 페이지와 지난 페이지 모두에 넣는다. 반응은 서버 없이 GA 이벤트 topic_vote 로만 모은다.
메일의 👍/👎 링크는 페이지를 ?vote=up|down&from=email 로 열고, 페이지가 같은 이벤트를 보낸다.
"""
import datetime as dt
import html
import json
import re
from pathlib import Path

import thumb

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://read.wspace.ai.kr"
VERSION = "2"

# 요일별 분야와 글 형태(tools/ROUTINE*.md 와 같아야 한다). 월요일부터.
WEEK = {
    "en": ["과학", "기술", "사회", "미래", "과학", "일상과 문화", "우주"],
    "ja": ["생활", "일본 문화", "쉬운 뉴스", "일과 학교", "과학과 자연", "여행과 장소", "계절과 날씨"],
    "de": ["일상생활", "독일어권 문화", "쉬운 뉴스", "일과 학교", "과학과 자연", "여행과 장소", "계절과 날씨"],
}
DAYS = "월화수목금토일"


def category(lang, day):
    p = ROOT / "content" / lang / f"{day}.json"
    cat = json.loads(p.read_text(encoding="utf-8")).get("category") if p.exists() else None
    return cat if cat in thumb.CATS else thumb.WEEKDAY[dt.date.fromisoformat(day).weekday()]


def week_html(lang, day):
    names = WEEK.get(lang, WEEK["en"])
    wd = dt.date.fromisoformat(day).weekday()
    parts = [f'<span class="today">{DAYS[i]} {n}</span>' if i == wd else f"{DAYS[i]} {n}" for i, n in enumerate(names)]
    return ", ".join(parts)


def rgb(t):
    return "#%02x%02x%02x" % t


CSS = "".join(
    f"  .cat-{k} {{ color: {rgb(v[1])}; background: {rgb(v[2])}; }}\n" for k, v in thumb.CATS.items()
) + (
    "  .cat { display: inline-block; font-size: 12px; font-weight: 700; padding: 2px 9px; border-radius: 999px; margin-left: 6px; vertical-align: 1px; }\n"
    "  .vote h2 { margin: 0 0 6px; }\n"
    "  .vote .desc { font-size: 14px; color: var(--sub); line-height: 1.6; margin: 0 0 14px; }\n"
    "  .vote .desc .cat { margin-left: 0; }\n"
    "  .vote-btns { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }\n"
    "  .vote-btn { display: flex; align-items: center; justify-content: center; gap: 6px; height: 48px; border-radius: 12px;"
    " border: 1.5px solid #e2e6ea; background: #fff; font: inherit; font-size: 15px; font-weight: 600; color: var(--ink); cursor: pointer; }\n"
    "  .vote-btn img { width: 22px; height: 22px; }\n"
    "  .vote-btn[aria-pressed=true] { border-color: #2a52d4; background: #eff3fd; color: #2a52d4; }\n"
    "  .vote.done .vote-btn[aria-pressed=false] { opacity: .55; }\n"
    "  .vote .thanks { font-size: 14px; font-weight: 600; color: #2a52d4; margin: 12px 0 0; }\n"
    "  .vote .week { font-size: 12.5px; color: var(--sub); line-height: 1.6; margin: 14px 0 0; padding-top: 12px; border-top: 1px solid #e2e6ea; }\n"
    "  .vote .week b { color: var(--ink); }\n"
    "  .vote .week .today { font-weight: 700; }\n"
) + "".join(f'  .vote[data-cat="{k}"] .week .today {{ color: {rgb(v[1])}; }}\n' for k, v in thumb.CATS.items())


def card_html(lang, day, cat):
    label = thumb.CATS[cat][0]
    return (
        f'  <section class="card vote" id="vote" data-v="{VERSION}" data-cat="{cat}" data-wd="{dt.date.fromisoformat(day).weekday()}">\n'
        "    <h2>오늘 주제 어땠어요?</h2>\n"
        f'    <p class="desc">오늘은 <span class="cat cat-{cat}">{html.escape(label)}</span> 분야였어요. 눌러 주시면 앞으로 어떤 주제를 더 자주 다룰지 정하는 데 써요.</p>\n'
        '    <div class="vote-btns">\n'
        '      <button class="vote-btn" type="button" data-vote="up" aria-pressed="false"><img src="/assets/vote-up.png" alt="">재밌었어요</button>\n'
        '      <button class="vote-btn" type="button" data-vote="down" aria-pressed="false"><img src="/assets/vote-down.png" alt="">별로였어요</button>\n'
        "    </div>\n"
        '    <p class="thanks" hidden>고마워요. 다음 주제를 고를 때 참고할게요. 다시 누르면 바꿀 수 있어요.</p>\n'
        f'    <p class="week"><b>요일마다 분야가 바뀌어요</b><br>{week_html(lang, day)}</p>\n'
        "  </section>\n"
    )


SCRIPT = """<script id="vote-js">
(function () {
  var card = document.getElementById('vote'); if (!card) return;
  var p = location.pathname.split('/'), lang = p[1] || '', day = p[2] || '';
  var KEY = 'vote:' + lang + '/' + day, btns = card.querySelectorAll('.vote-btn');
  function show(v) {
    [].forEach.call(btns, function (b) { b.setAttribute('aria-pressed', String(b.getAttribute('data-vote') === v)); });
    card.classList.toggle('done', !!v);
    card.querySelector('.thanks').hidden = !v;
  }
  function send(v, from) {
    var prev = null; try { prev = localStorage.getItem(KEY); } catch (e) {}
    show(v);
    if (prev === v) return;
    try { localStorage.setItem(KEY, v); } catch (e) {}
    if (typeof gtag === 'function') gtag('event', 'topic_vote', {
      lang: lang, day: day, cat: card.getAttribute('data-cat'), weekday: card.getAttribute('data-wd'),
      level: document.documentElement.classList.contains('level-a') ? 'a' : 'b', vote: v, from: from, changed: !!prev
    });
  }
  [].forEach.call(btns, function (b) { b.addEventListener('click', function () { send(b.getAttribute('data-vote'), 'page'); }); });
  try { var saved = localStorage.getItem(KEY); if (saved) show(saved); } catch (e) {}
  var q = new URLSearchParams(location.search), v = q.get('vote');
  if (v === 'up' || v === 'down') {
    send(v, q.get('from') || 'link');
    q.delete('vote'); q.delete('from');
    var s = q.toString();
    history.replaceState(null, '', location.pathname + (s ? '?' + s : '') + '#vote');
    card.scrollIntoView({ block: 'center' });
  }
})();
</script>
"""


def apply(page, lang, day):
    """페이지에 배지, 카드, CSS, 스크립트를 넣는다. 이미 같은 버전이 있으면 그대로 둔다(여러 번 돌려도 같다)."""
    if f'id="vote" data-v="{VERSION}"' in page:
        return page
    cat = category(lang, day)
    page = re.sub(r'\s*<section class="card vote" id="vote".*?</section>\n', "\n", page, count=1, flags=re.S)
    page = re.sub(r'<script id="vote-js">.*?</script>\n', "", page, count=1, flags=re.S)
    page = re.sub(r' <span class="cat cat-[a-z]+">[^<]*</span>', "", page, count=1)
    page = re.sub(r"  /\* vote-css \*/\n.*?  /\* /vote-css \*/\n", "", page, count=1, flags=re.S)
    page = page.replace("  .gnb {", "  /* vote-css */\n" + CSS + "  /* /vote-css */\n  .gnb {", 1)
    page = re.sub(r'(<div class="date">[^<]*)</div>',
                  lambda m: f'{m.group(1)} <span class="cat cat-{cat}">{html.escape(thumb.CATS[cat][0])}</span></div>', page, count=1)
    card = card_html(lang, day, cat)
    for anchor in ('  <details class="card">', '  <section class="card sub"', "</main>"):
        if anchor in page:
            page = page.replace(anchor, card + "\n" + anchor, 1)
            break
    return page.replace("</body>", SCRIPT + "</body>", 1)
