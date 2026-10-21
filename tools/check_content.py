"""지문 JSON 을 올리기 전에 독자에게 보일 실수를 잡는다.

사용: python3 tools/check_content.py en 2026-10-14      (한 편)
      python3 tools/check_content.py --all              (전체)
- 오류(종료 코드 1): 지원하지 않는 마크다운 기호가 남아 화면에 그대로 보이는 경우. 예: *The List*, _word_, [링크](url)
- 경고: 출처(source)가 없는데 인원, 금액, 수량 같은 구체적 수치가 있는 경우. 실제 사실처럼 읽히므로 출처를 달거나 수치를 빼야 한다.
  널리 알려진 일반 상식(계절, 대략적인 통계)이면 그대로 둬도 되고, 지어낸 사례면 "example": true 를 넣는다.
"""
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
    return errors, warnings


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


if __name__ == "__main__":
    if sys.argv[1:] == ["--all"]:
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
