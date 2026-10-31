"""지문 페이지의 단어 암기 반복(이슈 #16). 시안: design/word-drill W01~W06.

publish.patch_page 가 새 페이지와 지난 페이지 모두에 넣는다.
- 지문 끝(주제 반응 카드 앞) '오늘 단어 외우기' 카드: 카드로 외우기(기본) / 문제 풀기(4지선다)
- 몰랐던 단어는 같은 회차 뒤로 다시 나오고 연속 2번 맞혀야 빠진다
- 회차를 마치면 단어를 브라우저(localStorage 'drill:v1')에 담고 1, 3, 7, 14일 간격으로 다시 묻는다. 틀리면 1일부터
- 복습할 단어가 있으면 같은 언어 지문 페이지 맨 위에 복습 띠를 띄운다
서버는 없고 사용량은 GA 이벤트(word_drill_start, word_drill_done, word_review_start)로만 본다.
"""
import datetime as dt
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION = "8"
SPEECH = {"en": "en-US", "ja": "ja-JP", "de": "de-DE"}
DAYS = "월화수목금토일"

RUBY = re.compile(r"\{([^|{}]+)\|([^{}]+)\}")


def base(s):
    """{漢字|かな} 를 漢字 로, ** 를 지운 글자."""
    return RUBY.sub(r"\1", s).replace("**", "")


def reading(s):
    """{漢字|かな} 를 かな 로 바꾼 읽기. 루비가 없으면 빈 글자."""
    return RUBY.sub(r"\2", s).replace("**", "") if RUBY.search(s) else ""


def rich(s):
    """지문 문장을 카드에 넣을 HTML 로: 강조(**)는 <b>, 루비는 <ruby>."""
    out = html.escape(s, quote=False)
    out = RUBY.sub(lambda m: f"<ruby>{m.group(1)}<rt>{m.group(2)}</rt></ruby>", out)
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", out)


def _norm(s):
    return re.sub(r"\s+", " ", base(s)).strip().lower()


def _fold(s):
    """독일어 변이음을 접는다(Hänge ↔ Hang 을 같은 어간으로 찾으려고)."""
    return s.replace("ä", "a").replace("ö", "o").replace("ü", "u").replace("ß", "ss")


def _hint(m, word):
    """단어 쓰기 힌트용 뜻: 괄호 속에 정답 낱말이 든 덧붙임((das Ufer), (teaming up: …))은 지운다.
    그대로 두면 힌트에 답이 보였다(독일어 2026-10-31)."""
    key = _fold(_norm(word).lstrip("〜~").split()[0]) if _norm(word) else ""
    key = key[:max(3, len(key) - 2)] if len(key) > 4 else key
    if not key or not re.match(r"[a-z]", key):
        return m
    out = re.sub(r"\s*\([^()]*\)", lambda g: "" if key in _fold(g.group(0).lower()) else g.group(0), m).strip()
    return out or m


def _match(bold, word):
    b, w = _norm(bold), _norm(word)
    if not b or not w:
        return False
    if b == w or b in w or w in b:
        return True
    if re.match(r"[a-zäöüß]", w):  # 영어, 독일어: 앞 낱말이 같으면(range from A to B ↔ range from)
        return b.split()[0] == w.split()[0] and len(w.split()[0]) > 2
    i = 0  # 일본어: 앞 두 글자 이상이 같으면(集中する ↔ 集中できる)
    while i < min(len(b), len(w)) and b[i] == w[i]:
        i += 1
    return i >= 2


def _short(sent, bold=None):
    """문제 풀기 화면에 쓸 짧은 문장. 길면 그 단어가 든 끊어 읽기 두 덩이만."""
    en = sent["en"]
    if len(base(en)) <= 110 or not sent.get("chunks"):
        return en
    ch = [c[0] for c in sent["chunks"]]
    key = _norm(bold) if bold else None
    j = next((k for k, c in enumerate(ch) if (key and key in _norm(c)) or (not key and "**" in c)), 0)
    j = min(j, len(ch) - 2) if len(ch) > 1 else 0
    part = " ".join(ch[j:j + 2])
    return ("… " if j > 0 else "") + part + (" …" if j + 2 < len(ch) else "")


def _find(word, sents):
    """단어가 나온 문장 번호와 그 문장 속 강조 낱말. 강조로 못 찾으면 본문에서 찾는다."""
    for k, s in enumerate(sents):
        for b in re.findall(r"\*\*(.+?)\*\*", s["en"]):
            if _match(b, word):
                return k, b
    w = _norm(word).lstrip("〜~")
    if re.match(r"[a-zäöüß]", w):
        stem = w.split()[0] if len(w.split()[0]) > 2 else w
    else:  # 일본어: 앞의 한자 덩이(住む → 住), 한자가 없으면 앞 두 글자
        m = re.match(r"[\u4e00-\u9fff]+", w)
        stem = m.group(0) if m else w[:2]
    for k, s in enumerate(sents):
        if stem and stem in _norm(s["en"]):
            return k, None
    for k, s in enumerate(sents):  # 같은 표기가 없을 때만 변이음을 접어 찾는다(Hang 이 문장에는 Hängen 으로)
        if stem and _fold(stem) in _fold(_norm(s["en"])):
            return k, None
    return None, None


BLANK = "\x00"


def _target(raw, word, bold):
    """문장(원문 표기)에서 그 단어가 나온 자리 (시작, 끝). 강조 낱말, 영어/독일어는 같은 어간 낱말, 일본어는 같은 표기."""
    if bold:
        i = raw.find(f"**{bold}**")
        if i >= 0:
            return i, i + len(bold) + 4
    plain = raw.replace("**", "")
    w = base(word).lstrip("〜~")
    if re.match(r"[A-Za-zÄÖÜäöüß]", w):
        first = w.split()[0]
        stem = first[:max(3, len(first) - 2)] if len(first) > 4 else first
        # ** 는 같은 길이의 \x01\x01 로 바꿔 찾아야 위치가 원문과 맞는다
        src = raw.replace("**", "\x01\x01")
        m = re.search(r"(?<![\wÄÖÜäöüß])" + re.escape(stem) + r"[\wÄÖÜäöüß]*", src, re.I)
        if not m:  # 같은 표기가 없으면 어간의 a/o/u 자리에 변이음도 허용한다(Hang ↔ Hängen)
            pat = "".join({"a": "[aä]", "o": "[oö]", "u": "[uü]"}.get(ch.lower(), re.escape(ch)) for ch in stem)
            m = re.search(r"(?<![\wÄÖÜäöüß])" + pat + r"[\wÄÖÜäöüß]*", src, re.I)
        return (m.start(), m.end()) if m else None
    for m in RUBY.finditer(raw):
        if m.group(1) == w:
            return m.start(), m.end()
    i = raw.find(w)
    if i >= 0 and "{" not in raw[i:i + len(w)]:
        return i, i + len(w)
    # 활용한 동사, 형용사(含む → 含まれています): 앞 한자 덩이 뒤에 붙은 히라가나까지
    k = re.match(r"[\u4e00-\u9fff]+", w)
    if k and len(w) > len(k.group(0)):
        m = re.search(r"(?:\{" + re.escape(k.group(0)) + r"\|[^{}]+\}|" + re.escape(k.group(0)) + r")[\u3041-\u3096ー]+", raw)
        if m:  # 뒤에 붙은 이음말(ため, ように, ので…)과 조사는 뺀다
            tail = re.search(r"(?:ため|ように|ような|ので|から|けれど|けど|のに|こと|もの|とき|ながら)?[がをにはとへもや]?$", m.group(0))
            return m.start(), m.end() - len(tail.group(0))
    return None


def _fits(ans, word):
    """빈칸 정답이 그 단어의 형태인지: 같은 앞부분(한자 덩이, 영어/독일어는 앞 세 글자)으로 시작해야 한다(葉 ↔ 紅葉 은 아님)."""
    a, w = ans.lower(), base(word).lstrip("〜~").lower()
    if re.match(r"[a-zäöüß]", w):  # 영어, 독일어: 첫 낱말에 굴절 어미만 붙은 꼴(Bäcker ↔ Bäckerei 는 아님)
        fa, fw = a.split()[0] if a.split() else "", w.split()[0]
        ends = ("", "s", "es", "n", "en", "e", "er", "ern", "ed", "d", "ing", "ies", "ied")
        roots = {fw} | ({fw[:-1]} if fw[-1:] in "ey" and len(fw) > 3 else set())
        return any(fa.startswith(r) and fa[len(r):] in ends for r in roots)
    k = re.match(r"[\u4e00-\u9fff]+", w)
    return bool(a) and a.startswith(k.group(0) if k else w[:2])


def _shown(cz, ans):
    """빈칸 밖에 정답이 또 보이면 참(같은 단어가 문장에 두 번 나온 경우). 루비 읽기는 빼고 본다."""
    text = re.sub(r"<[^>]+>", "", re.sub(r"<rt>.*?</rt>", "", cz))
    return html.unescape(ans).lower() in html.unescape(text).lower()


def _marked(raw, span):
    """그 단어만 ** 로 강조한 문장 원문. 다른 강조는 지운다."""
    a, b = span
    seg = raw[a:b].replace("**", "")
    return raw[:a].replace("**", "") + f"**{seg}**" + raw[b:].replace("**", "")


def _cloze(raw, span):
    """그 단어 자리를 빈칸으로 바꾼 문장 HTML 과 정답 표기."""
    a, b = span
    seg = raw[a:b].replace("**", "")
    body = rich(raw[:a].replace("**", "") + BLANK + raw[b:].replace("**", ""))
    return body.replace(BLANK, '<span class="dr-blank"></span>'), base(seg)


def cards(lang, day):
    """content/<lang>/<day>.json 의 주요 단어(words)를 카드 자료로. 자료가 없으면 []."""
    p = ROOT / "content" / lang / f"{day}.json"
    if not p.exists():
        return []
    d = json.loads(p.read_text(encoding="utf-8"))
    words, sents, answers = d.get("words") or [], d.get("sentences") or [], d.get("answers") or []
    out = []
    for i, (w, m) in enumerate(words):
        c = {"w": base(w), "m": m}
        mh = _hint(m, w)
        if mh != m:
            c["mh"] = mh
        r = reading(w)
        if r and r != c["w"]:
            c["r"] = r
        k, b = _find(w, sents)
        if k is not None:
            raw = sents[k]["en"]
            span = _target(raw, w, b)
            if span:  # 카드와 문제에 그 단어만 강조하고, 빈칸 채우기 자료를 만든다
                cz, ca = _cloze(raw, span)
                if _fits(ca, w) and not _shown(cz, ca):
                    c["cz"], c["ca"] = cz, ca
                raw = _marked(raw, span)
                b = base(raw[raw.index("**") + 2:raw.index("**", raw.index("**") + 2)])
            c["ex"] = rich(raw)
            c["sh"] = rich(_short(dict(sents[k], en=raw), b))
            if k < len(answers):
                c["ek"] = answers[k]
        if (ROOT / lang / day / "audio" / f"w{i + 1}.mp3").exists():
            c["au"] = f"/{lang}/{day}/audio/w{i + 1}.mp3"
        out.append(c)
    for c in out:
        c["alts"] = [o["m"] for o in out if o is not c]
    return out


CSS = """  .dr-card .desc { font-size: 14px; color: var(--sub); line-height: 1.6; margin: -8px 0 16px; }
  .dr-chips { display: flex; flex-wrap: wrap; gap: 6px; margin: 0 0 16px; }
  .dr-chip { font-size: 13px; font-weight: 600; padding: 5px 11px; border-radius: 999px; background: var(--bg); color: var(--sub); }
  .dr-modes { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 0 0 12px; }
  .dr-mode { font: inherit; color: var(--ink); border: 1.5px solid #e2e6ea; background: #f4f6f8; border-radius: 12px; padding: 12px 14px; text-align: left; cursor: pointer; }
  .dr-mode[aria-pressed=true] { border-color: #2a52d4; background: #eff3fd; }
  .dr-mode b { display: block; font-size: 15px; font-weight: 700; }
  .dr-mode span { display: block; font-size: 12.5px; color: var(--sub); margin-top: 2px; line-height: 1.45; }
  .dr-mode[aria-pressed=true] b { color: #2a52d4; }
  .dr-btn { font: inherit; border: 0; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 6px; height: 52px; width: 100%; border-radius: 12px; background: #2a52d4; color: #fff; font-size: 16px; font-weight: 700; }
  .dr-btn:active { background: #2143ad; }
  .dr-btn.ghost { background: #eff3fd; color: #2a52d4; }
  .dr-foot { font-size: 12.5px; color: var(--muted); margin: 10px 0 0; line-height: 1.5; }
  .dr-due { display: flex; align-items: center; gap: 14px; margin: 12px 12px 0; padding: 16px 16px 16px 18px; border-radius: 18px; background: #2a52d4; color: #fff; box-shadow: var(--card-sh); }
  .dr-due[hidden] { display: none; }
  .dr-due .ic { flex: none; width: 44px; height: 44px; border-radius: 12px; background: rgba(255,255,255,.16); display: grid; place-items: center; font-size: 18px; font-weight: 800; }
  .dr-due .tx { flex: 1; min-width: 0; }
  .dr-due b { display: block; font-size: 16px; font-weight: 700; }
  .dr-due span { display: block; font-size: 13px; opacity: .85; }
  .dr-due .go { font: inherit; border: 0; cursor: pointer; flex: none; height: 38px; padding: 0 14px; border-radius: 10px; background: #fff; color: #2a52d4; font-size: 14px; font-weight: 700; }
  body.dr-open { overflow: hidden; }
  .dr { position: fixed; inset: 0; z-index: 100; background: var(--bg); overflow-y: auto; overscroll-behavior: contain; -webkit-overflow-scrolling: touch; }
  .dr[hidden] { display: none; }
  .dr-in { max-width: 560px; min-height: 100%; margin: 0 auto; display: flex; flex-direction: column; padding: 0 0 calc(20px + env(safe-area-inset-bottom)); }
  .dr-bar { display: flex; align-items: center; gap: 10px; height: 56px; margin: 12px 12px 0; padding: 0 16px 0 10px; border-radius: 16px; background: #fff; box-shadow: var(--bar-sh); }
  .dr-x { font: inherit; border: 0; background: none; cursor: pointer; width: 36px; height: 36px; border-radius: 10px; display: grid; place-items: center; color: var(--sub); }
  .dr-x svg { width: 18px; height: 18px; }
  .dr-bar .t { font-size: 15px; font-weight: 700; flex: 1; }
  .dr-bar .n { font-size: 14px; font-weight: 700; color: #2a52d4; }
  .dr-prog { margin: 14px 24px 0; }
  .dr-track { height: 6px; border-radius: 999px; background: #e3e7ec; overflow: hidden; display: flex; }
  .dr-track i { display: block; height: 100%; transition: width .25s; }
  .dr-track .ok { background: #2a52d4; }
  .dr-track .re { background: #f5a3aa; }
  .dr-legend { display: flex; justify-content: space-between; margin-top: 8px; font-size: 12.5px; font-weight: 600; color: var(--sub); }
  .dr-legend span { display: inline-flex; align-items: center; gap: 5px; }
  .dr-legend i { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
  .dr-legend i.ok { background: #2a52d4; }
  .dr-legend i.re { background: #f5a3aa; }
  .dr-fc { flex: 1; margin: 14px 12px 0; background: #fff; border-radius: 24px; box-shadow: var(--card-sh); padding: 22px 22px 24px; display: flex; flex-direction: column; }
  .dr-fc.fit { flex: none; }
  .dr-tag { align-self: flex-start; font-size: 12px; font-weight: 700; padding: 3px 10px; border-radius: 999px; background: var(--bg); color: var(--sub); }
  .dr-tag.re { background: #ffeeee; color: #f04452; }
  .dr-mid { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; gap: 14px; padding: 24px 0; }
  .dr-word { font-size: 38px; font-weight: 800; letter-spacing: -0.03em; line-height: 1.2; word-break: break-word; }
  .dr-word.sm { font-size: 30px; }
  .dr-pron { font-size: 15px; color: var(--muted); margin-top: -6px; }
  .dr-listen { font: inherit; border: 0; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; height: 40px; padding: 0 16px; border-radius: 999px; background: #eff3fd; color: #2a52d4; font-size: 14px; font-weight: 700; }
  .dr-listen svg { width: 16px; height: 16px; }
  .dr-hint { font-size: 13px; color: var(--muted); text-align: center; margin: 4px 0 0; }
  .dr-mean { font-size: 22px; font-weight: 700; color: #2a52d4; letter-spacing: -0.02em; line-height: 1.4; }
  .dr-ex { width: 100%; text-align: left; background: var(--bg); border-radius: 14px; padding: 14px 16px; }
  .dr-ex .lb { font-size: 12px; font-weight: 700; color: var(--muted); margin-bottom: 4px; }
  .dr-ex .en { font-size: 15px; line-height: 1.6; margin: 0; }
  .dr-ex .en b, .dr-qsub b { background: #fff3c4; font-weight: 700; padding: 0 2px; border-radius: 3px; }
  .dr-ex .ko { font-size: 13.5px; color: var(--sub); margin: 6px 0 0; line-height: 1.55; }
  .dr-ex .ko.flat { margin: 0; }
  .dr-acts { margin: 14px 12px 0; }
  .dr-judge { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
  .dr-judge button { font: inherit; border: 0; cursor: pointer; height: 56px; border-radius: 14px; font-size: 16px; font-weight: 700; line-height: 1.3; }
  .dr-judge .dr-no { background: #ffeeee; color: #f04452; }
  .dr-judge .dr-yes { background: #2a52d4; color: #fff; }
  .dr-judge small { display: block; font-size: 11.5px; font-weight: 600; opacity: .8; }
  .dr-judge.sm button { height: 48px; font-size: 15px; }
  .dr-fc.tap { cursor: pointer; -webkit-tap-highlight-color: transparent; }
  .dr-fc.tap:focus-visible, .dr-fc.swipe:focus-visible { outline: 3px solid #2a52d4; outline-offset: 2px; }
  .dr-listen.on { background: #2a52d4; color: #fff; }
  .dr-taphint { display: flex; align-items: center; justify-content: center; gap: 6px; font-size: 14px; font-weight: 600; color: #2a52d4; margin: 4px 0 0; }
  .dr-taphint svg { width: 18px; height: 18px; }
  .dr-stage { flex: 1; position: relative; display: flex; flex-direction: column; }
  .dr-fc.swipe { position: relative; z-index: 1; touch-action: pan-y; user-select: none; -webkit-user-select: none; -webkit-touch-callout: none; }
  .dr-fc.swipe.back { transition: transform .2s ease; }
  .dr-fc.under { position: absolute; inset: 8px 20px 0; margin: 14px 0 0; opacity: .6; transform: scale(.96); pointer-events: none; }
  .dr-fc.fly { position: absolute; top: 0; left: 0; right: 0; bottom: 0; z-index: 2; pointer-events: none; transition: transform .25s ease-in, opacity .25s ease-in; }
  /* 지문 페이지에 .no 규칙(문장 번호)이 있어 도장은 sy/sn 으로 쓴다 */
  .dr-stamp { position: absolute; top: 26px; width: max-content; white-space: nowrap; padding: 4px 12px; border: 3px solid; border-radius: 10px; background: #fff; font-size: 22px; font-weight: 800; opacity: 0; pointer-events: none; }
  .dr-stamp.sy { left: 22px; color: #2a52d4; transform: rotate(-12deg); }
  .dr-stamp.sn { right: 22px; color: #f04452; transform: rotate(12deg); }
  .dr-swipehint { display: flex; justify-content: space-between; align-items: center; margin: 14px 16px 0; font-size: 13px; font-weight: 700; }
  .dr-swipehint .l { color: #f04452; }
  .dr-swipehint .r { color: #2a52d4; }
  .dr-swipehint .c { font-size: 12px; font-weight: 600; color: var(--muted); }
  @media (prefers-reduced-motion: reduce) { .dr-fc.swipe.back, .dr-fc.fly { transition: none; } }
  .dr-q { font-size: 13px; font-weight: 700; color: #2a52d4; }
  .dr-qword { font-size: 32px; font-weight: 800; letter-spacing: -0.03em; margin: 6px 0 4px; line-height: 1.25; }
  .dr-qsub { font-size: 14px; color: var(--sub); margin: 0 0 18px; line-height: 1.6; }
  .dr-opts { display: flex; flex-direction: column; gap: 8px; }
  .dr-opt { font: inherit; color: var(--ink); cursor: pointer; display: flex; align-items: center; gap: 12px; text-align: left; border: 1.5px solid #e2e6ea; background: #f4f6f8; border-radius: 12px; padding: 13px 14px; font-size: 15px; font-weight: 600; }
  .dr-opt:disabled { cursor: default; }
  .dr-opt .k { flex: none; width: 24px; height: 24px; border-radius: 50%; border: 1.5px solid #c5ccd6; display: grid; place-items: center; font-size: 12px; font-weight: 700; color: var(--sub); background: #fff; }
  .dr-opt.wrong { border-color: #f04452; background: #ffeeee; color: #f04452; }
  .dr-opt.wrong .k { background: #f04452; border-color: #f04452; color: #fff; }
  .dr-opt.right { border-color: #0f9d6b; background: #e8f7f1; color: #0f9d6b; }
  .dr-opt.right .k { background: #0f9d6b; border-color: #0f9d6b; color: #fff; }
  .dr-opt .r { margin-left: auto; flex: none; font-size: 12px; font-weight: 700; }
  .dr-verdict { margin: 16px 0 10px; font-size: 15px; font-weight: 700; color: #f04452; }
  .dr-verdict.ok { color: #0f9d6b; }
  .dr-qts-lb { font-size: 13px; font-weight: 700; color: var(--sub); margin: 2px 0 8px; }
  .dr-qtypes { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; margin: 0 0 14px; }
  .dr-qt { font: inherit; cursor: pointer; border: 1.5px solid #e2e6ea; background: #fff; border-radius: 10px; padding: 9px 4px; text-align: center; font-size: 14px; font-weight: 700; color: var(--sub); }
  .dr-qt small { display: block; font-size: 11.5px; font-weight: 600; color: var(--muted); margin-top: 1px; }
  .dr-qt[aria-pressed=true] { border-color: #2a52d4; background: #eff3fd; color: #2a52d4; }
  .dr-qt[aria-pressed=true] small { color: #2a52d4; opacity: .8; }
  .dr-qmean { font-size: 26px; font-weight: 800; letter-spacing: -0.02em; color: #2a52d4; margin: 8px 0 6px; line-height: 1.35; }
  .dr-qhint { font-size: 13px; color: var(--muted); margin: 0 0 16px; }
  .dr-field { font: inherit; width: 100%; height: 56px; border-radius: 12px; border: 1.5px solid #e2e6ea; background: #fff; padding: 0 16px; font-size: 18px; font-weight: 600; color: var(--ink); }
  .dr-field:focus { outline: none; border-color: #2a52d4; }
  .dr-field::placeholder { color: var(--muted); font-weight: 500; font-size: 16px; }
  .dr-field.wrong { border-color: #f04452; background: #ffeeee; color: #f04452; text-decoration: line-through; opacity: 1; -webkit-text-fill-color: #f04452; }
  .dr-field.right { border-color: #0f9d6b; background: #e8f7f1; color: #0f9d6b; opacity: 1; -webkit-text-fill-color: #0f9d6b; }
  .dr-skip { font: inherit; display: block; width: 100%; border: 0; background: none; cursor: pointer; font-size: 14px; font-weight: 600; color: var(--sub); margin-top: 8px; padding: 8px 0; }
  .dr-answer { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 12px 14px; border-radius: 12px; background: var(--bg); }
  .dr-answer .lb { display: block; font-size: 12px; font-weight: 700; color: var(--muted); }
  .dr-answer b { font-size: 20px; font-weight: 800; }
  .dr-answer .rd { margin-left: 8px; font-size: 14px; color: var(--sub); }
  .dr-gap10 { margin-top: 10px; }
  .dr-cloze { font-size: 17px; line-height: 1.8; font-weight: 600; margin: 10px 0 8px; }
  .dr-blank { display: inline-block; min-width: 88px; border-bottom: 2.5px solid #2a52d4; margin: 0 3px; text-align: center; color: #2a52d4; line-height: 1.4; }
  .dr-blank:empty::before { content: "\00a0"; }
  .dr-blank.right { border-color: #0f9d6b; color: #0f9d6b; background: #e8f7f1; border-radius: 4px 4px 0 0; padding: 0 4px; }
  .dr-cko { font-size: 13.5px; color: var(--sub); line-height: 1.55; margin: 0 0 16px; }
  .dr .card { margin: 12px 12px 0; }
  .dr-score { display: flex; align-items: baseline; gap: 6px; margin: 4px 0; }
  .dr-score b { font-size: 44px; font-weight: 800; letter-spacing: -0.03em; color: #2a52d4; line-height: 1.1; }
  .dr-score span { font-size: 18px; font-weight: 700; color: var(--sub); }
  .dr-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin: 16px 0 0; }
  .dr-stat { background: var(--bg); border-radius: 12px; padding: 12px; }
  .dr-stat b { display: block; font-size: 18px; font-weight: 800; }
  .dr-stat span { font-size: 12px; color: var(--sub); font-weight: 600; }
  .dr-in h2.dr-h12 { margin-bottom: 12px; }
  .dr-in h2.dr-h6 { margin-bottom: 6px; }
  .dr-in p.dr-next { margin: 0 0 14px; font-size: 14px; color: var(--sub); line-height: 1.6; }
  .dr-wl { display: flex; justify-content: space-between; align-items: center; gap: 12px; padding: 12px 0; border-top: 1px solid #eef0f3; }
  .dr-wl:first-child { border-top: 0; padding-top: 0; }
  .dr-wl b { font-size: 16px; font-weight: 700; }
  .dr-wl em { font-style: normal; font-size: 12px; font-weight: 700; color: #f04452; background: #ffeeee; padding: 2px 8px; border-radius: 999px; margin-left: 6px; white-space: nowrap; }
  .dr-wl span { font-size: 14px; color: var(--sub); text-align: right; }
  .dr-none { font-size: 14px; color: var(--sub); margin: 0; }
  .dr-sched { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; }
  .dr-dot { text-align: center; padding: 10px 4px; border-radius: 12px; background: var(--bg); }
  .dr-dot b { display: block; font-size: 14px; font-weight: 800; }
  .dr-dot span { font-size: 11.5px; color: var(--sub); font-weight: 600; }
  .dr-dot.next { background: #2a52d4; color: #fff; }
  .dr-dot.next span { color: rgba(255,255,255,.85); }
  .dr-gap { margin-top: 16px; }
"""

DUE_HTML = (
    "<!-- drill-due -->\n"
    '  <div class="dr-due" id="dr-due" hidden><span class="ic" id="dr-due-n"></span>'
    '<div class="tx"><b id="dr-due-t"></b><span id="dr-due-s"></span></div>'
    '<button class="go" type="button" id="dr-due-go">복습하기</button></div>\n'
    "<!-- /drill-due -->\n"
)


def card_html(lang, day, items, step):
    n = len(items)
    chips = "".join(f'<span class="dr-chip" lang="{lang}">{html.escape(c["w"])}</span>' for c in items)
    mins = max(1, round(n * 25 / 60))
    return (
        "<!-- drill-card -->\n"
        f'  <section class="card dr-card" id="drill" data-v="{VERSION}">\n'
        f'    <div class="step">STEP {step}</div>\n'
        "    <h2>오늘 단어 외우기</h2>\n"
        f'    <p class="desc">지문에 나온 단어 {n}개를 외울 때까지 반복해요. 몰랐던 단어는 다시 나와요.</p>\n'
        f'    <div class="dr-chips">{chips}</div>\n'
        '    <div class="dr-modes">\n'
        '      <button class="dr-mode" type="button" data-mode="card" aria-pressed="true"><b>카드로 외우기</b><span>단어를 보고 뜻을 떠올려요</span></button>\n'
        '      <button class="dr-mode" type="button" data-mode="quiz" aria-pressed="false"><b>문제 풀기</b><span>문제 종류를 골라요</span></button>\n'
        "    </div>\n"
        '    <div class="dr-qts" id="dr-qts" hidden><div class="dr-qts-lb">문제 종류</div><div class="dr-qtypes">'
        '<button class="dr-qt" type="button" data-qt="quiz" aria-pressed="true">뜻 고르기<small>4개 중 하나</small></button>'
        '<button class="dr-qt" type="button" data-qt="write" aria-pressed="false">단어 쓰기<small>뜻 보고 입력</small></button>'
        '<button class="dr-qt" type="button" data-qt="cloze" aria-pressed="false">빈칸 채우기<small>예문에 맞게</small></button></div></div>\n'
        f'    <button class="dr-btn" type="button" id="dr-start">{n}개 외우기 시작</button>\n'
        f'    <p class="dr-foot">약 {mins}분 걸려요. 고른 방식과 기록은 이 기기에만 남아요.</p>\n'
        "  </section>\n"
        "<!-- /drill-card -->\n"
    )


SCRIPT = '<script id="drill-js" data-v="__V__" src="/assets/drill.js?v=__V__" defer></script>\n'


def _next_step(page):
    nums = [int(n) for n in re.findall(r'<div class="step"[^>]*>STEP (\d+)</div>', page)]
    return max(nums) + 1 if nums else 1


def apply(page, lang, day):
    """페이지에 복습 띠, 진입 카드, CSS, 자료, 스크립트를 넣는다. 같은 버전이 있으면 그대로 둔다(여러 번 돌려도 같다)."""
    if f'<script id="drill-js" data-v="{VERSION}"' in page:
        return page
    # 날짜 지문 페이지에만 넣는다(아카이브, 복습 페이지 등은 그대로).
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day or "") or "</header>\n" not in page or "  .gnb {" not in page:
        return page
    for a, b in (("<!-- drill-due -->", "<!-- /drill-due -->"), ("<!-- drill-card -->", "<!-- /drill-card -->")):
        page = re.sub(re.escape(a) + r".*?" + re.escape(b) + r"\n\n?", "", page, count=1, flags=re.S)
    page = re.sub(r'<script type="application/json" id="drill-data">.*?</script>\n', "", page, count=1, flags=re.S)
    page = re.sub(r'<script id="drill-js"[^>]*>.*?</script>\n', "", page, count=1, flags=re.S)
    # CSS 는 원래 자리에서 바꿔 끼운다(다른 패치가 뒤에 넣은 CSS 와 순서가 바뀌지 않게). 없으면 .gnb 앞에 넣는다
    css_at = re.search(r"  /\* drill-css \*/\n.*?  /\* /drill-css \*/\n", page, flags=re.S)
    if css_at:
        page = page[:css_at.start()] + "  /* drill-css */\n" + CSS + "  /* /drill-css */\n" + page[css_at.end():]

    items = cards(lang, day)
    if not css_at:
        page = page.replace("  .gnb {", "  /* drill-css */\n" + CSS + "  /* /drill-css */\n  .gnb {", 1)
    page = page.replace("</header>\n", "</header>\n" + DUE_HTML, 1)
    if items:
        card = card_html(lang, day, items, _next_step(page))
        for anchor in ('  <section class="card vote"', '  <details class="card">', '  <section class="card sub"', "</main>"):
            if anchor in page:
                page = page.replace(anchor, card + "\n" + anchor, 1)
                break
    data = json.dumps(items, ensure_ascii=False).replace("</", "<\\/")
    tail = f'<script type="application/json" id="drill-data">{data}</script>\n' + SCRIPT.replace("__V__", VERSION)
    return page.replace("</body>", tail + "</body>", 1)
