"""지문 JSON 을 올리기 전에 독자에게 보일 실수를 잡는다.

사용: python3 tools/check_content.py en 2026-10-14      (한 편)
      python3 tools/check_content.py --all              (전체)
- 오류(종료 코드 1): 지원하지 않는 마크다운 기호가 남아 화면에 그대로 보이는 경우. 예: *The List*, _word_, [링크](url)
- 경고: 출처(source)가 없는데 인원, 금액, 수량 같은 구체적 수치가 있는 경우. 실제 사실처럼 읽히므로 출처를 달거나 수치를 빼야 한다.
  널리 알려진 일반 상식(계절, 대략적인 통계)이면 그대로 둬도 되고, 지어낸 사례면 "example": true 를 넣는다.
- 오류: 같은 언어의 최근 14일 지문과 내용이 겹치는 경우. 주제가 같은 것은 괜찮고, 같은 기사(출처 주소)이거나
  형광펜 단어가 2개 이상 같거나, 본문이 많이 겹치면(영어/독일어: 핵심 단어 12% 이상, 일본어: 세 글자 묶음 15% 이상)
  같은 이야기를 반복하는 것으로 본다.
      python3 tools/check_content.py --overlap en 2026-10-14   (내용 겹침만 검사, 발행 워크플로가 쓴다)
- 오류: chunks 활성화 언어(langs 의 chunks 플래그)의 문장 끊어 읽기를 공백 하나로 이은 글이 문장과 다르거나,
  영어/독일어나 뜻이 빈 덩어리가 있는 경우.
  2026-10-23 이후 영어 지문과 영어 비축분은 모든 문장에 chunks 가 있어야 한다.
  독일어는 DE_CHUNKS_FROM 이후 지문과 독일어 비축분에 chunks 가 있어야 한다.
- 오류: 수준을 나눈 언어(langs 의 levels 플래그)의 기초 지문 levels.a 가 없거나 본문과 문장 수가 다른 경우.
  영어는 LEVELS_FROM, 독일어는 DE_LEVELS_FROM, 일본어는 JA_LEVELS_FROM 이후 지문과 그 언어의 비축분에 필수.
- 경고: 독일어와 일본어 본문(중급)이 수준에 비해 지나치게 짧은 경우.
- 경고(PLAN_FROM 이후 지문, ROUTINE.common.md): fit 이 요일과 다름, 소식과 설명 날 출처 없음, grammar 의 id 가 목록에 없거나
  pattern 이 문장별로 안 걸림, 영어 중급 길이 규칙 위반, 최근 90일 지문과 소재 반복. 비축분에는 적용하지 않는다.
      python3 tools/check_content.py --topics en 2026-11-09   (최근 90일 소재 목록, 지문을 쓰기 전에 본다)
      python3 tools/check_content.py --repeat en 2026-11-05   (소재 반복만 검사, PLAN_FROM 과 무관)
- 오류: 주요 단어(words)의 뜻 괄호에 그 단어나 변형이 들어 있는 경우. 예: ["Ufer", "물가 (das Ufer)"], ["genes", "유전자들 (gene의 복수)"].
  단어 쓰기 문제의 힌트에 답이 보인다. WORD_HINT_FROM 이후 지문과 모든 비축분에 적용.
"""
import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import grammar_pick as _grammar  # noqa: E402
import langs as _langs  # noqa: E402

# 화면에서 처리하는 표기: **굵게**, `코드`, {漢字|かな}. 이것을 지운 뒤 남은 기호를 찾는다.
SUPPORTED = re.compile(r"\*\*[^*]+\*\*|`[^`]+`|\{[^{}|]+\|[^{}]+\}")
LEFTOVER = re.compile(r"\*|(?<![\w])_[^_]+_(?![\w])|\[[^\]]+\]\([^)]+\)|^#+\s")
NUMBER = re.compile(r"\d{2,}|\b(?:hundred|thousand|million|billion|percent)\b|[百千万億]|パーセント|%", re.I)


def texts(c, where="", skip=("date", "category", "chips", "source", "photo_scene")):
    """지문, 단어, 체크 포인트, 해석 등 화면에 보이는 모든 글을 꺼낸다."""
    if isinstance(c, str):
        yield where, c
    elif isinstance(c, list):
        for x in c:
            yield from texts(x, where)
    elif isinstance(c, dict):
        for k, v in c.items():
            if k not in skip:
                yield from texts(v, where or k)


def check_de_quality(c, path):
    """독일어 지문 품질 검사 (문장 길이 경고, advanced 개수 오류)."""
    errors, warnings = [], []
    sents = c.get("sentences", [])
    if sents:
        avg_wc = sum(len(s.get("en", "").split()) for s in sents) / len(sents)
        if avg_wc < 14:
            warnings.append(
                f"de 문장 평균 단어 수({avg_wc:.1f})가 14 미만입니다. "
                "B1~B2 수준은 15~22단어를 권장합니다."
            )
    adv = c.get("advanced", [])
    is_pool = path.parent.parent.name == "pool"
    try:
        is_recent = dt.date.fromisoformat(path.stem) >= dt.date(2026, 10, 29)
    except ValueError:
        is_recent = False
    if (is_pool or is_recent) and len(adv) < 5:
        errors.append(
            f"advanced 항목이 {len(adv)}개입니다. "
            "독일어 지문은 6~8개가 필요합니다(pool 과 2026-10-29 이후 지문에 적용)."
        )
    return errors, warnings


JA_MIN_AVG_CHARS = 28  # 일본어 중급(N3) 본문 문장 평균 글자 수(후리가나 읽기 제외)가 이보다 짧으면 경고. N4~N5 지문은 20자 안팎이었다.


def check_ja_quality(c, path):
    """일본어 중급(N3) 본문이 예전 N4~N5 길이에 머물면 경고한다. JA_LEVELS_FROM 이후 지문과 비축분만 본다."""
    if path.parent.parent.name != "pool":
        try:
            if dt.date.fromisoformat(path.stem) < JA_LEVELS_FROM:
                return []
        except ValueError:
            return []
    sents = c.get("sentences", [])
    if not sents:
        return []
    avg = sum(len(re.sub(r"\s", "", _plain(s.get("en", "")))) for s in sents) / len(sents)
    if avg < JA_MIN_AVG_CHARS:
        return [f"ja 본문 문장 평균 글자 수({avg:.1f})가 {JA_MIN_AVG_CHARS} 미만입니다. "
                "중급(N3) 본문은 한 문장 30~45자를 권장합니다(ROUTINE.ja.md)."]
    return []


def check(path):
    c = json.loads(path.read_text(encoding="utf-8"))
    errors, warnings = [], []
    for where, t in texts(c):
        rest = SUPPORTED.sub("", t)
        if LEFTOVER.search(rest):
            errors.append(f"{where}: 처리되지 않는 마크다운 기호가 남음: {t[:80]}")
        if "·" in t:  # 사이트 표기 규칙: 가운뎃점 대신 쉼표나 슬래시
            errors.append(f"{where}: 가운뎃점(·)은 쓰지 않아요. 쉼표나 슬래시로 바꾸세요: {t[:80]}")
    # photo_scene 검증: 있으면 영어 한 문장(40~300자)이어야 한다
    _scene = c.get("photo_scene")
    if _scene is not None:
        if not isinstance(_scene, str) or not _scene.strip():
            errors.append("photo_scene: 문자열이어야 해요.")
        elif len(_scene.strip()) < 40:
            errors.append(f"photo_scene: 40자 이상이어야 해요 (현재 {len(_scene.strip())}자). 구체적인 장면을 더 자세히 설명하세요.")
        elif len(_scene.strip()) > 300:
            errors.append(f"photo_scene: 300자 이하여야 해요 (현재 {len(_scene.strip())}자).")
    if not c.get("source") and not c.get("example"):  # 지어낸 예문은 페이지에 그렇다고 표시된다
        body = " ".join(SUPPORTED.sub(lambda m: m.group(0).strip("*`"), s.get("en", "")) for s in c.get("sentences", []))
        hits = sorted(set(m.group(0) for m in NUMBER.finditer(body)))
        if hits:
            warnings.append(f"출처 없이 구체적 수치가 있음({', '.join(hits)}). 출처를 달거나 수치를 빼세요.")
    if path.parent.parent.name == "pool":
        new_format = True  # 비축분은 모두 제목을 채웠다(2026-10-21). 새 비축분도 두 제목이 있어야 한다
    else:
        try:
            new_format = dt.date.fromisoformat(path.stem) >= dt.date(2026, 10, 22)
        except ValueError:
            new_format = False
    if new_format:
        for k in ("title_ko", "headline"):
            if not str(c.get(k) or "").strip():
                errors.append(f"{k} 가 비어 있어요. 페이지 제목에 쓰입니다(ROUTINE 의 필드 설명 참고).")
    lang = path.parent.name
    try:
        L = _langs.LANGS.get(lang, {})
    except Exception:
        L = {}
    if L.get("chunks", lang == "en"):
        errors += check_chunks(c, required=path.parent.parent.name == "pool" or new_chunks(path, lang))
    if L.get("levels", lang == "en"):
        errors += check_levels_a(c, path)
        # levels.a 에도 출처 없는 수치 경고 적용
        levels_a = (c.get("levels") or {}).get("a")
        if levels_a and not c.get("source") and not c.get("example"):
            body_a = " ".join(s.get("en", "") for s in levels_a.get("sentences", []))
            hits_a = sorted(set(m.group(0) for m in NUMBER.finditer(body_a)))
            if hits_a:
                warnings.append(f"levels.a 에 출처 없는 구체적 수치({', '.join(hits_a)}). 출처를 달거나 수치를 빼세요.")
    errors += check_example_ko(c, path)
    errors += overlap(path, c)
    errors += check_word_meanings(c, path)
    errors += check_duplicate_meanings(c, path)
    errors += check_de_noun_gender(c, path)
    if path.parent.name == "de":
        de_errors, de_warnings = check_de_quality(c, path)
        errors += de_errors
        warnings += de_warnings
    if path.parent.name == "ja":
        warnings += check_ja_quality(c, path)
    style_errors, style_warnings = check_style(c, path)
    errors += style_errors
    warnings += style_warnings
    warnings += check_plan(c, path)
    return errors, warnings


STYLE_FROM = dt.date(2026, 11, 4)  # 이날 지문부터 뜻풀이, 제목, 일본어 출처 경고(그 전 발행분은 2026-11-03 손으로 점검해 고침)
_JA_CHARS = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff]")
_PAREN = re.compile(r"\([^()]*\)")
_PARAPHRASE = re.compile(r"(는 것|하는 |없고|이 없는|정한 |하는 일|좋은 때|드는 정도)")
_TITLE_TAIL = re.compile(r"(하려고|기까지의|하기 위해|위한 )")


def _gloss_head(m):
    """뜻의 첫 대응어(쓰임을 좁히는 괄호와 성별 괄호는 뺀다)."""
    return _PAREN.sub("", m).strip().split(",")[0].strip()


def check_style(c, path):
    """2026-11-03 사용자 지적이 다시 나오지 않게 막는다.
    - 오류: 일본어 뜻에 가나나 한자(일본어 읽기)가 들어 있으면 단어 쓰기 힌트에 답이 보인다(7つ '일곱 개 (ななつ)').
    - 경고: 뜻을 사전 대응어 대신 풀어 썼거나(平和 '전쟁이 없고 평온함'), 제목이 설명처럼 길거나,
      일본어 화, 수, 금 지문에 출처가 없을 때. 경고는 발행을 막지 않지만 루틴이 고치고 다시 검사한다."""
    errors, warnings = [], []
    lang = path.parent.name
    if lang == "ja":
        for w in c.get("words", []):
            if len(w) >= 2 and _JA_CHARS.search(w[1]):
                errors.append(f"words: '{w[0]}' 의 뜻에 일본어(가나, 한자)가 들어 있어 단어 쓰기 힌트에 답이 보여요: {w[1]}. 한국어로만 쓰세요.")
    if path.parent.parent.name != "pool":
        try:
            day = dt.date.fromisoformat(path.stem)
        except ValueError:
            return errors, warnings
        if day < STYLE_FROM:
            return errors, warnings
    else:
        day = None
    glosses = [("words", w[0], w[1]) for w in c.get("words", []) if len(w) >= 2]
    glosses += [("advanced", a.get("word", ""), a.get("meaning", "")) for a in c.get("advanced") or []]
    for kind, word, m in glosses:
        h = _gloss_head(m)
        if len(h.replace(" ", "")) > 9 or _PARAPHRASE.search(h):
            warnings.append(f"{kind}: '{word}' 의 뜻 '{m}' 이 풀어 쓴 설명 같아요. 한국어 사전의 대응어로 짧게 쓰세요"
                            "(예: 平和 → 평화, 機会 → 기회, Einwegflasche → 일회용 병). 대응어가 정말 없을 때만 설명을 두세요.")
    t = str(c.get("title_ko") or "")
    if len(t.replace(" ", "")) > 18 or _TITLE_TAIL.search(t):
        warnings.append(f"title_ko '{t}' 가 설명처럼 길어요. 15자 안팎의 명사구로, 원문 제목을 옮기지 말고 새로 지으세요(ROUTINE 의 제목 짓는 법).")
    if lang == "ja" and day and day < PLAN_FROM and day.weekday() in (1, 2, 4) and not c.get("source"):  # 이후는 check_plan
        warnings.append("화, 수, 금 일본어 지문은 출처가 필요해요(ROUTINE.ja.md 2번). 공식 페이지를 찾아 source 를 달거나, 못 찾았으면 마지막 답변에 이유를 적으세요.")
    return errors, warnings


PLAN_FROM = dt.date(2026, 11, 7)  # 이날 지문부터 공통 주간 구조(ROUTINE.common.md)를 검사한다
TOPIC_DAYS = 90
EN_WORDS = (12, 26)  # 영어 중급 한 문장 단어 수
EN_B2_MAX = 30
_KO_WORD = re.compile(r"[가-힣]{2,}")
_JOSA = re.compile(r"(에서|으로|에게|부터|까지|의|을|를|은|는|와|과|로|에)$")
GENERIC_WORDS = {
    "이야기", "오늘", "일본", "일본어", "독일", "독일어", "영어", "한국", "세계", "사람", "우리", "소식", "시작",
    "가장", "작은", "새로운", "새로", "방법", "이유", "원리", "시간", "하루", "이날", "모습", "동네", "마을",
    "유럽", "미국", "도시", "문화", "사회", "과학", "기술", "미래", "생활", "준비", "첫날",
    "가을", "겨울", "여름", "만든", "있는", "거대한", "처음", "경험", "대화", "일상", "장면",
    "프랑스", "영국", "중국", "스위스", "오스트리아", "이탈리아", "스페인", "캐나다", "호주", "대만",
    "서울", "부산", "도쿄", "교토", "오사카", "삿포로", "후쿠오카", "베를린", "뮌헨", "함부르크", "쾰른",
    "빈", "취리히", "런던", "맨체스터", "파리", "뉴욕", "포트워스", "텍사스", "캘리포니아",
}


def _topic_terms(c):
    """topic, keywords 의 한국어 낱말. 조사를 뗀 형태도 넣는다. title_ko 는 꾸밈말이 많아 비교하지 않는다."""
    text = " ".join([str(c.get("topic") or "")] + [str(k) for k in c.get("keywords") or []])
    terms = set()
    for w in _KO_WORD.findall(text):
        stem = _JOSA.sub("", w) if len(w) >= 3 else w
        if stem not in GENERIC_WORDS and w not in GENERIC_WORDS:
            terms.update(t for t in (w, stem) if len(t) >= 2)
    return terms


def topic_list(lang, day, days=TOPIC_DAYS, root=ROOT):
    """day 이전 최근 days 일의 (날짜, 지문)을 오래된 순서로 돌려준다."""
    day = dt.date.fromisoformat(day) if isinstance(day, str) else day
    start = (day - dt.timedelta(days=days)).isoformat()
    out = []
    for p in sorted((root / "content" / lang).glob("*.json")):
        if start <= p.stem < day.isoformat():
            out.append((p.stem, json.loads(p.read_text(encoding="utf-8"))))
    return out


def topic_repeats(lang, day, c, root=ROOT):
    """최근 지문과 소재 낱말이 겹치면 경고를 만든다. 본문 유사도가 아니라 소재를 본다."""
    mine = _topic_terms(c)
    out = []
    for d, old in topic_list(lang, day, root=root):
        same = sorted(mine & _topic_terms(old))
        if same:
            out.append(f"소재 반복: {d} '{old.get('topic')}' 와 '{', '.join(same)}' 이 겹쳐요. "
                       "같은 소재나 장면이면 고치고, 낱말만 겹치면 그대로 둡니다(ROUTINE.common.md 5절).")
    return out


def check_plan(c, path, plan_from=None):
    """공통 주간 구조 경고. 발행을 막지 않고, 비축분에는 적용하지 않는다."""
    if path.parent.parent.name == "pool":
        return []
    try:
        day = dt.date.fromisoformat(path.stem)
    except ValueError:
        return []
    if day < (plan_from or PLAN_FROM):
        return []
    warnings = []
    lang = path.parent.name
    want = _grammar.fit_of(day)
    if c.get("fit") != want:
        warnings.append(f"fit 은 요일 유형 '{want}' 이어야 해요(현재 {c.get('fit')!r}, ROUTINE.common.md 1절). 출처를 못 찾은 날도 그대로 둡니다.")
    if want in ("news", "explain") and not c.get("source"):
        warnings.append(f"{want} 날은 출처가 필요해요(ROUTINE.common.md 1절). 다시 찾고, 못 찾았으면 마지막 답변에 이유를 적으세요.")
    warnings += _check_grammar(c, lang)
    if "keywords" not in c:
        warnings.append("keywords 가 없어요. 소재 낱말 2~4개와 장면 유형 1개를 쓰세요(ROUTINE.common.md 1절, 5절).")
    if lang == "en":
        for n, s in enumerate(c.get("sentences", []), 1):
            count = len(_plain(s.get("en", "")).split())
            top = EN_B2_MAX if s.get("b2") else EN_WORDS[1]
            if not EN_WORDS[0] <= count <= top:
                warnings.append(f"sentences {n}번이 {count}단어예요. 중급은 {EN_WORDS[0]}~{EN_WORDS[1]}단어, b2 문장만 {EN_B2_MAX}단어까지입니다.")
    warnings += topic_repeats(lang, day, c, root=path.parent.parent.parent)
    return warnings


def _check_grammar(c, lang):
    if "grammar" not in c:
        return ["grammar 가 없어요. 쓴 문법 id 를 적고, 없으면 빈 목록으로 두세요(ROUTINE.common.md 3절)."]
    try:
        table = _grammar.load(lang)
    except OSError:
        return []
    bodies = {"b": c.get("sentences", []), "a": ((c.get("levels") or {}).get("a") or {}).get("sentences", [])}
    out = []
    used = c.get("grammar") if isinstance(c.get("grammar"), dict) else {}
    for level, ids in used.items():
        items = {i["id"]: i for i in table.get(level, [])}
        for gid in ids or []:
            item = items.get(gid)
            if item is None:
                out.append(f"grammar: '{gid}' 는 {lang} {level} 목록에 없어요.")
            elif item["pattern"] and not any(re.search(item["pattern"], _plain(s.get("en", "")).strip()) for s in bodies.get(level, [])):
                out.append(f"grammar: '{gid}' 를 적었는데 {level} 지문의 어느 문장에서도 찾지 못했어요. 문장을 고치거나 grammar 에서 빼세요.")
    return out


WORD_HINT_FROM = dt.date(2026, 11, 1)  # 이날 지문부터 뜻에 단어를 다시 쓰면 오류(그 전 36개는 페이지에서 가린다)


def check_duplicate_meanings(c, path):
    """같은 날 단어 중 뜻이 겹치는 쌍을 오류로 잡는다(4지선다 답 누출 방지)."""
    try:
        import drill  # noqa: PLC0415
    except ImportError:
        return []
    lang = path.parent.name
    day = path.stem
    try:
        probs = drill.problems(lang, day)
    except Exception:
        return []
    errors = []
    for a, b, m in probs.get("duplicate_meanings", []):
        errors.append(f"단어 뜻 중복: '{a}'와 '{b}'의 뜻이 같습니다 ({m}). 4지선다 답이 새어 나옵니다.")
    return errors


_GENDER_BRACKET = re.compile(r'\s*\((?:남성|여성|중성)\b[^()]*\)')  # (남성 der), (여성 die), (중성 das, 복수 …) 등


def check_word_meanings(c, path):
    """뜻 괄호에 답이 든 주요 단어. 판정은 페이지가 힌트에서 가리는 규칙(drill._hint)과 같다.
    관사 표기 (남성 der)/(여성 die)/(중성 das) 는 정상이므로 제거 후 검사한다."""
    if path.parent.parent.name != "pool":
        try:
            if dt.date.fromisoformat(path.stem) < WORD_HINT_FROM:
                return []
        except ValueError:
            return []
    import drill  # 페이지 생성 모듈. 이 검사에서만 쓴다  # noqa: PLC0415
    out = []
    for w in c.get("words", []):
        if len(w) < 2:
            continue
        # 관사 표기 괄호를 제외한 뜻 기준으로 검사: (여성 die), (중성 das, 복수 Blätter) 등은 정상
        m_clean = _GENDER_BRACKET.sub("", w[1]).strip()
        if drill._hint(m_clean, w[0]) != m_clean:
            out.append(f"words: '{w[0]}' 의 뜻 괄호에 그 단어가 들어 있어 단어 쓰기 힌트에 답이 보여요: {w[1]}. "
                       "관사는 '(중성 das)'처럼 관사만, 복수형이나 과거형은 '(복수형)', '(과거형)'처럼 단어를 쓰지 말고 적으세요.")
    return out


DE_GENDER_FROM = dt.date(2026, 10, 28)  # 이날부터 독일어 명사는 뜻에 성별 표기가 있어야 한다


def check_de_noun_gender(c, path):
    """독일어 명사(대문자로 시작)는 뜻에 성별 표기((남성 der), (여성 die), (중성 das))가 있어야 한다."""
    lang = path.parent.name
    if lang != "de":
        return []
    if path.parent.parent.name != "pool":
        try:
            if dt.date.fromisoformat(path.stem) < DE_GENDER_FROM:
                return []
        except ValueError:
            return []
    gender_pat = re.compile(r'\((?:남성|여성|중성)\s+(?:der|die|das)\b')
    out = []
    for w in c.get("words", []):
        if len(w) < 2:
            continue
        word, meaning = w[0], w[1]
        if word[:1].isupper() and not gender_pat.search(meaning):
            out.append(
                f"words: '{word}' 는 명사이므로 뜻에 성별 표기가 필요합니다. "
                "뜻 끝에 '(남성 der)', '(여성 die)', '(중성 das)' 중 하나를 추가하세요. "
                "복수형이 있으면 '(중성 das, 복수 Blätter)'처럼 한 괄호 안에 씁니다."
            )
    return out


CHUNKS_FROM = dt.date(2026, 10, 23)  # 이날 지문부터 영어 문장마다 끊어 읽기(chunks)가 있어야 한다
DE_CHUNKS_FROM = dt.date(2026, 10, 28)  # 독일어 루틴 시작일. 이날 이후 독일어 지문에 chunks 필수.
LEVELS_FROM = dt.date(2026, 10, 23)  # 이날 이후 영어 지문에 levels.a 필드가 필수
EXAMPLE_KO_FROM = dt.date(2026, 10, 23)  # 이날 이후 advanced 항목에 example_ko 필드가 필수
DE_LEVELS_FROM = dt.date(2026, 10, 29)   # 이날 이후 독일어 지문에 levels.a 필수
JA_LEVELS_FROM = dt.date(2026, 10, 29)   # 이날 이후 일본어 지문에 levels.a 필수(본문은 N3, levels.a 는 N4~N5)

_LEVELS_FROM_MAP = {
    "en": LEVELS_FROM,
    "de": DE_LEVELS_FROM,
    "ja": JA_LEVELS_FROM,
}

_CHUNKS_FROM_MAP = {
    "en": CHUNKS_FROM,
    "de": DE_CHUNKS_FROM,
}


def new_chunks(path, lang=None):
    """이 파일에 chunks 가 필수인지 판단한다. lang 을 넘기면 언어별 시작일을 사용한다."""
    if lang is None:
        lang = path.parent.name
    from_date = _CHUNKS_FROM_MAP.get(lang, CHUNKS_FROM)
    try:
        return dt.date.fromisoformat(path.stem) >= from_date
    except ValueError:
        return False


def levels_required(path):
    """이 파일에 levels.a 필드가 필수인지 판단한다."""
    lang = path.parent.name
    if lang not in _LEVELS_FROM_MAP:
        return False
    if path.parent.parent.name == "pool":
        return True  # 수준을 나눈 언어의 비축분은 levels.a 필수
    try:
        return dt.date.fromisoformat(path.stem) >= _LEVELS_FROM_MAP[lang]
    except ValueError:
        return False


def check_levels_a(c, path):
    """levels.a 필드가 있으면 검증하고, 언어별 시작일(_LEVELS_FROM_MAP) 이후 지문이나 비축분인데 없으면 오류를 낸다."""
    out = []
    lang = path.parent.name
    if lang not in _LEVELS_FROM_MAP:
        return out
    missing = "levels.a 필드가 없어요. 기초 지문은 시작일 이후 지문과 비축분에 필수입니다(ROUTINE 의 levels 설명 참고)."
    levels = c.get("levels")
    if levels is None:
        if levels_required(path):
            out.append(missing)
        return out
    levels_a = levels.get("a")
    if levels_a is None:
        if levels_required(path):
            out.append(missing)
        return out
    main_n = len(c.get("sentences", []))
    a_sents = levels_a.get("sentences", [])
    a_answers = levels_a.get("answers", [])
    if len(a_sents) != main_n:
        out.append(f"levels.a.sentences 개수({len(a_sents)})가 sentences 개수({main_n})와 달라요. 1:1 대응이어야 해요.")
    if len(a_answers) != len(a_sents):
        out.append(f"levels.a.answers 개수({len(a_answers)})가 levels.a.sentences 개수({len(a_sents)})와 달라요.")
    # levels.a.sentences[].en 에 마크다운/가운뎃점 검사 적용
    for i, s in enumerate(a_sents, 1):
        en = s.get("en", "")
        rest = SUPPORTED.sub("", en)
        if LEFTOVER.search(rest):
            out.append(f"levels.a.sentences {i}번 en: 처리되지 않는 마크다운 기호가 남음: {en[:80]}")
        if "·" in en:
            out.append(f"levels.a.sentences {i}번 en: 가운뎃점(·)은 쓰지 않아요: {en[:80]}")
    # levels.a.sentences[].chunks 검사: chunks 를 쓰는 언어(en, de)는 필수, 일본어처럼 쓰지 않는 언어는 있을 때만 검사
    needs_chunks = _langs.LANGS.get(lang, {}).get("chunks", lang == "en")
    out += check_chunks({"sentences": [{"en": s.get("en", ""), "chunks": s.get("chunks")} for s in a_sents]}, required=needs_chunks)
    return out


def check_chunks(c, required=False):
    """끊어 읽기 덩어리를 검사한다. 덩어리를 공백 하나로 이으면 문장(en)과 정확히 같아야 한다(** 표시 포함)."""
    out = []
    for i, s in enumerate(c.get("sentences", []), 1):
        ch = s.get("chunks")
        if ch is None:
            if required:
                out.append(f"sentences {i}번에 chunks 가 없어요. 끊어 읽기 덩어리를 넣으세요(ROUTINE 의 chunks 설명 참고).")
            continue
        if not isinstance(ch, list) or not ch:
            out.append(f"sentences {i}번 chunks 는 [영어 덩어리, 한국어 뜻] 목록이어야 해요.")
            continue
        bad = [x for x in ch if not (isinstance(x, list) and len(x) == 2 and all(isinstance(t, str) and t.strip() for t in x))]
        if bad:
            out.append(f"sentences {i}번 chunks 에 영어나 뜻이 빈 항목이 있어요: {str(bad[0])[:80]}")
            continue
        if any(x[0].count("**") % 2 for x in ch):
            out.append(f"sentences {i}번 chunks: ** 표시는 한 덩어리 안에서 열고 닫아야 해요.")
        joined = " ".join(x[0] for x in ch)
        if joined != s.get("en"):
            out.append(f"sentences {i}번 chunks 를 이은 글이 문장과 달라요: {joined[:80]}")
    return out


def example_ko_required(path):
    """이 파일에 advanced[].example_ko 필드가 필수인지 판단한다."""
    if path.parent.parent.name == "pool":
        return True  # pool 비축분은 언어 무관하게 advanced 항목에 example_ko 필수
    try:
        return dt.date.fromisoformat(path.stem) >= EXAMPLE_KO_FROM
    except ValueError:
        return False


def check_example_ko(c, path):
    """advanced 항목의 example_ko 필드를 검증한다.
    있으면: 비어 있지 않고, 마크다운 잔재가 없고, 가운뎃점이 없어야 한다.
    EXAMPLE_KO_FROM 이후 지문이면: 모든 항목에 있어야 한다."""
    out = []
    required = example_ko_required(path)
    for i, a in enumerate(c.get("advanced", []), 1):
        eko = a.get("example_ko")
        if eko is None:
            if required:
                out.append(f"advanced {i}번에 example_ko 가 없어요. EXAMPLE_KO_FROM 이후 지문에는 필수입니다.")
            continue
        if not str(eko).strip():
            out.append(f"advanced {i}번 example_ko 가 비어 있어요.")
            continue
        rest = SUPPORTED.sub("", str(eko))
        if LEFTOVER.search(rest):
            out.append(f"advanced {i}번 example_ko: 처리되지 않는 마크다운 기호가 남음: {str(eko)[:80]}")
        if "·" in str(eko):
            out.append(f"advanced {i}번 example_ko: 가운뎃점(·)은 쓰지 않아요. 쉼표나 슬래시로 바꾸세요.")
    return out


# 내용 겹침 기준. 2026-10 지문으로 맞췄다: 실제로 겹친 두 쌍(수리 카페 0.16, 로보택시 0.13)은 걸리고,
# 서로 다른 지문끼리는 가장 높아도 0.09였다.
OVERLAP_DAYS = 14
OVERLAP_JACCARD = 0.12
OVERLAP_KEYWORDS = 2
OVERLAP_MIN_SHARED = 6  # 아주 짧은 글끼리 우연히 겹친 비율에 속지 않도록, 겹친 단어가 이만큼은 있어야 한다
# 일본어는 띄어쓰기가 없어 세 글자 묶음으로 비교한다. 문법 어미처럼 어느 글에나 나오는 묶음은 뺀다.
# 2026-10 지문끼리는 가장 높아도 0.06(12개)였고, 같은 이야기를 바꿔 쓴 글은 0.24(30개)였다.
OVERLAP_JA_JACCARD = 0.15
OVERLAP_JA_MIN_SHARED = 15
JA_COMMON = set("ありま いです いまし います かった があり しまし たです ったで とても なりま ました ません りまし ります わたし 一緒に 友だち 土曜日".split())
STOPWORDS = set("""that this with from they their have been will would about which when there were also more than into
some only other them your what because could after first still most such those these over even just where every each like
says said made make many much very well while week year years people help team small called uses used""".split())

# 독일어 불용어 (~60개). 자주 나오지만 내용 분별에 도움이 안 되는 단어.
DE_STOPWORDS = set("""aber alle allen allem alles also auch auf
dass dem den der des die dies diese diesem diesen dieser dieses
dort durch ein eine einem einen einer eines
gegen haben hat hier
kann kein keine keinem keinen keiner
macht mehr mich mit
nach nicht noch
oder ohne
schon sehr sich sind
über unter uns
viel viele von vor
weil wenn werden wird wir
zum zur""".split())


def _plain(t):
    return re.sub(r"\{([^|}]+)\|[^}]+\}", r"\1", t.replace("**", "").replace("`", ""))


def _content_words(c):
    body = " ".join(_plain(s.get("en", "")) for s in c.get("sentences", [])).lower()
    return set(re.findall(r"[a-z']{4,}", body)) - STOPWORDS


def _de_content_words(c):
    """독일어 지문에서 내용어를 추출한다. Umlaut(ä,ö,ü)와 ß 를 포함한 정규식을 쓴다."""
    body = " ".join(_plain(s.get("en", "")) for s in c.get("sentences", [])).lower()
    return set(re.findall(r"[a-zäöüß]{4,}", body)) - DE_STOPWORDS


def _keywords(c):
    return {re.sub(r"\s*\(.*?\)", "", _plain(w[0])).strip().lower() for w in c.get("words", []) if w}


def _ja_grams(c):
    text = re.sub(r"[\s。、「」『』？！・…\.\?!,0-9０-９]", "", " ".join(_plain(s.get("en", "")) for s in c.get("sentences", [])))
    return {text[i:i + 3] for i in range(len(text) - 2)}


def _ja_common(folder):
    """지문이 10편 넘게 쌓이면, 20%가 넘는 지문에 나오는 묶음을 흔한 표현으로 보고 뺀다."""
    docs = [_ja_grams(json.loads(q.read_text(encoding="utf-8"))) for q in folder.glob("*.json")]
    common = set(JA_COMMON)
    if len(docs) >= 10:
        from collections import Counter
        df = Counter(g for d in docs for g in d)
        common |= {g for g, k in df.items() if k / len(docs) > 0.2}
    return common


def overlap(path, c, days=OVERLAP_DAYS):
    """content/<언어>/YYYY-MM-DD.json 을 앞선 days일 지문과 비교해 같은 이야기를 반복하면 오류 문구를 돌려준다."""
    try:
        day = dt.date.fromisoformat(path.stem)
    except ValueError:
        return []
    if path.parent.parent.name != "content":
        return []
    lang = path.parent.name
    url = (c.get("source") or {}).get("url")
    mine_w = _de_content_words(c) if lang == "de" else _content_words(c)
    mine_k = _keywords(c)
    if lang == "ja":
        ja_common = _ja_common(path.parent)
        mine_g = _ja_grams(c) - ja_common
    out = []
    for q in sorted(path.parent.glob("*.json")):
        try:
            d = dt.date.fromisoformat(q.stem)
        except ValueError:
            continue
        if not 0 < (day - d).days <= days:
            continue
        o = json.loads(q.read_text(encoding="utf-8"))
        tag = f"{q.stem} {o.get('topic', '')}"
        if url and url == (o.get("source") or {}).get("url"):
            out.append(f"최근 지문({tag})과 같은 기사예요. 다른 소식으로 바꾸세요.")
            continue
        shared = sorted(mine_k & _keywords(o))
        if len(shared) >= OVERLAP_KEYWORDS:
            out.append(f"최근 지문({tag})과 형광펜 단어가 겹쳐요({', '.join(shared)}). 같은 내용을 반복하지 말고 새로 생긴 일에 초점을 맞추거나 다른 소식으로 바꾸세요.")
            continue
        if lang == "ja":
            og = _ja_grams(o) - ja_common
            shared_g = mine_g & og
            j = len(shared_g) / max(1, len(mine_g | og))
            if j >= OVERLAP_JA_JACCARD and len(shared_g) >= OVERLAP_JA_MIN_SHARED:
                out.append(f"최근 지문({tag})과 본문 내용이 {j:.0%} 겹쳐요({', '.join(sorted(shared_g)[:10])}). 같은 내용을 반복하지 말고 새로 생긴 일에 초점을 맞추거나 다른 소재로 바꾸세요.")
        if lang in ("en", "de"):
            other = _de_content_words(o) if lang == "de" else _content_words(o)
            j = len(mine_w & other) / max(1, len(mine_w | other))
            if j >= OVERLAP_JACCARD and len(mine_w & other) >= OVERLAP_MIN_SHARED:
                words = ", ".join(sorted(mine_w & other)[:12])
                out.append(f"최근 지문({tag})과 본문 내용이 {j:.0%} 겹쳐요({words}). 같은 설명을 반복하지 말고 새로 생긴 일에 초점을 맞추거나 다른 소식으로 바꾸세요.")
    return out


def main(paths):
    failed = False
    for p in paths:
        errors, warnings = check(p)
        for e in errors:
            print(f"::error file={p.relative_to(ROOT)}::{e}")
        for w in warnings:
            print(f"::warning file={p.relative_to(ROOT)}::{w}")
        failed |= bool(errors)
        if not errors and not warnings:
            print(f"ok {p.relative_to(ROOT)}")
    sys.exit(1 if failed else 0)


def main_overlap(lang, day):
    """발행 워크플로용: 내용 겹침만 검사한다. 겹치면 종료 코드 1."""
    p = ROOT / "content" / lang / f"{day}.json"
    if not p.exists():
        print(f"::error::{p.relative_to(ROOT)} 파일이 없어요")
        sys.exit(1)
    errors = overlap(p, json.loads(p.read_text(encoding="utf-8")))
    for e in errors:
        print(f"::error file={p.relative_to(ROOT)}::{e}")
    if not errors:
        print(f"no overlap {p.relative_to(ROOT)}")
    sys.exit(1 if errors else 0)


def main_topics(lang, day):
    """지문을 쓰기 전에 볼 최근 90일 소재 목록."""
    for d, c in topic_list(lang, day):
        print(f"{d} | {c.get('topic')} | {c.get('title_ko')} | {', '.join(c.get('keywords') or [])}")


def main_repeat(lang, day):
    """소재 반복만 검사한다. 날짜 기준 없이 돌리고 종료 코드는 언제나 0."""
    p = ROOT / "content" / lang / f"{day}.json"
    found = topic_repeats(lang, day, json.loads(p.read_text(encoding="utf-8")))
    for w in found:
        print(f"::warning file={p.relative_to(ROOT)}::{w}")
    if not found:
        print(f"no repeat {p.relative_to(ROOT)}")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--overlap"]:
        main_overlap(sys.argv[2], sys.argv[3])
    elif sys.argv[1:2] == ["--topics"]:
        main_topics(sys.argv[2], sys.argv[3])
    elif sys.argv[1:2] == ["--repeat"]:
        main_repeat(sys.argv[2], sys.argv[3])
    elif sys.argv[1:] == ["--all"]:
        main(sorted(ROOT.glob("content/*/*.json")))
    elif sys.argv[1:] == ["--pool"]:
        # pool/<lang>/*.json 파일을 모두 검사한다
        pool_files = sorted(ROOT.glob("pool/*/*.json"))
        if not pool_files:
            print("pool 파일 없음")
            sys.exit(0)
        main(pool_files)
    else:
        main([ROOT / "content" / sys.argv[1] / f"{sys.argv[2]}.json"])
