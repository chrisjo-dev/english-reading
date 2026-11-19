# 독해한입: 매일 외국어 읽기

한국인 학습자가 하루에 외국어 한 단락씩 읽게 돕는 사이트입니다(https://dokhaehanip.com). 매일 아침 새로 쓴 지문을 문장별 음성, 주요 단어, 모범 해석과 함께 올리고, 아침 메일을 신청한 가입자에게 메일로도 보냅니다.

| 언어 | 주소 | 수준 | 음성 |
|---|---|---|---|
| 영어 | `/en/YYYY-MM-DD/` | CEFR B1~B2, 기초 A2~B1 | Kokoro (af_heart) |
| 일본어 | `/ja/YYYY-MM-DD/` | JLPT N3, 기초 N4~N5 | VOICEVOX:冥鳴ひまり |
| 독일어 | `/de/YYYY-MM-DD/` | CEFR B1~B2, 기초 A2~B1 | Qwen3-TTS (Serena) |

- `/`는 첫 화면(랜딩)이고, `/<언어>/archive/`는 지난 지문, `/<언어>/review/YYYY-MM-DD/`는 일요일 주간 단어 복습입니다.
- 가입은 `/join/`, 마이페이지는 `/me/`입니다.
- 지문은 기사 문장을 옮기지 않고 새로 쓴 글입니다. 바탕이 된 기사는 각 페이지에 출처로 밝힙니다.

## 기술 스택

| 부분 | 쓰는 것 |
|---|---|
| 지문, 목록, 가입, 마이페이지 | Python(`tools/`)이 만드는 정적 HTML과 프레임워크 없는 JavaScript(`assets/`) |
| 첫 화면 | Next.js 15, React 19, TypeScript, Tailwind 4(`landing/`). 정적으로 내보내 루트에 복사 |
| 호스팅 | GitHub Pages(`CNAME`). main에 push하면 바로 실제 사이트에 반영 |
| 자동 발행 | GitHub Actions(`.github/workflows/`) |
| 음성 | Kokoro(onnx), VOICEVOX, Qwen3-TTS와 faster-whisper 검사, ffmpeg(`tools/audio.py`) |
| 썸네일 | 맥 미니 이미지 API(Tailscale)를 먼저 쓰고, 안 되면 OpenAI `gpt-image-1-mini`(`tools/thumb.py`) |
| 로그인, 회원 데이터 | Supabase(Auth, Postgres, RLS, Vault, pg_net). supabase-js는 CDN으로 불러옴(`assets/auth.js`) |
| 서버 | Cloudflare Worker `api.dokhaehanip.com`(`worker/`): 카카오 토큰 교환, 사이트 감시, 반응 저장 |
| 메일 | Buttondown(`tools/send_email.py`) |
| 알림, 측정 | Slack `#독해한입-알림`, Google Analytics, AdSense |
| 테스트 | pytest(`tests/*.py`), `node --test`(`tests/*.test.mjs`, `worker/*.test.mjs`) |

## 폴더

```
content/<언어>/YYYY-MM-DD.json   지문 원본(예약 작업이 씀). 페이지는 여기서 만든다
pool/                            예약 작업이 비었을 때 꺼내 쓰는 비축 지문
tools/                           페이지, 음성, 메일, 동기화 도구와 예약 작업 지침(ROUTINE*.md)
assets/                          브라우저 스크립트(auth, join, me, drill 등)와 그림
landing/                         첫 화면 소스(Next.js)
worker/                          API Worker
supabase/migrations/             DB 마이그레이션(0001부터 차례로). 계획 문서 PLAN-*.md
tests/                           단위 테스트
en/ ja/ de/ join/ me/ about/ …   생성된 페이지(손으로 고치지 않는다)
index.html, _next/               landing 빌드 결과(손으로 고치지 않는다)
```

## 흐름

**매일 발행**
1. 언어별 예약 작업이 `tools/ROUTINE.md`(영어), `tools/ROUTINE.ja.md`, `tools/ROUTINE.de.md`를 따라 `content/<언어>/YYYY-MM-DD.json`을 main에 push합니다.
2. `publish.yml`이 음성, 페이지(`tools/render.py`, `tools/publish.py`), 썸네일을 만들어 커밋합니다. 페이지가 실제로 열리면 그 언어 메일을 보냅니다. 독일어는 `de-audio.yml`이 음성을 먼저 만든 뒤 publish를 부릅니다.
3. 07:15(KST)까지 그날 지문이 없으면 `fallback.yml`이 `pool/`에서 꺼내 발행합니다.
4. 일요일 08:30(KST)에는 `weekly.yml`이 주간 복습 페이지와 메일을 만듭니다.

**가입과 아침 메일**
- 메일은 가입한 사람만 받습니다. 가입은 카카오(OpenID Connect, Worker가 토큰 교환)나 Google(Supabase OAuth, PKCE)로 합니다.
- 가입할 때나 마이페이지에서 받을 언어와 수준을 고르면 `profiles`에 저장됩니다. `sync-members.yml`이 매시 `tools/sync_members.py`로 Buttondown 구독자를 Supabase에 맞춥니다.
- 선착순 100명까지만 넣고 그 뒤는 대기 명단입니다(`mail_seats`). 가입 전부터 있던 Buttondown 구독자는 건드리지 않습니다.
- 메일 발송은 `send_email.release()`를 거칩니다. 24시간에 20통을 넘거나 같은 본문을 24시간 안에 다시 보내면 멈춥니다.

**사이트 반응**
- 지문 페이지의 "오늘 주제 어땠어요?", 언어 추가 요청, 기능 건의와 버그 제보 누름은 브라우저가 `sendBeacon`으로 Worker `/events`에 보냅니다(`tools/siteevent.py`, `landing/src/lib/event.ts`).
- Worker(`worker/events.js`)가 출처와 값을 검사하고 IP마다 1분 20번으로 제한한 뒤, 서비스 키로 `site_events`에 씁니다. 브라우저에는 이 표의 권한이 없습니다.
- 클릭과 화면 측정은 GA에만 남깁니다.

**알림**
- 새 가입은 DB 트리거(0004)가, 워크플로 실패는 `notify.yml`이, 사이트 다운은 Worker 감시(`worker/watch.js`)가 Slack으로 알립니다.

## DB(Supabase)

| 표 | 내용 | 브라우저 권한 |
|---|---|---|
| `profiles` | 닉네임, 로그인 방식, 메일 주소와 설정(`mail_*`) | 본인 행 읽기, 닉네임과 메일 설정 일부만 고치기 |
| `drill_state` | 단어 복습 기록 | 본인 행 읽기, 쓰기 |
| `events` | 로그인한 사람의 활동(가입, 로그인 등) | 본인 행 읽기, 쓰기 |
| `mail_seats` | 선착순 자리 수(한 줄) | 누구나 읽기 |
| `site_events` | 주제 반응, 언어 요청, 건의 누름. 익명 방문 번호만 남김 | 없음(Worker만 씀) |

- 마이그레이션은 `supabase/migrations/`의 SQL을 Supabase SQL Editor에서 차례로 실행합니다. 파일 끝에 되돌리는 방법을 적어 둡니다.
- 서버만 쓰는 칸(`mail_verified`, `mail_wait`, `mail_synced_at`)은 칸 단위 권한으로 막혀 있습니다.

## 개발

```bash
git config core.hooksPath .githooks      # push 전에 테스트를 돌린다(한 번만)
bash tools/test.sh                        # 단위 테스트 전부
python tools/check_content.py --all       # 지문 검사(ci 에서도 돈다)
```

- 페이지를 고칠 때는 생성된 HTML이 아니라 `tools/`를 고친 뒤 다시 만듭니다. 지난 페이지는 `publish.patch_page(lang, day)`와 `rebuild_lists(lang)`, 계정 페이지는 `rebuild_account_pages()`로 다시 만듭니다. 카드처럼 지난 페이지에 들어가는 조각은 `data-v` 버전을 올려야 다시 바뀝니다.
- 브라우저 스크립트를 고치면 `tools/publish.py`의 `ACCOUNT_V`를 올려 캐시를 넘깁니다.
- 첫 화면은 `cd landing && npm run build && bash scripts/deploy-landing.sh`로 빌드하고 루트에 복사합니다.
- 로컬 확인은 아무 정적 서버로 저장소 루트를 열면 됩니다(음성 탐색은 Range 요청을 받는 서버가 필요합니다).
- Worker는 `cd worker && npx wrangler deploy`로 배포합니다.

## 비밀값

저장소에는 넣지 않습니다.

| 어디 | 이름 |
|---|---|
| GitHub Actions | `BUTTONDOWN_API_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SLACK_WEBHOOK_URL`, `OPENAI_API_KEY`, `LOCAL_IMAGE_URL`, `LOCAL_IMAGE_TOKEN`, `TS_OAUTH_CLIENT_ID`, `TS_OAUTH_SECRET` |
| Worker(`wrangler secret put`) | `KAKAO_REST_API_KEY`, `KAKAO_CLIENT_SECRET`, `SLACK_WEBHOOK_URL`, `SUPABASE_SERVICE_ROLE_KEY` |
| Supabase Vault | `slack_webhook_url` |

브라우저 코드(`assets/auth.js`)에는 Supabase 주소와 공개(publishable) 키만 둡니다.

## 조심할 것

- main에 push하면 바로 배포됩니다. 아침 발행(05:50~08:30 KST) 시간에는 push를 피합니다.
- 메일은 한 번 나가면 되돌릴 수 없습니다. 안내 메일(`announce.yml`)이나 다시 보내기(`resend.yml`)는 손으로만 돌립니다.
- Buttondown은 짧은 시간의 대량 발송, 구독과 해지 반복을 자동 검사로 잡아 계정을 막습니다. 발송 장치(`release`)와 매시 한 번 동기화는 그래서 있습니다.
