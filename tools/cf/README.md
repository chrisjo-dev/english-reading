# 예전 주소 read.wspace.ai.kr 넘기기 (Cloudflare)

독해한입은 2026-11 에 `read.wspace.ai.kr` 에서 `dokhaehanip.com` 으로 옮겼다. 예전 주소로 오는 요청은 Cloudflare 에서 받아 새 주소로 보낸다.
전제는 wspace.ai.kr 네임서버가 Cloudflare 에 있고, `read` 레코드가 Proxied(주황 구름)인 상태다(docs 의 전환 계획 Phase 1, 2).

## 1. Worker (학습 기록까지 옮김, 2~4주 유지)

`read-redirect.js` 는 사람이 여는 HTML 페이지에는 작은 이동 페이지를 돌려준다. 이 페이지가 예전 주소의 localStorage
(단어 반복, 수준, 재생 속도, 주제 반응)를 읽어 `https://dokhaehanip.com/<경로>?<쿼리>#mig=<base64url(JSON)>` 로 옮기고,
새 주소의 머리 스크립트(`tools/migrate.py`)가 없는 키만 넣은 뒤 `#` 을 지운다. 봇, 이미지, 음성, xml, HEAD 같은 나머지 요청은 바로 301 이다.

배포(대시보드):
1. Workers & Pages → Create → Worker → 이름 `read-redirect` → Deploy 후 Edit code
2. `read-redirect.js` 내용을 그대로 붙여 넣고 Deploy
3. Worker → Settings → Domains & Routes → Add → Route: `read.wspace.ai.kr/*`, Zone: `wspace.ai.kr`
4. 확인
   ```bash
   curl -sI https://read.wspace.ai.kr/en/ | grep -i -E '^(HTTP|location)'          # HEAD: 301, location https://dokhaehanip.com/en/
   curl -s -H 'Accept: text/html' https://read.wspace.ai.kr/en/ | grep -c 'mig='    # 브라우저 HTML: 이동 페이지(1 이상)
   curl -sI -A Googlebot https://read.wspace.ai.kr/en/2026-11-12/ | grep -i location
   ```
   브라우저에서는 예전 주소에 기록이 있는 기기로 열어, 새 주소의 개발자 도구 Application → Local Storage 에 키가 들어왔는지 본다.

테스트: `node --test tools/cf/read-redirect.test.mjs` (Worker 핸들러 상태와 Location, 보내는 쪽과 받는 쪽 왕복).
받는 키를 바꾸면 `read-redirect.js` 의 KEYS, PREFIXES 와 `tools/migrate.py` 를 같이 바꾼다(`tests/test_migrate.py` 가 확인).

## 2. Redirect Rule (백업안, Worker 를 내린 뒤 계속 둠)

Rules → Redirect Rules → Create rule:

| 항목 | 값 |
|------|------|
| Rule name | `read to dokhaehanip` |
| If incoming requests match | Custom filter expression: `http.host eq "read.wspace.ai.kr"` |
| Then | Dynamic redirect |
| Expression | `concat("https://dokhaehanip.com", http.request.uri)` |
| Status code | 301 |
| Preserve query string | 끔 (`http.request.uri` 에 이미 쿼리가 들어 있다) |

Worker 경로가 있으면 Worker 가 먼저 응답한다. Worker 를 내리면 이 규칙이 모든 요청을 301 로 받는다.

## 3. 되돌리기

- Worker 만 내리기: Worker → Settings → Domains & Routes 에서 `read.wspace.ai.kr/*` 경로 삭제(규칙이 이어서 받는다).
- 예전 주소로 완전히 되돌리기: Redirect Rule 끄기, Worker 경로 삭제, `read` 레코드를 DNS only(회색)로 되돌린 뒤
  `CNAME` 파일을 `read.wspace.ai.kr` 로, `tools/langs.py` 와 `landing/src/lib/site.ts` 의 SITE 를 예전 주소로 바꾸는 새 커밋을 올리고 재생성한다.
