#!/bin/bash
# 맥 미니에서 english-reading 워크플로를 시간에 맞춰 trigger 하는 스크립트.
# LaunchAgent 의 StartCalendarInterval 로 07:15, 07:45, 08:00, (일요일 08:30) KST 에 실행된다.
# 실행 시각을 읽어 어느 워크플로를 실행할지 판단한다.
#
# 사전 조건: gh auth login --scopes workflow (GitHub workflow 권한 포함)
# 로그: ~/Library/Logs/english-reading-mini-cron.log

PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin
REPO="chrisjo-dev/english-reading"
LOG="$HOME/Library/Logs/english-reading-mini-cron.log"

ts=$(date '+%Y-%m-%d %H:%M:%S')
hour=$(date +%H)
min=$(date +%M)
dow=$(date +%u)  # 1=월 ... 7=일

echo "$ts START hour=$hour min=$min dow=$dow" >> "$LOG"

run() {
  echo "$ts $*" >> "$LOG"
  gh workflow run "$@" -R "$REPO" >> "$LOG" 2>&1
  echo "$ts EXIT $?" >> "$LOG"
}

# 07:xx KST → fallback.yml (07:15 와 07:45 두 슬롯 모두 처리)
# GitHub 예약 작업이 늦어지거나 빠진 날 비축분에서 자동 발행한다.
# fallback.py 는 그날 content 가 이미 있으면 EXISTS 를 반환해 아무것도 하지 않으므로 중복 실행에 안전하다.
if [ "$hour" = "07" ]; then
  run fallback.yml

# 08:00 KST → catchup.yml
# 아침 본 메일을 받지 못한 구독자에게 보충 발송한다.
# send_email.catchup 은 이미 받은 구독자를 건너뛰므로 중복 실행에 안전하다.
elif [ "$hour" = "08" ] && [ "$min" = "00" ]; then
  run catchup.yml

# 08:30 KST 일요일 → weekly.yml
# 주간 단어 복습 메일. send_email.send 의 중복 발송 방지 로직으로 안전하다.
# GitHub 크론(30 23 * * 6 UTC = 08:30 KST 일요일)이 백업으로 남아 있으므로,
# 미니 트리거가 먼저 실행돼도 GitHub 크론이 나중에 실행해도 중복 발송이 없다.
elif [ "$hour" = "08" ] && [ "$min" = "30" ] && [ "$dow" = "7" ]; then
  run weekly.yml

else
  echo "$ts 해당 시각에 실행할 워크플로 없음 (hour=$hour min=$min dow=$dow)" >> "$LOG"
fi
