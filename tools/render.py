"""content/<언어>/YYYY-MM-DD.json 을 tools/template.html 에 채워 <언어>/YYYY-MM-DD/index.html 을 만든다.

사용: python3 tools/render.py en 2026-10-12
음성은 <언어>/YYYY-MM-DD/audio/s1.mp3 … 가 문장 수만큼 모두 있을 때만 연결한다.
없으면 AUDIO 가 빈 배열이 되어 페이지가 브라우저 내장 음성으로 읽는다.

content JSON 형식 (지문 안 강조는 **단어**, 체크 포인트 안 코드 표시는 `표현`,
일본어 후리가나는 {漢字|かんじ} — 지문, 단어, 예문, 체크 포인트 어디서나 쓸 수 있다):
{
  "date": "2026-10-12",
  "category": "science",            # science, tech, society, future, culture, space
  "topic": "핵시계",                 # 짧은 주제어. 썸네일, 지난 지문 목록, 첫 화면에 쓰인다
  "title_ko": "세상에서 가장 정확한 시계",  # 페이지 h1 과 메일 제목("오늘은 ... 이야기예요")
  "headline": "The Most Exact Clock in the World",  # h1 아래 작은 제목. 지문 언어로, 지문보다 쉽게
  "chips": ["5문장", "B1 위주", "B2 1문장", "약 3분"],
  "sentences": [{"en": "... **exact** ...", "b2": false,    # b2: 조금 어려운 문장(영어 B2, 일본어 N4 배지)
                 "chunks": [["...", "짧은 뜻"], ["**exact** ...", "..."]]}],  # 영어만, 선택. 끊어 읽기 덩어리(공백으로 이으면 en 과 같아야 한다)
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
import math
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
WARN = '<span class="warn">{}</span>'


# 출처가 없는 글도 성격을 밝힌다. 기사 없이 쓴 생활 주제 글과, 사례를 지어낸 예문을 구분한다.
NO_SOURCE_NOTE = "특정 기사를 바탕으로 하지 않은 학습용 글입니다."
EXAMPLE_NOTE = "실제 사례가 아니라 학습용으로 지어낸 이야기입니다. 등장하는 장소, 인물, 숫자는 예시입니다."


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


def plain_word_tts(text, lang):
    """단어를 TTS에 넘길 수 있게 가공한다.
    ** 와 괄호 주석을 제거하고, 일본어는 {漢字|かな}를 가나 읽기로, 영어는 한자로 바꾼다."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\s*\([^)]*\)", "", text)
    if lang == "ja":
        text = re.sub(r"\{([^{}|]+)\|([^{}|]+)\}", r"\2", text)
    else:
        text = re.sub(r"\{([^{}|]+)\|([^{}|]+)\}", r"\1", text)
    return text.strip()


_SPKR_BTN = (
    '<button class="wbtn" type="button" data-kind="{kind}" data-i="{i}"'
    ' data-word="{word}" aria-label="{word} 발음 듣기">'
    '<svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">'
    '<path d="M9.5 5v10a.5.5 0 0 1-.8.4l-3.2-2.4H4a1 1 0 0 1-1-1V8a1 1 0 0 1 1-1h1.5L8.7 4.6A.5.5 0 0 1 9.5 5z"/>'
    '<path d="M12.5 7.5a3 3 0 0 1 0 5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>'
    '</svg></button>'
)


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
    # levels 필드 파싱 (없으면 None)
    c["_levels_a"] = (c.get("levels") or {}).get("a")
    return c


def chunk_rows(lang, day, sentences):
    """모든 문장의 chunks 가 맞으면 문장별 끊어 읽기 줄(HTML)을, 아니면 None 을 돌려준다.

    덩어리를 공백 하나로 이은 글이 문장과 정확히 같아야 하고(** 표시 포함), 각 덩어리는 영어와 뜻이 모두 있어야 한다.
    한 문장이라도 어긋나면 페이지 전체에서 끊어 읽기를 뺀다(버튼도 없음).
    chunks 플래그가 False 인 언어는 None 을 반환한다.
    """
    if not langs.LANGS.get(lang, {}).get("chunks", lang == "en"):
        return None
    if not all(s.get("chunks") for s in sentences):
        return None
    for i, s in enumerate(sentences, 1):
        ch = s["chunks"]
        ok = all(isinstance(c, list) and len(c) == 2 and all(isinstance(x, str) and x.strip() for x in c)
                 and c[0].count("**") % 2 == 0 for c in ch)
        if not ok or " ".join(c[0] for c in ch) != s["en"]:
            print(f"경고: content/{lang}/{day}.json {i}번 문장의 chunks 가 문장과 맞지 않아 끊어 읽기를 뺐어요", file=sys.stderr)
            return None
    sep = '<span class="s">/</span>'
    return [
        '<div class="chunks">' + "".join(
            f'<span class="ck"><span class="e">{marks(e, "b")}{sep if j < len(s["chunks"]) - 1 else ""}</span>'
            f'<span class="k">{esc(k)}</span></span>'
            for j, (e, k) in enumerate(s["chunks"])
        ) + "</div>"
        for s in sentences
    ]


def chunk_rows_a(lang, day, a_sentences):
    """levels.a 의 끊어 읽기 줄(HTML)을 만든다. chunk_rows 와 같은 규칙, 클래스만 다르다."""
    if not langs.LANGS.get(lang, {}).get("chunks", lang == "en"):
        return None
    if not all(s.get("chunks") for s in a_sentences):
        return None
    for i, s in enumerate(a_sentences, 1):
        ch = s["chunks"]
        ok = all(isinstance(c, list) and len(c) == 2 and all(isinstance(x, str) and x.strip() for x in c)
                 and c[0].count("**") % 2 == 0 for c in ch)
        if not ok or " ".join(c[0] for c in ch) != s["en"]:
            return None
    sep = '<span class="s">/</span>'
    return [
        '<div class="chunks-a">' + "".join(
            f'<span class="ck"><span class="e">{marks(e, "b")}{sep if j < len(s["chunks"]) - 1 else ""}</span>'
            f'<span class="k">{esc(k)}</span></span>'
            for j, (e, k) in enumerate(s["chunks"])
        ) + "</div>"
        for s in a_sentences
    ]


def render(lang, day):
    L = langs.get(lang)
    c = load(lang, day)
    d = dt.date.fromisoformat(day)
    n = len(c["sentences"])
    chunks = chunk_rows(lang, day, c["sentences"])
    levels_a = c.get("_levels_a")
    chunks_a = chunk_rows_a(lang, day, levels_a["sentences"]) if levels_a else None
    sentences = "".join(
        f'    <div class="sent"><button class="no" type="button" data-i="{i}" aria-label="{i + 1}번 문장 듣기">{i + 1}</button>'
        f'<div class="say"><div class="en">{marks(s["en"], "b")}{BADGE.format(L["hard_badge"]) if s.get("b2") else ""}</div>'
        f'{chunks[i] if chunks else ""}<div class="ko" hidden>{marks(a, "")}</div>'
        + (
            f'<div class="en-a">{marks(levels_a["sentences"][i]["en"], "b")}</div>'
            f'{chunks_a[i] if chunks_a else ""}'
            f'<div class="ko-a" hidden>{marks(levels_a["answers"][i], "")}</div>'
            if levels_a else ""
        )
        + '</div></div>\n'
        for i, (s, a) in enumerate(zip(c["sentences"], c["answers"]))
    )
    src = c.get("source")
    if src:
        source = f'    <p class="src">출처: <a href="{html.escape(src["url"])}" target="_blank" rel="noopener">{esc(src["title"])}</a></p>\n'
    elif c.get("example"):
        source = f'    <p class="src">{EXAMPLE_NOTE}</p>\n'
    else:
        source = f'    <p class="src">{NO_SOURCE_NOTE}</p>\n'
    words = "".join(
        '    <div class="word">'
        '<span class="wl">'
        + f'<span class="w">{marks(w, "")}</span>'
        + _SPKR_BTN.format(kind="w", i=i, word=html.escape(plain_word_tts(w, lang), quote=True))
        + '</span>'
        + f'<span class="m">{esc(m)}</span></div>\n'
        for i, (w, m) in enumerate(c["words"])
    )
    points = "".join(
        f'    <div class="point">\n      <strong>{esc(p["title"])}</strong>\n      <p>{marks(p["body"], "code")}</p>\n    </div>\n'
        for p in c["points"]
    )
    answers = "".join(
        f'      <div class="sent"><span class="no">{i}</span><div class="ko">{marks(a, "")}</div></div>\n'
        for i, a in enumerate(c["answers"], 1)
    )
    advanced = "".join(
        '      <div class="adv"><div class="w">'
        + f'<span class="wt">{marks(a["word"], "")}</span>'
        + _SPKR_BTN.format(kind="v", i=i, word=html.escape(plain_word_tts(a["word"], lang), quote=True))
        + '</div>'
        + f'<div class="m">{esc(a["meaning"])}'
        + (WARN.format(ruby(esc(a["confuse"]))) if a.get("confuse") else "")
        + '</div>\n'
        + f'        <div class="ex">{marks(a["example"], "b")}</div>'
        + (f'\n        <div class="ex-ko">{esc(a["example_ko"])}</div>' if a.get("example_ko") else "")
        + '</div>\n'
        for i, a in enumerate(c["advanced"])
    )
    out_dir = ROOT / lang / day
    files = [f"audio/s{i}.mp3" for i in range(1, n + 1)]
    audio = json.dumps(files) if all((out_dir / f).exists() for f in files) else "[]"
    # level a 오디오: audio/a{i}.mp3 (없으면 빈 배열, SpeechSynthesis 폴백)
    files_a = [f"audio/a{i}.mp3" for i in range(1, n + 1)]
    audio_a = json.dumps(files_a) if (levels_a and all((out_dir / f).exists() for f in files_a)) else "[]"
    # 단어 발음 오디오: audio/w{i}.mp3 (words), audio/v{i}.mp3 (advanced). 일부만 있으면 빈 배열.
    nw, nv = len(c["words"]), len(c["advanced"])
    files_w = [f"audio/w{i}.mp3" for i in range(1, nw + 1)]
    files_v = [f"audio/v{i}.mp3" for i in range(1, nv + 1)]
    word_audio = json.dumps(files_w) if nw and all((out_dir / f).exists() for f in files_w) else "[]"
    adv_audio = json.dumps(files_v) if nv and all((out_dir / f).exists() for f in files_v) else "[]"
    # 수준 전환 링크: levels.a 가 있을 때만 표시
    if levels_a:
        level_link = (
            '<p class="level-link" id="level-link">'
            '<a href="?level=a" id="to-level-a">기초로 보기</a>'
            '<a href="?level=b" id="to-level-b" hidden>중급으로 보기</a>'
            '</p>\n'
        )
    else:
        level_link = ""
    # 기초 수준 칩: levels.a 가 있을 때만 생성. 문장 수 칩 + 기초 A2~B1 칩 + 예상 읽기 시간 칩.
    # 읽기 시간은 level-a 문장의 단어 수 ÷ 40 wpm(학습 속도)로 올림 계산, 최소 1분.
    if levels_a:
        a_words = sum(len(re.sub(r"\*\*", "", s["en"]).split()) for s in levels_a["sentences"])
        a_min = max(1, math.ceil(a_words / 40))
        a_time_chip = f"약 {a_min}분"
        chips_a_html = (
            '    <div class="chips chips-a">\n'
            f'      <span class="chip blue">{esc(c["chips"][0])}</span>\n'
            '      <span class="chip easy">기초 A2~B1</span>\n'
            f'      <span class="chip">{esc(a_time_chip)}</span>\n'
            '    </div>\n'
        )
    else:
        chips_a_html = ""
    values = {
        "date_short": f"{d.month}월 {d.day}일",
        "date_label": f"{d.month}월 {d.day}일 {DAYS[d.weekday()]}요일",
        "topic": esc(c.get("title_ko") or c["topic"]),
        "headline": f'    <p class="headline" lang="{lang}">{marks(c["headline"], "")}</p>\n' if c.get("headline") else "",
        "chips": "\n".join(f'      <span class="chip{" blue" if i == 0 else ""}">{esc(t)}</span>' for i, t in enumerate(c["chips"])),
        "chips_a": chips_a_html,
        "sentences": sentences,
        "source": source,
        "placeholder": "".join(f"{i}. &#10;" for i in range(1, n)) + f"{n}. ",
        "words": words,
        "points": points,
        "answers": answers,
        "advanced": advanced,
        "audio": audio,
        "audio_a": audio_a,
        "word_audio": word_audio,
        "adv_audio": adv_audio,
        "level_link": level_link,
        "name": L["name"],
        "head_extra": L["head_extra"] + ("\n" if L["head_extra"] else ""),
        "tools_extra": L["tools_extra"],
        "chunk_btn": '\n      <button class="tool" id="chunkbtn" type="button" aria-pressed="false">끊어 읽기</button>' if chunks else "",
        "furi_btn": L.get("furi_btn", ""),
        "tts_lang": L["tts_lang"],
        "copy_head": L["copy_head"],
        "copy_weak": L["copy_weak"],
        "credit": f" {esc(L['credit'])}" if L.get("credit") else "",
    }
    page = TEMPLATE.read_text(encoding="utf-8")
    for k, v in values.items():
        page = page.replace("{{" + k + "}}", v)
    # noindex 플래그가 True 인 언어는 검색엔진 인덱싱을 막는 메타 태그를 삽입한다.
    if L.get("noindex", False):
        page = page.replace(
            "<link rel=\"stylesheet\"",
            '<meta name="robots" content="noindex">\n<link rel="stylesheet"',
            1,
        )
    out = out_dir / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    return out, c["category"], audio != "[]"


if __name__ == "__main__":
    out, _, has_audio = render(sys.argv[1], sys.argv[2])
    print(out, "audio" if has_audio else "no-audio")
