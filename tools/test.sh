#!/usr/bin/env bash
# 단위 테스트 전부: 파이썬(tools, 생성 페이지), 브라우저 스크립트와 위 메뉴 계약(tests/*.test.mjs), API Worker, 옛 주소 이동.
# ci.yml 과 push 전 점검(.githooks/pre-push)이 같이 쓴다. 지문 검사(check_content)는 ci 에서만 돈다.
set -euo pipefail
cd "$(dirname "$0")/.."
python -m pytest -q tests
# landing/src/lib/me.ts 를 node 가 타입만 지워 바로 읽는다(node 23.6 이상). 그 파일의 모듈 형식 경고는 끈다
node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test tests/*.test.mjs worker/*.test.mjs tools/cf/*.test.mjs
