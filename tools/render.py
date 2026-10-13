"""content/<언어>/YYYY-MM-DD.json 을 tools/template.html 에 채워 <언어>/YYYY-MM-DD/index.html 을 만든다.

사용: python3 tools/render.py en 2026-10-12
음성은 <언어>/YYYY-MM-DD/audio/s1.mp3 … 가 문장 수만큼 모두 있을 때만 연결한다.
없으면 AUDIO 가 빈 배열이 되어 페이지가 브라우저 내장 음성으로 읽는다.

content JSON 형식 (지문 안 강조는 **단어**, 체크 포인트 안 코드 표시는 `표현`,
일본어 후리가나는 {漢字|かんじ} — 지문, 단어, 예문, 체크 포인트 어디서나 쓸 수 있다):
{
  "date": "2026-10-12",
  "category": "science",            # science, tech, society, future, culture, space
  "topic": "핵시계",                 # h1 의 <em> 과 썸네일, 메일 제목에 쓰인다
  "chips": ["5문장", "B1 위주", "B2 1문장", "약 3분"],
  "sentences": [{"en": "... **exact** ...", "b2": false}],   # b2: 조금 어려운 문장(영어 B2, 일본어 N4 배지)
  "words": [["exact", "정확한"]],
  "points": [{"title": "...", "body": "... `one second` ..."}],
  "answers": ["문장 1의 모범 해석", "..."],
  "advanced": [{"word": "precise", "meaning": "정밀한", "confuse": "precious(소중한)와 혼동 주의", "example": "The most **precise** clocks ..."}],
  "source": {"title": "기사 제목 (매체, YYYY-MM-DD)", "url": "https://..."}   # 검색 없이 쓴 날은 null
}
"""
import datetime as dt
import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import langs  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = Path(__file__).resolve().parent / "template.html"
DAYS = "월화수목금토일"
CATEGORIES = {"science", "tech", "society", "future", "culture", "space"}
BADGE = '<span class="badge">{}</span>'
WARN = ' <span class="warn">· {}</span>'


def esc(s):
    return html.escape(s, quote=False)


def ruby(s):
    """{漢字|かんじ} 를 <ruby>漢字<rt>かんじ</rt></ruby> 로 바꾼다(이스케이프한 문자열에 쓴다)."""
    return re.sub(r"\{([^{}|]+)\|([^{}|]+)\}", r"<ruby>\1<rp>(</rp><rt>\2</rt><rp>)</rp></ruby>", s)


def marks(s, tag):
    """이스케이프한 뒤 후리가나, **x** 를 <b>x</b> 로, `x` 를 <code>x</code> 로 바꾼다."""
    s = ruby(esc(s))
    if tag == "b":
        return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    if tag == "code":
        return re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    return s


def load(lang, day):
    c = json.loads((ROOT / "content" / lang / f"{day}.json").read_text(encoding="utf-8"))
    n = len(c["sentences"])
    problems = []
    if c.get("date") != day:
        problems.append("date 가 파일 이름과 다름")
    if c.get("category") not in CATEGORIES:
        problems.append(f"category 는 {sorted(CATEGORIES)} 중 하나")
    if not c.get("topic"):
        problems.append("topic 없음")
    if not 4 <= n <= 6:
        problems.append("문장은 4~6개")
    if len(c.get("answers", [])) != n:
        problems.append("answers 개수가 문장 수와 다름")
    if not 5 <= len(c.get("words", [])) <= 7:
        problems.append("words 는 5~7개")
    if not 1 <= len(c.get("points", [])) <= 2:
        problems.append("points 는 1~2개")
    if not 6 <= len(c.get("advanced", [])) <= 8:
        problems.append("advanced 는 6~8개")
    if problems:
        raise SystemExit(f"content/{lang}/{day}.json 확인 필요: " + ", ".join(problems))
    return c


def render(lang, day):
    L = langs.get(lang)
    c = load(lang, day)
    d = dt.date.fromisoformat(day)
    n = len(c["sentences"])
    sentences = "".join(
        f'    <div class="sent"><button class="no" type="button" data-i="{i}" aria-label="{i + 1}번 문장 듣기">{i + 1}</button>'
        f'<div class="en">{marks(s["en"], "b")}{BADGE.format(L["hard_badge"]) if s.get("b2") else ""}</div></div>\n'
        for i, s in enumerate(c["sentences"])
    )
    src = c.get("source")
    source = (f'    <p class="src">출처: <a href="{html.escape(src["url"])}" target="_blank" rel="noopener">{esc(src["title"])}</a></p>\n'
              if src else "")
    words = "".join(f'    <div class="word"><span class="w">{marks(w, "")}</span><span class="m">{esc(m)}</span></div>\n' for w, m in c["words"])
    points = "".join(
        f'    <div class="point">\n      <strong>{esc(p["title"])}</strong>\n      <p>{marks(p["body"], "code")}</p>\n    </div>\n'
        for p in c["points"]
    )
    answers = "".join(
        f'      <div class="sent"><span class="no">{i}</span><div class="ko">{marks(a, "")}</div></div>\n'
        for i, a in enumerate(c["answers"], 1)
    )
    advanced = "".join(
        f'      <div class="adv"><div class="w">{marks(a["word"], "")}</div><div class="m">{esc(a["meaning"])}'
        f'{WARN.format(ruby(esc(a["confuse"]))) if a.get("confuse") else ""}</div>\n'
        f'        <div class="ex">{marks(a["example"], "b")}</div></div>\n'
        for a in c["advanced"]
    )
    out_dir = ROOT / lang / day
    files = [f"audio/s{i}.mp3" for i in range(1, n + 1)]
    audio = json.dumps(files) if all((out_dir / f).exists() for f in files) else "[]"
    values = {
        "date_short": f"{d.month}월 {d.day}일",
        "date_label": f"{d.month}월 {d.day}일 {DAYS[d.weekday()]}요일",
        "topic": esc(c["topic"]),
        "chips": "\n".join(f'      <span class="chip{" blue" if i == 0 else ""}">{esc(t)}</span>' for i, t in enumerate(c["chips"])),
        "sentences": sentences,
        "source": source,
        "placeholder": "".join(f"{i}. &#10;" for i in range(1, n)) + f"{n}. ",
        "words": words,
        "points": points,
        "answers": answers,
        "advanced": advanced,
        "audio": audio,
        "name": L["name"],
        "head_extra": L["head_extra"] + ("\n" if L["head_extra"] else ""),
        "tools_extra": L["tools_extra"],
        "tts_lang": L["tts_lang"],
        "copy_head": L["copy_head"],
        "copy_weak": L["copy_weak"],
        "credit": f" {esc(L['credit'])}" if L.get("credit") else "",
    }
    page = TEMPLATE.read_text(encoding="utf-8")
    for k, v in values.items():
        page = page.replace("{{" + k + "}}", v)
    out = out_dir / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    return out, c["category"], audio != "[]"


if __name__ == "__main__":
    out, _, has_audio = render(sys.argv[1], sys.argv[2])
    print(out, "audio" if has_audio else "no-audio")
