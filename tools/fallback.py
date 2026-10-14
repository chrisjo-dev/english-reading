"""pool/<언어>/*.json 에서 오늘 지문이 없을 때 비축분을 꺼내 content 에 복사한다.

사용: python3 tools/fallback.py [--lang en|ja] [--day YYYY-MM-DD] [--dry-run]
- --lang 없으면 langs.LANGS 의 모든 언어를 처리한다.
- --day 없으면 오늘(Asia/Seoul 기준).
- --dry-run: 파일을 쓰거나 지우지 않고 어떤 결과가 될지만 보여 준다.

출력 요약 (한 줄/언어):
  EXISTS <lang>               — content/<lang>/<day>.json 이 이미 있음
  USED <lang> <day> <pool-file> <remaining>  — 비축분을 사용함
  EMPTY <lang>                — 사용 가능한 비축분이 없음
"""
import argparse
import datetime
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_content  # noqa: E402
import langs          # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
POOL_DIR = ROOT / "pool"
CONTENT_DIR = ROOT / "content"

# 같은 주제를 반복하지 않도록 제한하는 기간(일)
TOPIC_EXCLUDE_DAYS = 60


def kst_today():
    """Asia/Seoul 기준 오늘 날짜 문자열 YYYY-MM-DD."""
    # KST = UTC+9
    return (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)).strftime("%Y-%m-%d")


def recent_topics(lang: str, day: str, days: int = TOPIC_EXCLUDE_DAYS) -> set:
    """content/<lang>/ 에서 최근 days일 이내에 쓰인 topic 집합을 반환한다."""
    cutoff = datetime.date.fromisoformat(day) - datetime.timedelta(days=days)
    topics = set()
    for path in (CONTENT_DIR / lang).glob("*.json"):
        stem = path.stem
        try:
            d = datetime.date.fromisoformat(stem)
        except ValueError:
            continue
        if d >= cutoff:
            try:
                c = json.loads(path.read_text(encoding="utf-8"))
                t = c.get("topic")
                if t:
                    topics.add(t)
            except (json.JSONDecodeError, OSError):
                pass
    return topics


def pool_candidates(lang: str) -> list:
    """pool/<lang>/*.json 파일을 파일명 순으로 반환한다."""
    pool_lang = POOL_DIR / lang
    if not pool_lang.is_dir():
        return []
    return sorted(pool_lang.glob("*.json"))


def process_lang(lang: str, day: str, dry_run: bool) -> str:
    """한 언어를 처리하고 요약 줄을 반환한다."""
    dest = CONTENT_DIR / lang / f"{day}.json"

    # 이미 있으면 건너뜀
    if dest.exists():
        return f"EXISTS {lang}"

    used_topics = recent_topics(lang, day)
    candidates = pool_candidates(lang)

    # 사용 가능한 파일: 최근 60일 주제와 겹치지 않는 것
    available = []
    for p in candidates:
        try:
            c = json.loads(p.read_text(encoding="utf-8"))
            if c.get("topic") not in used_topics:
                available.append(p)
        except (json.JSONDecodeError, OSError):
            pass

    if not available:
        return f"EMPTY {lang}"

    # 가장 오래된 파일부터 시도
    for pool_file in available:
        if dry_run:
            # dry-run: 실제 파일 변경 없이 결과만 보여 준다
            remaining_after = len(candidates) - 1
            return f"USED {lang} {day} {pool_file.name} {remaining_after} (dry-run)"

        # content 디렉터리가 없을 수 있으므로 생성
        dest.parent.mkdir(parents=True, exist_ok=True)

        # 파일 내용에 date 를 설정해 content 에 씀
        try:
            c = json.loads(pool_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            print(f"[fallback] {pool_file.name} 읽기 오류, 다음 후보 시도: {e}", file=sys.stderr)
            continue

        c["date"] = day
        dest.write_text(json.dumps(c, ensure_ascii=False, indent=2), encoding="utf-8")

        # check_content 검증
        errors, warnings = check_content.check(dest)
        for w in warnings:
            print(f"[fallback] 경고({pool_file.name}): {w}", file=sys.stderr)
        if errors:
            for e in errors:
                print(f"[fallback] 오류({pool_file.name}): {e}", file=sys.stderr)
            # 오류: dest 파일 제거하고 다음 후보로
            dest.unlink(missing_ok=True)
            continue

        # 성공: pool 파일을 git rm (스테이징 + 삭제)
        result = subprocess.run(
            ["git", "rm", str(pool_file.relative_to(ROOT))],
            cwd=ROOT, capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(f"[fallback] git rm 실패, 직접 삭제: {result.stderr.strip()}", file=sys.stderr)
        # git rm 이 파일을 이미 지웠더라도 missing_ok=True 로 안전하게 처리한다
        pool_file.unlink(missing_ok=True)

        # 사용 후 남은 개수 (현재 pool 재계산)
        remaining = len([p for p in pool_candidates(lang)])
        return f"USED {lang} {day} {pool_file.name} {remaining}"

    # 후보가 있었으나 모두 check 실패
    return f"EMPTY {lang}"


def main():
    parser = argparse.ArgumentParser(description="비축분(pool)에서 오늘 지문을 꺼낸다")
    parser.add_argument("--lang", help="언어 코드 (en, ja). 없으면 모든 언어")
    parser.add_argument("--day", help="날짜 YYYY-MM-DD. 없으면 오늘(KST)")
    parser.add_argument("--dry-run", action="store_true", help="파일을 변경하지 않고 결과만 출력")
    args = parser.parse_args()

    day = args.day or kst_today()
    lang_codes = [args.lang] if args.lang else list(langs.LANGS.keys())

    # 알 수 없는 언어 코드 조기 검증
    for code in lang_codes:
        langs.get(code)

    if args.dry_run:
        print(f"[fallback] dry-run 모드: 파일을 변경하지 않습니다 (day={day})")

    any_empty = False
    for code in lang_codes:
        summary = process_lang(code, day, dry_run=args.dry_run)
        print(summary)
        if summary.startswith("EMPTY"):
            any_empty = True

    if any_empty:
        sys.exit(1)


if __name__ == "__main__":
    main()
