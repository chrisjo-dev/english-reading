"""오늘 지문에 넣을 문법 후보를 고른다(규칙은 ROUTINE.common.md 3절).

사용: python3 tools/grammar_pick.py en b --day 2026-11-09
      python3 tools/grammar_pick.py ja a --day 2026-11-09 --skip 1   (다음 후보)
- 요일로 오늘 유형(fit)을 정하고, 그 유형에 맞는 항목 중 후보 3개를 낸다.
- 순서: content/<언어>/*.json 의 grammar 에 기록이 없는 항목, 가장 오래전에 쓴 항목, 같으면 목록 순서.
- 후보가 없거나 읽지 못해도 0 으로 끝난다. 예약 작업은 이 단계에서 멈추지 않는다.
"""
import argparse
import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COUNT = 3
FIT_BY_WEEKDAY = ("news", "explain", "news", "explain", "news", "life", "life")  # 월요일부터


def fit_of(day):
    return FIT_BY_WEEKDAY[day.weekday()]


def load(lang, root=ROOT):
    return json.loads((root / "tools" / "grammar" / f"{lang}.json").read_text(encoding="utf-8"))


def history(lang, level, day, root=ROOT):
    """day 이전 지문에서 항목별 마지막 사용일을 모은다."""
    last = {}
    for p in sorted((root / "content" / lang).glob("*.json")):
        if p.stem >= day.isoformat():
            continue
        grammar = json.loads(p.read_text(encoding="utf-8")).get("grammar")
        if isinstance(grammar, dict):
            for gid in grammar.get(level) or []:
                last[gid] = p.stem
    return last


def candidates(lang, level, day, skip=0, root=ROOT):
    fit = fit_of(day)
    last = history(lang, level, day, root)
    items = [i for i in load(lang, root).get(level, []) if fit in i["fit"]]
    ordered = sorted(enumerate(items), key=lambda x: (x[1]["id"] in last, last.get(x[1]["id"], ""), x[0]))
    return [i for _, i in ordered][skip * COUNT:(skip + 1) * COUNT]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lang")
    ap.add_argument("level", choices=["a", "b"])
    ap.add_argument("--day", required=True)
    ap.add_argument("--skip", type=int, default=0, help="앞에서 건너뛸 후보 묶음 수")
    args = ap.parse_args()
    try:
        day = dt.date.fromisoformat(args.day)
        picks = candidates(args.lang, args.level, day, max(args.skip, 0))
    except (OSError, ValueError, KeyError) as e:
        print(f"후보 없음: {e}")
        return
    print(f"fit={fit_of(day)}")
    if not picks:
        print("후보 없음")
    for i in picks:
        print(f"{i['id']} | {i['name']} | {i['example']}")


if __name__ == "__main__":
    main()
