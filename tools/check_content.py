"""지문 JSON 을 올리기 전에 독자에게 보일 실수를 잡는다.

사용: python3 tools/check_content.py en 2026-10-14      (한 편)
      python3 tools/check_content.py --all              (전체)
- 오류(종료 코드 1): 지원하지 않는 마크다운 기호가 남아 화면에 그대로 보이는 경우. 예: *The List*, _word_, [링크](url)
- 경고: 출처(source)가 없는데 인원, 금액, 수량 같은 구체적 수치가 있는 경우. 실제 사실처럼 읽히므로 출처를 달거나 수치를 빼야 한다.
  널리 알려진 일반 상식(계절, 대략적인 통계)이면 그대로 둬도 되고, 지어낸 사례면 "example": true 를 넣는다.
- 오류: 같은 언어의 최근 14일 지문과 내용이 겹치는 경우. 주제가 같은 것은 괜찮고, 같은 기사(출처 주소)이거나
  형광펜 단어가 2개 이상 같거나, 본문이 많이 겹치면(영어: 핵심 단어 12% 이상, 일본어: 세 글자 묶음 15% 이상)
  같은 이야기를 반복하는 것으로 본다.
      python3 tools/check_content.py --overlap en 2026-10-14   (내용 겹침만 검사, 발행 워크플로가 쓴다)
"""
import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 화면에서 처리하는 표기: **굵게**, `코드`, {漢字|かな}. 이것을 지운 뒤 남은 기호를 찾는다.
SUPPORTED = re.compile(r"\*\*[^*]+\*\*|`[^`]+`|\{[^{}|]+\|[^{}]+\}")
LEFTOVER = re.compile(r"\*|(?<![\w])_[^_]+_(?![\w])|\[[^\]]+\]\([^)]+\)|^#+\s")
NUMBER = re.compile(r"\d{2,}|\b(?:hundred|thousand|million|billion|percent)\b|[百千万億]|パーセント|%", re.I)


def texts(c, where="", skip=("date", "category", "chips", "source")):
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


def check(path):
    c = json.loads(path.read_text(encoding="utf-8"))
    errors, warnings = [], []
    for where, t in texts(c):
        rest = SUPPORTED.sub("", t)
        if LEFTOVER.search(rest):
            errors.append(f"{where}: 처리되지 않는 마크다운 기호가 남음: {t[:80]}")
        if "·" in t:  # 사이트 표기 규칙: 가운뎃점 대신 쉼표나 슬래시
            errors.append(f"{where}: 가운뎃점(·)은 쓰지 않아요. 쉼표나 슬래시로 바꾸세요: {t[:80]}")
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
    errors += overlap(path, c)
    return errors, warnings


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


def _plain(t):
    return re.sub(r"\{([^|}]+)\|[^}]+\}", r"\1", t.replace("**", "").replace("`", ""))


def _content_words(c):
    body = " ".join(_plain(s.get("en", "")) for s in c.get("sentences", [])).lower()
    return set(re.findall(r"[a-z']{4,}", body)) - STOPWORDS


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
    mine_w, mine_k = _content_words(c), _keywords(c)
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
        if lang == "en":
            other = _content_words(o)
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


if __name__ == "__main__":
    if sys.argv[1:2] == ["--overlap"]:
        main_overlap(sys.argv[2], sys.argv[3])
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
