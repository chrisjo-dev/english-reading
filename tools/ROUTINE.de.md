# 매일 독일어 읽기: 생성 절차 (독일어, de)

예약 작업이 매일 아침 이 파일을 읽고 따른다. 대상은 CEFR B1~B2 수준의 한국인 독일어 학습자이고, 설명과 뜻은 모두 한국어로 쓴다.

## 난이도 규칙 (매우 중요)
- **중급(main) 지문**: B1 위주 + B2 1~2문장. 문장은 정확히 6개, 한 문장은 **15~22단어**(공백 기준).
  - B1 특징: Nebensätze(weil, dass, obwohl, wenn), 분리동사(Verbklammer), 수동태(wird gebacken), 형용사 변화.
  - B2 표시(`"b2": true`): 아래 기능 중 하나가 **반드시** 포함되어야 한다.
    - **Konjunktiv II**: `würden ... vorziehen`, `könnte sich ... verwischen`, `wäre kaum möglich`처럼 würde/könnte/hätte/wäre를 실제로 사용해야 한다. `obwohl`(B1) 단독은 B2가 아니다.
    - **Passiv mit Modalverb**: `können ... erworben werden`, `müssen ... beachtet werden`처럼 Modalverb+Partizip II+werden.
    - **Partizipialattribute**: `das von Millionen täglich genutzte Netz`처럼 분사가 관사와 명사 사이에서 긴 수식어로 사용.
    - **je...desto**: `Je mehr ... verschiebt, desto stärker ... müssen`.
    - **sowohl...als auch**: `sowohl ein Bußgeld als auch den Ärger`.
    - **erweiterte Relativsätze**: 관계절 안에 전치사구/부사구가 추가된 복합 구조.
    - **Nominalstil**: 동사 대신 파생 명사를 쓰는 문장(`die Einführung ... führte zu`).
    - **um...zu + 복잡한 목적어**: `um die heimische Landwirtschaft zu unterstützen und frischere Waren zu bekommen`.
  - Konjunktiv II는 1~2문장에만 사용하고 모든 문장에 쓰지 않는다.
- **기초(levels.a) 지문**: A2~B1. 중급과 같은 주제·사실을 1:1로 다시 씀. 문장을 짧게(**8~14단어**), 단순 구조(주어+동사+목적어/부사)로. Nebensatz는 최소화.
  - **굵은 글자(bold) 규칙**: 중급 문장에서 굵게 표시한 단어(`**단어**`)를 기초 문장에서도 A2~B1 수준에 맞으면 그대로 유지한다. 해당 단어가 기초 수준에 어색하거나 없어서 다른 표현을 써야 할 때에 한해 더 쉬운 동의어를 대신 굵게 표시한다. 굵은 단어를 아예 생략하지 않는다.
- 문체는 표준 독일어(Hochdeutsch). 방언, 구어체 축약 금지.
- 스스로 난이도를 올리지 않는다.

## 독일어 정서법 (매우 중요)
- **명사 대문자**: 독일어 정서법 그대로 유지.
- **Umlaut/ß**: 그대로 표기(ä, ö, ü, ß). 대체 표기(ae, oe, ue, ss 등) 금지.
- **관사**: 명사는 알맞은 정관사(der/die/das)나 부정관사(ein/eine)와 함께.
- **격변화(Kasus)**: Nominativ/Akkusativ/Dativ 격을 문맥에 맞게 정확히.

## 끊어 읽기(chunks) 규칙 (중급/기초 모두 필수)
독일어 어순에 따라 아래 경계에서 끊는다.
- 주어부(Subjekt), 정동사(Verb), 목적어/보어(Objekt/Prädikativ), 부사구(Adverbial), 분리 전철/종결 동사(Verbklammer)
- 접속사(weil, dass, obwohl, wenn, aber, und) 앞에서 끊는다.
- 뜻은 직독직해(독일어 어순 그대로 앞에서부터)로 짧게.

예시:
- "Ich gehe heute mit meiner Familie in den Park." →
  `[["Ich", "나는"], ["gehe", "간다"], ["heute", "오늘"], ["mit meiner Familie", "가족과 함께"], ["in den Park.", "공원에"]]`
- "Er kauft jeden Morgen **Brötchen**, weil er sie gern isst." →
  `[["Er kauft", "그는 산다"], ["jeden Morgen", "매일 아침"], ["**Brötchen**,", "빵을"], ["weil er sie gern isst.", "왜냐하면 그가 그것을 좋아하기 때문에"]]`

## 오늘의 소재 정하기 (지문을 쓰기 전에 수행)

**최근 내용 겹치지 않기**: 고르기 전에 아래 명령으로 최근 14편의 주제와 본문을 확인한다.
`python3 -c "import json,glob; [print(p[-15:-5], json.load(open(p)).get('topic'), '|', ' '.join(s['en'] for s in json.load(open(p))['sentences'])[:200]) for p in sorted(glob.glob('content/de/*.json'))[-14:]]"`

1. **오늘의 분야와 글의 형태** (Asia/Seoul 기준 요일):
   - 월: 일상생활 (쇼핑, 교통, 식사)
   - 화: 독일어권 문화 (음식, 축제, 도시)
   - 수: 사회/쉬운 뉴스 (독일, 오스트리아, 스위스 소식)
   - 목: 일과 학교
   - 금: 과학과 자연
   - 토: 여행과 장소
   - 일: 계절과 날씨
   `category` 값: 생활/문화/여행은 `culture`, 사회는 `society`, 과학과 자연은 `science`, 기술은 `tech`, 미래는 `future`, 우주는 `space`.
2. **수요일 뉴스**: WebSearch로 최근 독일어권 소식을 찾는다. 원문 문장을 옮기지 말고, 확인한 사실 2~3개로 새로 쓴다. 이때만 `source`를 채운다.
3. **그 밖의 요일**: 실제 사실을 지어내지 않는 일반적인 생활 글. 특정 가게, 사람, 구체적 수치를 실제인 것처럼 쓰지 않는다. `source`는 `null`.
4. **무거운 소식 금지**: 재난, 사망, 전쟁, 정치 갈등 금지.

## 매일 생성할 형식 (content JSON 필드)

### 중급(main) 지문 필드
1. **지문** `sentences`: 6문장. 주요 단어는 `**…**`로 표시. B2 문장 1~2개에 `"b2": true`(B2 배지 표시).
2. **끊어 읽기** `chunks`: 모든 문장에 필수. 덩어리를 공백 하나로 이으면 `en`과 정확히 같아야 한다(`**` 표시 포함).
3. **주요 단어** `words`: 5~7개. `["Umwelt", "환경"]` 형태. 뜻에 그 단어나 변형(관사+명사, 복수형)을 다시 쓰지 않는다. 단어 쓰기 문제 힌트에 답이 보이기 때문이다. 관사는 관사만 적는다. 예: `["Ufer", "물가, 호숫가 (중성 das)"]` (O), `["Ufer", "물가, 호숫가 (das Ufer)"]` (X). `check_content.py`가 잡는다.
4. **체크 포인트** `points`: 1~2개. 그날 지문에 실제로 나온 문법을 한국어로 짧게 설명. 지문 표현은 `` `…` ``로 감싼다.
5. **모범 해석** `answers`: 6개. 문장 순서대로 자연스러운 한국어 해석.
6. **한 단계 위 어휘** `advanced`: **반드시 6~8개**. B2 수준 단어, 한국어 뜻, 혼동 주의(없으면 `null`), 예문(`**…**`), `example_ko`.
7. 기타: `topic`(한국어 주제어 2~8자), `title_ko`, `headline`(A2 수준 짧은 독일어 제목), `chips`(`["6문장", "B1 위주", "B2 1문장", "약 4분"]`), `date`, `category`.
   - `photo_scene`: FLUX.1 로 썸네일 사진을 생성할 장면 설명 **(선택 사항)**. 영어 한 문장, 40~300자. 구체적이고 시각적인 장면으로 쓰고 글자나 간판이 보이는 장면은 피한다. 예: `"A baker in an apron placing a freshly baked loaf of bread on a wooden counter inside a traditional German bakery."` 이 필드가 있으면 맥 미니 LaunchAgent 가 발행 직전에 FLUX.1 사진을 생성해 `content/de/YYYY-MM-DD.photo.jpg` 로 커밋한다.

### 기초(levels.a) 지문 필드
`levels.a`는 중급 지문과 1:1로 대응하는 6개 문장이다.
- `sentences`: 중급의 각 문장을 A2~B1 수준으로 다시 씀. 순서와 핵심 정보는 유지. `**볼드**`는 같은 단어에 유지.
- `chunks`: 기초 문장에도 필수.
- `answers`: 기초 문장 6개의 한국어 해석.
- `words`, `points`, `advanced`, `source`는 중급과 공유(levels.a 안에 없음).

### 생성 예시 (형식 참고용)
중급 문장: `"Obwohl viele Ketten **Brot** günstiger verkaufen, kaufen viele Kunden ihr Brot lieber beim lokalen Bäcker."`
- b2: true
- chunks: `[["Obwohl viele Ketten", "많은 체인이"], ["**Brot** günstiger verkaufen,", "빵을 더 저렴하게 팔지만"], ["kaufen viele Kunden", "많은 고객들은 산다"], ["ihr Brot lieber", "빵을 더 좋아서"], ["beim lokalen Bäcker.", "동네 빵집에서"]]`

기초 문장: `"Viele Kunden kaufen ihr **Brot** beim lokalen Bäcker."`
- chunks: `[["Viele Kunden", "많은 고객들은"], ["kaufen", "삽니다"], ["ihr **Brot**", "빵을"], ["beim lokalen Bäcker.", "동네 빵집에서"]]`

## 결과물 만들기와 올리기

작업 디렉터리는 `chrisjo-dev/english-reading`의 clone(main 브랜치). 날짜는 Asia/Seoul 기준 오늘 `YYYY-MM-DD`. **반드시 맨 먼저 `TZ=Asia/Seoul date +%F`를 실행해 그 결과를 오늘 날짜로 쓴다.**

1. **이미 올라간 날인지 확인**: `content/de/YYYY-MM-DD.json`이 있으면 새로 만들지 말고 끝낸다.
2. **content JSON 쓰기**: 중급(`sentences`, `levels.a`)을 포함해 위 형식 그대로 `content/de/YYYY-MM-DD.json`을 쓴다.
3. **검증**: `python3 tools/render.py de YYYY-MM-DD` → `python3 tools/check_content.py de YYYY-MM-DD`. `::error`가 나오면 JSON을 고쳐 다시 실행.
4. **확인 후 되돌리기**: `git checkout -- . && git clean -fd -- de/YYYY-MM-DD`로 생성 파일 삭제, content 파일만 유지.
5. **push**: `git add content/de/YYYY-MM-DD.json && git -c user.name="chrisjo" -c user.email="wonsang.dev@gmail.com" commit -m "Add de YYYY-MM-DD: 주제어 Refs #9" && git push origin HEAD:main`. 커밋 메시지에 Co-Authored-By 줄 금지.
6. **마지막 답변**: 한두 문장과 페이지 주소 `https://read.wspace.ai.kr/de/YYYY-MM-DD/`. 실패하면 원인 명시.

## 주의사항
- 음성(TTS)이 없는 날에는 페이지가 브라우저 내장 SpeechSynthesis(de-DE)로 동작.
- 이미 발행한 날의 지문 문장을 고치면 그 날짜의 `de/<날짜>/audio/` 음성을 지워 다시 만들게 한다. 음성마다 만든 문장 기록(`.text.json`)이 있으면 바뀐 것만 자동으로 다시 만들지만, 기록이 없는 옛 음성은 그대로 믿기 때문이다.
- 2026-10-30 공식 공개: `noindex: false`, `email: true`. 검색엔진, 사이트맵, 첫 화면, 언어 탭에 나오고 구독자에게 메일이 간다.
- 발행 후 페이지 `https://read.wspace.ai.kr/de/YYYY-MM-DD/`를 직접 열어 중급/기초 전환, chunks, 번역 토글을 확인.
