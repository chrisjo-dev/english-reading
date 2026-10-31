# 매일 영어 읽기: 생성 절차 (영어, en)

예약 작업이 매일 아침 이 파일을 읽고 따른다. 학습자 개인의 수준과 약점, 피드백 규칙은 예약 작업 지시문에 있다.

## 오늘의 소재 정하기 (지문을 쓰기 전에 수행)
매일 같은 느낌의 글이 되지 않도록, 그날의 실제 소식에서 출발해 분야와 글의 형태를 요일마다 바꿉니다.

1. **오늘의 분야와 글의 형태** (Asia/Seoul 기준 요일):
   - 월: 과학 · 뉴스 요약
   - 화: 기술 · 원리 설명 (어떻게 작동하는지)
   - 수: 사회 · 인물/현장 이야기
   - 목: 미래 · 찬반 의견 (장점과 우려를 함께)
   - 금: 과학 · 원리 설명
   - 토: 일상·문화 · 인물/현장 이야기
   - 일: 우주·미래 · 뉴스 요약
2. **검색**: WebSearch(ToolSearch로 불러오기, mode "standard")로 오늘 분야의 최근 1~2일 소식을 찾습니다. B1 수준으로 풀어 쓸 수 있고 흥미로운 소식 하나를 고릅니다. 재난·사망·전쟁·정치 갈등처럼 무거운 소식은 피합니다.
   **최근 내용 겹치지 않기**: 고르기 전에 `python3 -c "import json,glob; [print(p[-15:-5], json.load(open(p)).get('topic'), '|', ' '.join(s['en'] for s in json.load(open(p))['sentences'])[:300]) for p in sorted(glob.glob('content/en/*.json'))[-14:]]"`로 최근 14편의 주제와 본문을 읽습니다. 주제는 다시 나와도 됩니다. 다만 최근에 쓴 지문과 같은 기사, 같은 사건, 같은 설명(예: '고장 난 물건을 가져오면 봉사자가 고쳐 준다'를 또 설명하기)을 반복하면 안 됩니다. 같은 주제를 고른다면 새로 생긴 일에만 초점을 맞추고, 이미 설명한 배경은 다시 쓰지 않습니다.
3. **사실 확인**: 고른 소식의 원문 기사를 WebFetch로 열어(검색 결과에 나온 주소만 엽니다. 주소를 추측해 열면 승인 요청에 걸려 실행이 멈춥니다), 지문에 쓸 사실 2~4개(숫자, 시간, 누가 했는지)와 키워드 3~5개를 뽑습니다. 원문에서 확인한 숫자와 고유명사만 씁니다.
4. **새로 쓰기**: 기사 문장을 옮기지 말고, 뽑은 키워드와 사실로 지문을 처음부터 새로 씁니다. 고유명사(사람·기관·제품 이름)는 지문당 2개 이내. 난이도 규칙은 그대로 지킵니다.
5. **구조 다양화**: 아래 원샷 예시의 문장 구조(새 시설 소개 → 숫자 → take + 시간 → N more)를 따라 하지 마세요. 오늘의 글 형태에 맞게 시작 방식과 문장 흐름을 매번 다르게 씁니다. 약점 표현(take + 시간, N more, suggests that 등)도 매일 억지로 넣지 말고, 그날 소식에 자연스럽게 맞는 것만 씁니다. 체크 포인트도 그날 지문에 실제로 나온 약점으로 고릅니다.
6. **실패 시**: 검색이 안 되거나 알맞은 소식이 없으면 멈추지 말고, 오늘의 분야와 글 형태로 실제 사실을 지어내지 않는 일반적인 지문을 씁니다. 이 경우 마지막 답변에 "오늘은 검색 없이 만든 지문입니다"라고 한 줄 적습니다.
7. **출처**: content JSON의 `source`에 기사 제목과 URL을 넣고, 마지막 답변 끝에도 `출처: [기사 제목](URL)` 한 줄을 붙입니다.

## 매일 생성할 형식
1. **오늘의 지문** — 4~6문장 분량의 자연스러운 한 단락. 대부분 B1, B2 문장 1~2개 섞음. 주제는 "오늘의 소재 정하기"에서 고른 소식이고, 글의 형태는 그날 요일의 형태를 따름. 문장마다 번호를 붙이고, 주요 단어는 지문 안에서 형광펜으로 표시하고, B2 문장 끝에는 B2 배지를 붙임. 듣기, 복사, 내 해석 칸은 사이트 템플릿에 이미 있으므로 따로 만들지 않음.
2. **주요 단어** — 지문에서 걸릴 만한 단어 5~7개. 영어 + 한국어 뜻. 고빈도 단어(예: significantly)는 반드시 포함.
3. **오늘의 체크 포인트** — 위 약점 중 이 지문에서 특히 볼 1~2가지를 짧게 안내.
4. **먼저 해석해보세요** — 학습자가 직접 해석하도록 유도. 모범 해석은 문장 번호별로 `answers`에 넣음(사이트에서 접힌 칸에 들어감).
5. **한 단계 위 어휘** — 지문의 표현을 B2~C1 수준으로 바꿔 말할 때 쓰는 단어 6~8개. 영어 + 한국어 뜻 + 지문 내용을 그 단어로 바꿔 쓴 짧은 예문(해당 단어는 굵게). 비슷하게 생긴 단어와 혼동할 수 있으면 "혼동 주의"를 붙임. `advanced`에 넣음(사이트에서 접힌 칸에 들어감).

## 원샷 예시

### [생성 예시 — 오늘의 지문]
"The new electric bus started running in the city last month. It can carry up to sixty passengers, and it is much quieter than the old diesel buses. Although the batteries take three hours to charge, the city plans to add twenty more buses by next year."

### [생성 예시 — 주요 단어]
- **electric** — 전기의
- **passengers** — 승객들 (복수 -s 주의)
- **diesel** — 디젤, 경유
- **batteries** — 배터리들 (battery의 복수)
- **Although** — 비록 ~일지라도, ~에도 불구하고

### [생성 예시 — 오늘의 체크 포인트]
- 문장 끝 정보: "last month", "up to sixty passengers", "by next year" — 시간과 수량이 문장 끝에 몰려 있어요.
- "Although"로 시작하는 마지막 문장의 대조 구조에 주의.

### [생성 예시 — 모범 해석 (접힌 칸에 배치)]
"새 전기 버스가 지난달 그 도시에서 운행을 시작했다. 최대 60명의 승객을 태울 수 있고, 기존 디젤 버스보다 훨씬 조용하다. 배터리를 충전하는 데 세 시간이 걸리지만, 그 도시는 내년까지 버스를 스무 대 더 추가할 계획이다."

위 예시는 출력 형식(단어 목록, 체크 포인트, 해석, 피드백의 모양)을 보여주는 참고용일 뿐입니다. 예시 지문의 주제, 문장 구조, 흐름은 따라 하지 말고 매번 "오늘의 소재 정하기"에 따라 새로 쓰세요.

## 결과물 만들기와 올리기

작업 디렉터리는 사이트 저장소 `chrisjo-dev/english-reading`의 clone입니다(main 브랜치). 날짜는 Asia/Seoul 기준 오늘 `YYYY-MM-DD`입니다. **반드시 맨 먼저 `TZ=Asia/Seoul date +%F`를 실행해 그 결과를 오늘 날짜로 쓰세요.** 실행 알림이나 시스템 메시지에 적힌 시각은 UTC라서 새벽에는 하루 전 날짜가 됩니다. 그 날짜를 쓰면 안 됩니다. 요일도 `TZ=Asia/Seoul date +%a`로 정합니다.

1. **이미 올라간 날인지 확인**: `content/en/YYYY-MM-DD.json`이 이미 있으면 새로 만들지 말고, PushNotification으로 "오늘 지문은 이미 올라가 있어요: https://read.wspace.ai.kr/en/YYYY-MM-DD/"만 보내고 끝냅니다.
2. **content JSON 쓰기**: `tools/render.py` 맨 위 설명의 형식 그대로 `content/en/YYYY-MM-DD.json`을 씁니다.
   - `category`: 오늘 요일의 분야. 월·금 `science`, 화 `tech`, 수 `society`, 목 `future`, 토 `culture`, 일 `space`. 고른 소식이 그 분야와 너무 다르면 실제 내용에 맞는 값으로 바꿔도 됩니다.
   - `topic`: 한국어 주제어 하나(2~8자, 예: "핵시계", "수직 농장"). 썸네일과 지난 지문 목록에 쓰입니다.
   - `title_ko`: 페이지 제목과 메일 제목. "오늘은 ___ 이야기예요"의 빈칸에 들어갈 자연스러운 한국어 명사구로, 무엇에 대한 이야기인지 한눈에 알 수 있게 씁니다(예: "세상에서 가장 정확한 시계", "100세 어르신들의 생일 파티"). 줄임말이나 어색한 직역("부푼 행성")은 피합니다.
   - `headline`: 제목 아래 작게 보이는 영어 제목. 기사 제목을 옮기지 말고, 지문보다 쉬운 B1 수준의 짧은 제목을 새로 씁니다(예: "The Most Exact Clock in the World"). 관용구와 말장난은 쓰지 않습니다.
   - `chips`: `["N문장", "B1 위주", "B2 N문장", "약 N분"]`.
   - `sentences[].en`: 주요 단어는 `**단어**`로 감쌉니다. B2 문장은 `"b2": true`.
   - `sentences[].chunks`: 끊어 읽기 덩어리. 모든 문장에 넣습니다(2026-10-23부터 없으면 `check_content`가 오류를 냅니다). 형식은 `[["영어 덩어리", "짧은 한국어 뜻"], ...]`입니다.
     - 보통 2~6단어씩, 구와 절의 경계(주어, 동사, 목적어, 전치사구, 접속사, 관계사 앞)에서 끊습니다. 쉼표와 마침표는 앞 덩어리 끝에 붙입니다.
     - 덩어리를 공백 하나로 이으면 `en`과 글자 하나까지 같아야 합니다. `**단어**` 표시도 그대로 두고, 한 덩어리 안에서 열고 닫습니다.
     - 뜻은 영어 순서 그대로 앞에서부터 이해하는 직독직해로, 덩어리마다 짧은 한국어로 씁니다. 한국어 어순으로 뒤집어 문장 전체 해석을 나눠 넣지 않습니다.
     - 예: `"en": "**Supporters** say the service could save people a trip to the store."`이면 `"chunks": [["**Supporters** say", "지지하는 사람들은 말한다"], ["the service could save people", "그 서비스가 사람들에게 덜어 줄 수 있다고"], ["a trip to the store.", "가게에 가는 수고를"]]`
   - `words`: `[["영어", "한국어 뜻"], ...]` 5~7개. 뜻에 그 단어나 변형(원형 등)을 다시 쓰지 않습니다. 단어 쓰기 문제 힌트에 답이 보이기 때문입니다. 예: `["genes", "유전자들 (복수형)"]` (O), `["genes", "유전자들 (gene의 복수)"]` (X). `check_content.py`가 잡습니다.
   - `points`: 1~2개. `body` 안에서 지문 표현은 `` `표현` ``으로 감쌉니다.
   - `answers`: 문장 순서대로의 모범 해석.
   - `advanced`: 6~8개. `confuse`는 혼동 주의가 없으면 `null`, 있으면 "precious(소중한)와 혼동 주의" 형태. `example`의 해당 단어는 `**단어**`. `example_ko`는 `example` 문장의 자연스러운 한국어 번역(필수). 예: `"example_ko": "지지자들은 30분 안에 주문을 받을 수 있는 편리함을 칭찬합니다."`
   - `source`: 검색한 기사면 `{"title": "기사 제목 (매체, YYYY-MM-DD)", "url": "..."}`, 검색 없이 쓴 날은 `null`. 출처 없는 글은 페이지에 "특정 기사를 바탕으로 하지 않은 학습용 글"로 표시됩니다.
   - `photo_scene`: 맥 미니 이미지 API 로 썸네일 사진을 생성할 때 쓰는 장면 설명 **(선택 사항)**. 영어 한 문장, 40~300자. 구체적이고 시각적인 실제 장면을 묘사하고, 글자나 간판이 보이는 장면은 피한다. 예: `"A scientist in a white lab coat examining a glowing blue crystal under a microscope."` 이 필드가 있으면 발행 시 맥 미니 이미지 API(tools/image-api/server.py, Tailscale 경유)가 FLUX.1 사진을 생성해 썸네일에 쓴다. 없거나 API 가 응답하지 않으면 OpenAI API 폴백이나 일러스트를 쓴다.
   - `levels`: **기초(A 수준) 병행 지문**. 반드시 main 지문과 같은 수의 문장(1:1 대응)으로 씁니다. 없어도 발행은 가능하지만 기초 구독자에게 지문이 전달되지 않습니다. 가능하면 항상 작성합니다.
     형식: `{"a": {"sentences": [{"en": "...", "chunks": [...]}, ...], "answers": ["한국어 해석", ...]}}`
     작성 원칙:
     - **난이도**: A2~B1. 문장마다 약 15단어 이하. 자주 쓰는 단어, 능동태 위주, 짧은 절.
     - **사실/이름/숫자** 유지: main 지문의 사실, 고유명사, 수치는 그대로 씁니다.
     - **형광펜 단어**: main 지문에서 `**단어**`로 표시된 단어가 A 문장에 자연스럽게 들어가면 그대로 `**단어**` 표시를 유지합니다. 너무 어려운 단어는 생략하거나 문맥으로 설명할 수 있습니다.
     - **chunks**: main의 chunks 규칙과 동일. 덩어리를 공백으로 이으면 `en`과 정확히 같아야 하고, 한 덩어리 안에서 `**` 를 열고 닫습니다. 뜻은 직독직해로 씁니다. levels.a 의 chunks 는 **항상 필수**입니다.
     - **answers**: 각 A 문장의 자연스러운 한국어 해석. 문장 수와 일치.

     **원샷 예시** (main 1문장 → A 1문장):
     ```
     main:   "When sunlight enters the air, it hits tiny gas **molecules**, and these molecules **scatter** short blue waves in every direction much more than long red ones."
     level a: {"en": "Gas **molecules** in the air **scatter** blue waves in all directions.",
               "chunks": [["Gas **molecules** in the air", "공기 속 기체 분자들이"], ["**scatter** blue waves", "파란 파동을 흩뜨린다"], ["in all directions.", "모든 방향으로"]]}
     answer: "공기 속 기체 분자들이 파란 파동을 모든 방향으로 흩뜨린다."
     ```
   - 모든 문자열은 일반 텍스트로 씁니다(HTML 태그 금지).
3. **검증**: `python3 tools/render.py en YYYY-MM-DD`를 실행해 오류 없이 끝나는지 확인합니다. 오류가 나면 JSON을 고쳐 다시 실행합니다. 이 명령이 만든 HTML 파일은 커밋하지 않습니다(Actions가 다시 만듭니다). `git checkout -- . && git clean -fd -- en/YYYY-MM-DD` 로 되돌린 뒤 content 파일만 남깁니다.
   그다음 `python3 tools/check_content.py en YYYY-MM-DD`를 실행합니다. `::error`(화면에 그대로 보이는 마크다운 기호, 이은 글이 문장과 다른 chunks 등)가 나오면 JSON을 고쳐 다시 실행합니다. `::error`(최근 지문과 내용 겹침)가 나오면 새로 생긴 일에 초점을 맞춰 고쳐 쓰거나 다른 소식으로 다시 고릅니다. 겹친 채로 올리면 발행 단계에서 비축분으로 바뀝니다. `::warning`(출처 없이 구체적 수치)이 나오면 출처를 달거나 수치를 빼고, 학습용으로 지어낸 사례라면 JSON에 `"example": true`를 넣습니다(페이지에 "지어낸 이야기"라고 표시됩니다). `::error`(levels.a 오류)가 나오면 JSON의 `levels.a` 를 수정해 다시 실행합니다. levels.a 오류만 남고 해결이 어려우면 `levels` 키 전체를 제거하고 main 지문만 커밋합니다(levels.a 는 발행을 막지 않습니다).
4. **push**: `git add content/en/YYYY-MM-DD.json && git -c user.name="chrisjo" -c user.email="wonsang.dev@gmail.com" commit -m "Add YYYY-MM-DD: 주제어" && git push origin HEAD:main`. 커밋 메시지에 Co-Authored-By 같은 작성자 줄을 붙이지 마세요. 다른 브랜치로 push하지 마세요. push가 거절되면 `git pull --rebase origin main` 후 한 번만 다시 push합니다.
5. **알림**: PushNotification으로 짧게 알립니다. 예: "오늘의 영어 읽기(10/13, 주제: 핵시계)가 올라갔어요. 몇 분 뒤 열려요: https://read.wspace.ai.kr/en/YYYY-MM-DD/". 알림에는 지문 전문과 모범 해석을 넣지 않습니다.
6. **마지막 답변**: 한두 문장과 페이지 주소, 끝에 `출처: [기사 제목](URL)` 한 줄. 모범 해석은 답변에 노출하지 않습니다. push까지 실패했다면 원인과 함께 그 사실을 분명히 적고, 알림에도 "오늘 지문 올리기 실패"라고 적습니다.
