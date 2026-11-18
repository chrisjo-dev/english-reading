# 가입한 사람만 구독 (선착순 100명, 이후 대기 명단) 구현 계획

2026-11-18 사용자 결정
- 메일 구독은 가입한 사람만 한다. 로그인 없이 메일만 받는 길은 없앤다.
- 기존 Buttondown 구독자는 그대로 둔다(계속 받는다).
- 발송은 Buttondown 을 유지하고, Supabase profiles 를 기준으로 Buttondown 에 동기화한다.
- "선착순 100명 무료" 문구만 쓴다(남은 자리 숫자는 안 보인다). 100명이 차면 가입은 받고 메일은 대기 명단.
- 승인 시안: design/kakao-login K17, K20, K21, K22, K24, K25 (그리고 이 계획에 맞춘 문구 보정과 K26 마이페이지)

## 1. DB (supabase/migrations/0005_join_subscribe.sql)
- profiles 에 칸 추가
  - mail_lang text not null default 'en' check (en, ja, de), mail_level text not null default 'b' check (a, b): 클라이언트가 고칠 수 있다(칸 단위 GRANT update).
  - mail_wait boolean not null default false, mail_synced_at timestamptz: 서버(동기화)만 쓴다. 클라이언트 쓰기 권한 없음.
- public.mail_seats (id=1 한 줄: taken, cap=100, updated_at). RLS 켜고 anon, authenticated 에 select 만. 화면이 "다 찼는지"만 읽는다.
- 기존 트리거(dkh_profile_mail)는 그대로. mail_opt_at 은 켤 때마다 갱신된다.

## 2. 동기화 (tools/sync_members.py, .github/workflows/sync-members.yml, 매시 10분 + 수동)
- 비밀값: SUPABASE_SERVICE_ROLE_KEY(GitHub secret, 사용자가 넣음), BUTTONDOWN_API_KEY(있음).
- Buttondown 구독자 전체를 type 별(regular, unactivated, unsubscribed 등)로 읽어 이메일(소문자) 기준으로 묶는다.
- taken = regular + unactivated 수. cap = 100.
- 메일을 켠 가입자(mail_opt_in, email 있음)를 mail_opt_at 순서로:
  - Buttondown 에 regular/unactivated 로 있으면: metadata(lang, level, account="1")가 다를 때만 PATCH. mail_wait=false.
  - Buttondown 에서 unsubscribed 등(메일 하단 수신거부)이고 mail_opt_at <= mail_synced_at 이면: 사용자가 메일에서 끊은 것 → profiles.mail_opt_in=false 로 맞춘다.
    mail_opt_at > mail_synced_at 이면(동기화 뒤에 다시 켬): 자리가 있으면 collision add 로 다시 넣는다(확인된 주소는 regular, 아니면 unactivated 로 확인 메일).
  - 없으면: taken < cap 이면 POST(확인된 주소 = Google 은 type regular 로 확인 메일 없이, 카카오 직접 입력은 type 없이 = 확인 메일). taken += 1, mail_wait=false. 자리가 없으면 mail_wait=true(대기).
- 메일을 끈 가입자, 탈퇴로 profiles 에서 사라진 주소: Buttondown 에 metadata.account="1" 로 있으면 regular 는 unsubscribed 로, unactivated 는 삭제(해지 불가 타입).
  account 표시가 없는 기존 구독자는 건드리지 않는다.
- 바뀐 것만 쓴다(같은 주소를 짧은 시간에 넣었다 뺐다 하지 않게, 매시 한 번이라 마이페이지 스위치를 여러 번 눌러도 한 번만 반영).
- 끝에 mail_seats.taken 갱신. 실패하면 job 실패 → notify.yml 이 Slack 으로 알린다.

## 3. 화면
- 랜딩(landing/src HeroForm, SubFormsList): 이메일 칸을 "가입하고 아침 메일 받기" 버튼으로(K20). /join/?mail=1&lang=&level=. 로그인 상태면 /me/#mail. "선착순 100명 무료" 표시. 다 찼으면 대기 명단 안내.
- 지문 페이지 하단(tools/publish.py sub_html, data-v="4" 로 올려 patch_page 가 121쪽을 교체): K22 와 같다.
- /join/(join.js): mail=1 이면 K21(받을 메일 고르기, 메일 받기 체크). 고른 lang, level 을 dkh-next 에 같이 남긴다.
- /join/callback/: 메일을 골랐으면 profiles 에 mail_opt_in, mail_lang, mail_level 저장. 이메일 없으면(카카오) /join/email/, 있으면(Google) /join/done/.
- /join/email/: 저장 뒤 같은 자리에서 K25(받은편지함 확인) 안내.
- /join/done/(새 페이지, K24): 받을 메일과 주소. mail_seats 가 찼으면 대기 명단 문구.
- /me/: 메일 칸에 언어, 수준 고르기와 상태(대기 중, 확인 메일 대기) 표시(K26).

## 4. 검증
- python 단위: sync 결정 로직(신규, 기존, 수신거부, 다시 켬, 끔, 탈퇴, 자리 없음), sub_html v4, 계정 페이지 문구.
- 브라우저: 로컬 서버로 랜딩, 지문 페이지, /join/?mail=1, /join/done/, /me/ 를 390px 로 시안과 비교.
- 독립 리뷰(코드, 보안) 뒤 배포: 0005 적용(SQL Editor), main push, sync 워크플로 수동 1회 실행 결과 확인.
