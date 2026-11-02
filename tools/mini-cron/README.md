# 맥 미니 크론 트리거

GitHub Actions 예약 작업은 최대 1~2시간 지연될 수 있습니다. 맥 미니가 항상 켜져 있다면 LaunchAgent 로 정확한 시각에 워크플로를 직접 트리거할 수 있습니다. GitHub 크론은 백업으로 남겨 두므로 미니가 꺼진 날에도 발행이 끊기지 않습니다.

## 실행 일정

| 시각(KST) | 요일 | 워크플로 | 설명 |
|---|---|---|---|
| 07:15 | 매일 | `fallback.yml` | 예약 발행 누락 시 비축분 자동 발행 |
| 07:45 | 매일 | `fallback.yml` | 예비 슬롯(07:15 실행 후 이미 있으면 무시) |
| 08:00 | 매일 | `catchup.yml` | 아침 메일 미수신 구독자 보충 발송 |
| 08:30 | 일요일 | `weekly.yml` | 주간 단어 복습 메일 |

## 중복 실행 안전성

- **fallback.yml**: `process_lang` 이 그날 `content/<lang>/<day>.json` 이 있으면 EXISTS 를 반환해 아무것도 하지 않습니다. GitHub 크론이 나중에 실행해도 안전합니다.
- **catchup.yml**: `send_email.catchup` 이 이미 이벤트가 기록된 구독자를 건너뜁니다. 두 번 실행해도 중복 발송이 없습니다.
- **weekly.yml**: `send_email.send` 의 중복 발송 방지 로직(`same_issue`)으로 두 번 트리거해도 메일이 한 번만 나갑니다.

## 설치

### 1. 사전 조건

```bash
# gh 설치 (이미 있으면 건너뜀)
brew install gh

# GitHub 인증 (workflow 권한 필요)
gh auth login --scopes workflow

# 권한 확인
gh auth status
```

### 2. 스크립트 설치

```bash
# 실행 권한 부여
chmod +x ~/test/english-reading/tools/mini-cron/mini-cron.sh

# 스크립트 경로가 맞는지 확인
bash ~/test/english-reading/tools/mini-cron/mini-cron.sh
```

### 3. LaunchAgent 등록

```bash
# plist 복사 (YOURNAME 을 실제 사용자 이름으로 바꾼다)
cp ~/test/english-reading/tools/mini-cron/kr.wspace.english-reading-mini-cron.plist \
   ~/Library/LaunchAgents/

# plist 파일 안의 YOURNAME 을 실제 경로로 수정
# ProgramArguments 와 StandardOutPath/StandardErrorPath 두 곳

# 등록
launchctl load ~/Library/LaunchAgents/kr.wspace.english-reading-mini-cron.plist
```

### 4. 시간대 확인

맥 미니 시스템 설정 > 일반 > 날짜 및 시간 > 시간대를 **Asia/Seoul** 로 설정해야 KST 기준으로 실행됩니다.

### 5. PATH 설정

plist 는 로그인 쉘이 아닌 환경에서 실행되므로 `gh` 명령어를 못 찾을 수 있습니다. 스크립트 상단에 `/opt/homebrew/bin:/usr/local/bin` 이 포함돼 있습니다. `gh` 위치가 다르면 `which gh` 로 확인해 스크립트에 추가하세요.

## 확인 및 제거

```bash
# 로그 확인
tail -f ~/Library/Logs/english-reading-mini-cron.log

# 수동 테스트 (실제 워크플로를 trigger 하지 않으려면 gh 를 echo 로 대체)
bash ~/test/english-reading/tools/mini-cron/mini-cron.sh

# LaunchAgent 제거
launchctl unload ~/Library/LaunchAgents/kr.wspace.english-reading-mini-cron.plist
rm ~/Library/LaunchAgents/kr.wspace.english-reading-mini-cron.plist
```

## 비고

- GitHub 크론(`15 22 * * *`, `45 22 * * *` UTC)은 백업으로 유지합니다. 미니가 실행한 뒤 GitHub 크론이 늦게 실행해도 이미 컨텐츠가 있으므로 fallback 은 아무것도 하지 않습니다.
- weekly.yml 은 GitHub 크론(`30 23 * * 6` UTC = 일요일 08:30 KST)이 있어 미니 트리거가 없어도 발행됩니다. 미니가 먼저 실행해도 send 중복 방지 로직으로 안전합니다.
