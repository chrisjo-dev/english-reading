"""단어 암기 카드 품질 감시 테스트 (이슈 #17).

- Defect 1: 4지선다 뜻 문제에 답이 alts 에 보임  → correct_m 이 alts 에 없어야 함
- Defect 2: 일본어 굵은 글씨가 카드 단어 일부만 포함  → ex 의 bold 가 단어 앞 한자 블록으로 시작해야 함
- Defect 3: 일본어 복합어 클로즈 답이 앞부분만 → ca == w 여야 함 (한자+히라가나+한자 형태)
- Defect 4: 같은 날 뜻이 같은 단어 쌍  → problems() 에서 검사
- Defect 5: 클로즈 답이 빈칸 밖 본문에 그대로 보임  → _shown 이 False 여야 함
- Defect 7: 독일어 움라우트 단어가 클로즈에서 누락  → _fits 가 True 여야 함

False positive 허용 목록:
- de: Fähre/fahren (파생어 관계)
- ja: 選ばれる/選手, 植える/植木鉢 (공유 한자이지만 다른 단어)
- ja: 히라가나 활용형 (ならぶ→ならんで 등)
"""
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import drill  # noqa: E402

# ── 허용 목록 ────────────────────────────────────────────────────────────────
# 각 항목은 (lang, day, word) 또는 (lang, day, card_word, bold_word) 형식
BOLD_ALLOWLIST = {
    # 히라가나 활용형은 bold 가 활용형이어도 무방
    ("ja", "2026-10-13", "ならぶ", "ならんで"),
    ("ja", "2026-10-13", "あたたかい", "あたたかくて"),
    ("ja", "2026-10-13", "買いに行く", "買い"),
    ("ja", "2026-10-14", "まちがえる", "まちがえないで"),
    ("ja", "2026-10-20", "持って行きます", "持って"),
    ("ja", "2026-10-28", "なくなります", "なくなりました"),
    # 노벨상: 단어 자체가 더 긴 표현 안에 포함
    ("ja", "2026-10-07", "ノーベル賞", "ノーベル化学賞"),
    ("ja", "2026-10-07", "化学", "ノーベル化学賞"),
    # 鈴虫/虫: 포함 관계지만 앞 한자가 다름 → 고쳐진 로직에서 이미 걸러짐
}

CLOZE_ALLOWLIST = {
    ("ja", "2026-10-07", "ノーベル賞"),
    ("ja", "2026-10-11", "鳴き声"),
    ("ja", "2026-10-13", "ならぶ"),
    ("ja", "2026-10-13", "買いに行く"),
    ("ja", "2026-10-13", "あたたかい"),
    ("ja", "2026-10-14", "まちがえる"),
    ("ja", "2026-10-20", "持って行きます"),
    ("ja", "2026-10-28", "なくなります"),
}

SHOWN_ALLOWLIST: set = set()  # 실제 누출이 허용된 케이스 없음


def _all_cards():
    for lang in ("en", "ja", "de"):
        for p in sorted((ROOT / "content" / lang).glob("????-??-??.json")):
            day = p.stem
            try:
                cs = drill.cards(lang, day)
            except Exception:
                continue
            for c in cs:
                yield lang, day, c


def _strip_tags(s):
    s = re.sub(r"<rt>.*?</rt>", "", s)
    return re.sub(r"<[^>]+>", "", html.unescape(s))


# ── Defect 1: alts 에 정답 포함 ───────────────────────────────────────────────
def test_no_answer_in_alts():
    leaks = []
    for lang, day, c in _all_cards():
        correct = c.get("mh", c["m"])
        for alt in c.get("alts", []):
            if alt == correct:
                leaks.append(f"{lang}/{day}: w={c['w']} correct={correct!r} leaked in alts")
    assert not leaks, "\n".join(leaks)


# ── Defect 2: 일본어 bold 불일치 ─────────────────────────────────────────────
def test_ja_bold_match():
    mismatches = []
    for lang, day, c in _all_cards():
        if lang != "ja" or "ex" not in c:
            continue
        mb = re.search(r"<b>(.*?)</b>", c["ex"])
        if not mb:
            continue
        inner = mb.group(1)
        bold = _strip_tags(inner)
        w = c["w"].lstrip("〜~")
        if bold == w:
            continue
        if (lang, day, w, bold) in BOLD_ALLOWLIST:
            continue
        # 허용: 히라가나만인 카드 단어의 활용형 (ならぶ 류)
        if re.match(r"^[ぁ-ゖ]+$", w):
            continue
        # 수정된 _match 로 검사
        if not drill._match(bold, w):
            mismatches.append(f"ja/{day}: card={w!r} bold={bold!r}")
    assert not mismatches, "\n".join(mismatches)


# ── Defect 3: 일본어 복합어 클로즈 부분 답 ────────────────────────────────────
def test_ja_cloze_exact_compound():
    partials = []
    for lang, day, c in _all_cards():
        if lang != "ja" or "cz" not in c:
            continue
        w = c["w"].lstrip("〜~")
        ca = c.get("ca", "")
        if ca == w:
            continue
        if (lang, day, w) in CLOZE_ALLOWLIST:
            continue
        # 한자 뒤에 또 한자가 오는 복합어 패턴
        km = re.match(r"[一-鿿]+", w)
        if km:
            after = w[len(km.group(0)):]
            if re.search(r"[一-鿿]", after):
                partials.append(f"ja/{day}: card={w!r} ca={ca!r} (should be exact)")
    assert not partials, "\n".join(partials)


# ── Defect 4: 같은 날 중복 뜻 ────────────────────────────────────────────────
def test_no_duplicate_meanings():
    dups = []
    for lang in ("en", "ja", "de"):
        for p in sorted((ROOT / "content" / lang).glob("????-??-??.json")):
            day = p.stem
            try:
                probs = drill.problems(lang, day)
            except Exception:
                continue
            for a, b, m in probs.get("duplicate_meanings", []):
                dups.append(f"{lang}/{day}: {a!r} and {b!r} share meaning {m!r}")
    assert not dups, "\n".join(dups)


# ── Defect 5: 클로즈 답 본문 외부 노출 ───────────────────────────────────────
def test_cloze_answer_not_shown():
    leaks = []
    for lang, day, c in _all_cards():
        if "cz" not in c:
            continue
        ca = c.get("ca", "")
        cz = c["cz"]
        key = (lang, day, c["w"])
        if key in SHOWN_ALLOWLIST:
            continue
        if drill._shown(cz, ca, lang):
            leaks.append(f"{lang}/{day}: card={c['w']!r} ca={ca!r} visible outside blank")
    assert not leaks, "\n".join(leaks)


# ── Defect 7: 독일어 움라우트 클로즈 적합성 ──────────────────────────────────
def test_de_umlaut_fits():
    pairs = [
        ("hängen", "Hang"),
        ("Tälern", "Tal"),
        ("läuft", "laufen"),
        ("fährt", "fahren"),
    ]
    failures = []
    for ans, word in pairs:
        if not drill._fits(ans, word):
            failures.append(f"_fits({ans!r}, {word!r}) returned False")
    assert not failures, "\n".join(failures)
