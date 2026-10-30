#!/usr/bin/env bash
# ref-clone 정적 빌드에서 첫 화면(index.html)과 _next/ 만 english-reading 루트로 복사한다.
# 다른 파일(404.html 등)은 기존 사이트 파일을 덮어쓰지 않도록 가져가지 않는다.
# 사용: scripts/deploy-landing.sh [english-reading 경로]   (빌드는 npm run build 로 먼저)
set -euo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${1:-$HERE/..}"
OUT="$HERE/out"

[ -f "$OUT/index.html" ] && [ -d "$OUT/_next" ] || { echo "out/ 가 없습니다. 먼저 npm run build 를 실행하세요." >&2; exit 1; }
{ [ -d "$DEST/.git" ] || [ -f "$DEST/.git" ]; } || { echo "english-reading 저장소가 아닙니다: $DEST" >&2; exit 1; }

rm -rf "$DEST/_next"
cp -R "$OUT/_next" "$DEST/_next"
cp "$OUT/index.html" "$DEST/index.html"
# 아이콘은 Next 가 out/ 루트에 내보내므로 함께 복사한다.
for f in apple-icon.png; do [ -f "$OUT/$f" ] && cp "$OUT/$f" "$DEST/$f"; done
# icon.svg 대신 icon.png(favicon)를 icon-32.png 로 복사한다.
[ -f "$OUT/icon.png" ] && cp "$OUT/icon.png" "$DEST/icon-32.png" && cp "$OUT/icon.png" "$DEST/icon.png"  # 랜딩 index.html 은 /icon.png 를 가리킨다
echo "복사 완료: $DEST/index.html, $DEST/_next/, 아이콘"
