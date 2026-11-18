# 로그인 설정 (카카오, Google)

> 2026-11-18 설정 완료: Supabase 프로젝트 `dokhaehanip`(lilyrang 조직, 서울, ref `kfprgssvigujxphfmlth`), 카카오 앱 "독해한입"(ID 1655290), Google Cloud 프로젝트 `dokhaehanip`(OAuth 클라이언트 "dokhaehanip web", 프로덕션 게시), Worker `dokhaehanip-api`(비밀값 2개). 공개값은 `assets/auth.js`에 들어 있습니다.

코드는 `feat/login` 브랜치에 있습니다. `assets/auth.js`의 설정 값이 비어 있으면 로그인 기능이 꺼진 채로 동작합니다. 이때는 문제 풀기도 잠그지 않습니다. 그래서 아래 설정을 끝내기 전에 배포해도 사이트는 지금과 같습니다. 다만 메인의 "03 / 단어 연습" 섹션은 바로 보이므로, 메인(index.html)은 설정을 마친 뒤에 올립니다.

비밀 키(카카오 Client Secret, Google Client Secret, Supabase service role 키, DB 비밀번호)는 채팅에 붙이지 말고 아래에 적은 곳에 직접 넣어 주세요.

## 1. Supabase 프로젝트

1. https://supabase.com/dashboard 에서 `lilyrang` 조직 또는 새 조직에 프로젝트를 만듭니다. 이름 `dokhaehanip`, 지역 Seoul(ap-northeast-2).
   - 무료 플랜은 조직마다 활성 프로젝트 2개까지입니다.
2. SQL Editor에서 `supabase/migrations/0001_init.sql`을 실행합니다.
3. Project Settings > API에서 Project URL과 anon(publishable) 키를 확인합니다. 이 두 값은 공개해도 되는 값이라 `assets/auth.js`에 넣습니다.
4. Authentication > URL Configuration:
   - Site URL: `https://dokhaehanip.com`
   - Redirect URLs: `https://dokhaehanip.com/join/callback/`
5. Authentication > Providers:
   - Email은 끕니다.
   - Kakao를 켭니다. REST API 키와 Client Secret을 넣습니다. 이 단계는 id_token 검증에 쓰입니다.
   - Google을 켭니다. 3번에서 만든 Client ID와 Client Secret을 넣습니다.

## 2. 카카오 앱

1. https://developers.kakao.com 에서 앱 "독해한입"을 만듭니다. 비즈 앱은 필요 없습니다.
2. 카카오 로그인을 켜고 OpenID Connect도 켭니다.
3. 동의 항목은 닉네임(profile_nickname)만 받습니다. 이메일과 프로필 사진은 받지 않습니다.
4. 플랫폼 Web 사이트 도메인: `https://dokhaehanip.com`
5. Redirect URI: `https://dokhaehanip.com/join/callback/`
6. 보안에서 Client Secret을 켭니다.
7. REST API 키는 `assets/auth.js`의 `kakaoClientId`에 넣습니다. 이 키는 공개값입니다.

## 3. Google OAuth

1. Google Cloud Console > APIs & Services > OAuth consent screen에서 External로 만듭니다.
   - 앱 이름: 독해한입
   - 범위: openid, email, profile
   - 승인된 도메인: dokhaehanip.com, supabase.co
2. Credentials > OAuth client ID(Web application)를 만듭니다.
   - 승인된 리디렉션 URI: `https://<프로젝트 ref>.supabase.co/auth/v1/callback`
3. 받은 Client ID와 Client Secret을 Supabase Google provider에 넣습니다.
4. 게시 상태를 "프로덕션"으로 바꿉니다. 테스트 상태에서는 등록한 테스트 사용자만 로그인할 수 있습니다.

## 4. API Worker (api.dokhaehanip.com)

카카오 토큰 교환에만 씁니다. Google은 Supabase가 직접 처리합니다.

```bash
cd worker
npx wrangler secret put KAKAO_REST_API_KEY
npx wrangler secret put KAKAO_CLIENT_SECRET
npx wrangler deploy
```

dokhaehanip.com DNS는 Cloudflare에 있습니다(2026-11-18 확인). 첫 배포 때 `api.dokhaehanip.com` 레코드와 인증서가 만들어집니다.

## 5. 값 넣고 배포

1. `assets/auth.js` 맨 위 `CFG`의 `supabaseUrl`, `supabaseAnonKey`, `kakaoClientId`를 채웁니다.
2. `tools/drill.py`의 `AUTH_V`를 올리고, 날짜 페이지를 다시 만듭니다. 이렇게 해야 브라우저 캐시에 남은 빈 설정이 바뀝니다.
3. 테스트를 돌립니다.
   - `python -m pytest -q tests`
   - `node --test tests/auth.test.mjs worker/kakao.test.mjs`
4. 브라우저에서 카카오와 Google 로그인을 한 번씩 해 봅니다.

## 가입자 수 보기

Supabase SQL Editor에서 다음을 실행합니다.

```sql
select count(*) from public.profiles;                                   -- 전체 가입자
select provider, count(*) from public.profiles group by 1;               -- 카카오, Google 별
select date(created_at), count(*) from public.profiles group by 1 order by 1;  -- 날짜별 가입
select name, count(*) from public.events where at > now() - interval '7 days' group by 1;  -- 잠금 노출, 클릭, 가입
```
