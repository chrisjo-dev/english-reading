#!/usr/bin/env bash
# landing/out/ → 저장소 루트 복사 (배포가 아니라 빌드 결과를 루트에 반영)
# 언어 페이지(en/ ja/ de/), 콘텐츠, 설정 파일은 건드리지 않는다.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$REPO/landing/out"

if [ ! -d "$OUT" ]; then
  echo "landing/out/ 가 없습니다. npm run build 를 먼저 실행하세요." >&2
  exit 1
fi

# 루트에 복사할 파일/디렉터리 목록
COPY_FILES=(index.html 404.html apple-icon.png icon.png)
COPY_DIRS=(_next)

for f in "${COPY_FILES[@]}"; do
  if [ -f "$OUT/$f" ]; then
    cp -f "$OUT/$f" "$REPO/$f"
    echo "복사: $f"
  fi
done

for d in "${COPY_DIRS[@]}"; do
  if [ -d "$OUT/$d" ]; then
    rm -rf "$REPO/$d"
    cp -r "$OUT/$d" "$REPO/$d"
    echo "복사: $d/"
  fi
done

# assets/ 는 머지 (새 파일만 추가, 기존 파일 덮어쓰지 않음)
if [ -d "$OUT/assets" ]; then
  cp -rn "$OUT/assets/." "$REPO/assets/" 2>/dev/null || true
  echo "머지: assets/"
fi

echo "완료"
