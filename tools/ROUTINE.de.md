# 매일 독일어 읽기: 생성 절차 (독일어, de)

예약 작업이 매일 아침 이 파일을 읽고 따른다. 대상은 Goethe A2~B1 수준의 한국인 독일어 학습자이고, 설명과 뜻은 모두 한국어로 쓴다.

## 난이도 규칙 (매우 중요)
- 지문은 **A2 위주 + B1 1~2문장** 정도로 쓴다. 문장은 4~6개, 한 문장은 짧게(대략 12~18단어).
- 문체는 표준 독일어(Hochdeutsch)로 통일한다. 방언, 구어체 축약, 경어(존댓말식 과도한 표현)는 쓰지 않는다.
- 어휘는 A2~B1 범위에서 고르고, 주제에 꼭 필요한 B1 이상 단어는 지문당 1~2개까지만 쓰며 반드시 주요 단어(`words`)에 넣는다.
- 스스로 난이도를 올리지 않는다.

## 독일어 정서법 (매우 중요)
- **명사 대문자**: 독일어 정서법 그대로 유지. 지문에서 명사 첫 글자 대문자를 바꾸지 않는다.
- **Umlaut/ß**: 그대로 표기(ä, ö, ü, ß). 대체 표기(ae, oe, ue, ss 등) 금지.
- **관사**: 명사는 반드시 알맞은 정관사(der/die/das)나 부정관사(ein/eine)와 함께 쓴다. 오류 없이.
- **격변화(Kasus)**: Nominativ/Akkusativ/Dativ 격을 문맥에 맞게 정확히 쓴다.

## 끊어 읽기(chunks) 규칙 (모든 문장에 필수)
독일어 어순이 영어와 다르므로 아래 경계에서 끊는다.
- 주어부(Subjekt), 정동사(Verb), 목적어/보어(Objekt/Prädikativ), 부사구(Adverbial), 분리 전철/종결 동사(Verbklammer)
- 접속사(weil, dass, obwohl, wenn, aber, und) 앞에서도 끊는다.
- 뜻은 직독직해 순서(독일어 어순 그대로 앞에서부터 이해)로 짧게 쓴다.

예시:
- "Ich gehe heute mit meiner Familie in den Park." →
  chunks: `[["Ich", "나는"], ["gehe", "간다"], ["heute", "오늘"], ["mit meiner Familie", "가족과 함께"], ["in den Park.", "공원에"]]`
- "Er kauft jeden Morgen **Brötchen**, weil er sie gern isst." →
  chunks: `[["Er kauft", "그는 산다"], ["jeden Morgen", "매일 아침"], ["**Brötchen**,", "빵을"], ["weil er sie gern isst.", "왜냐하면 그가 그것을 좋아하기 때문이다"]]`

## 오늘의 소재 정하기 (지문을 쓰기 전에 수행)

**최근 내용 겹치지 않기**: 고르기 전에 `python3 -c "import json,glob; [print(p[-15:-5], json.load(open(p)).get('topic'), '|', ' '.join(s['en'] for s in json.load(open(p))['sentences'])[:200]) for p in sorted(glob.glob('content/de/*.json'))[-14:]]"`로 최근 14편의 주제와 본문을 읽습니다.

1. **오늘의 분야와 글의 형태** (Asia/Seoul 기준 요일):
   - 월: 일상생활 (쇼핑, 교통, 식사)
   - 화: 독일어권 문화 (음식, 축제, 도시)
   - 수: 사회/쉬운 뉴스 (독일, 오스트리아, 스위스 소식)
   - 목: 일과 학교
   - 금: 과학과 자연
   - 토: 여행과 장소
   - 일: 계절과 날씨
   `category` 값: 생활/문화/여행은 `culture`, 사회는 `society`, 과학과 자연은 `science`, 기술은 `tech`, 미래는 `future`, 우주는 `space`.
2. **수요일 뉴스**: WebSearch로 최근 독일어권(독일, 오스트리아, 스위스) 소식을 찾는다. 원문 문장을 옮기지 말고, 확인한 사실(숫자, 날짜, 장소) 2~3개로 새로 쓴다. 이때만 `source`를 채운다.
3. **그 밖의 요일**: 실제 사실을 지어내지 않는 일반적인 생활 글로 쓴다. 특정 가게, 사람, 수치를 실제인 것처럼 쓰지 않는다. `source`는 `null`.
4. **무거운 소식 금지**: 재난, 사망, 전쟁, 정치 갈등은 피한다.

## 매일 생성할 형식 (content JSON 필드)
1. **지문** `sentences`: 4~6문장. 주요 단어는 `**…**`로 표시(명사는 관사 없이 단어만). B1 문장 하나에 `"b2": true`(사이트에 B1 배지로 보인다).
2. **끊어 읽기** `chunks`: 모든 문장에 필수. 위 chunks 규칙에 따라 `[["독일어 덩어리", "한국어 뜻"], ...]` 형태. 덩어리를 공백 하나로 이으면 `en` 필드와 정확히 같아야 한다(`**` 표시 포함).
3. **주요 단어** `words`: 5~7개. `["Umwelt", "환경"]`처럼 독일어 + 한국어 뜻.
4. **체크 포인트** `points`: 1~2개. 그날 지문에 실제로 나온 문법을 한국어로 짧게 설명한다. 명사 성(der/die/das), 격변화(Kasus), 분리동사(trennbare Verben), 문장 끝 동사 위치(Verbstellung), 복합 명사 가운데서 고른다. 지문 표현은 `` `…` ``로 감싼다.
5. **모범 해석** `answers`: 문장 순서대로 자연스러운 한국어 해석.
6. **한 단계 위 어휘** `advanced`: 6~8개. B1~B2 수준 단어, 한국어 뜻, 혼동 주의(없으면 `null`), 지문 내용을 그 단어로 바꿔 쓴 예문(해당 단어는 `**…**`), `example_ko`(예문의 한국어 해석).
7. 그 밖의 필드: `topic`(한국어 주제어 2~8자, 예: "독일 빵집"), `title_ko`(페이지와 메일 제목. "오늘은 ___ 이야기예요"에 들어갈 자연스러운 한국어 명사구), `headline`(제목 아래 작게 보이는 독일어 제목. A2 수준의 짧은 제목으로 새로 쓰기), `chips`(`["N문장", "A2 위주", "B1 1문장", "약 N분"]`), `date`, `category`.

### 생성 예시 (형식 참고용, 내용과 흐름은 따라 하지 말 것)
- 지문: `"Jeden Morgen kauft Maria frisches **Brot** beim Bäcker."`
- chunks: `[["Jeden Morgen", "매일 아침"], ["kauft", "산다"], ["Maria", "마리아는"], ["frisches", "신선한"], ["**Brot**", "빵을"], ["beim Bäcker.", "빵집에서"]]`
- 주요 단어: `["Brot", "빵"]`
- 체크 포인트: `{"title": "beim = bei + dem", "body": "`beim Bäcker`의 beim 은 전치사 bei 와 정관사 dem(Dativ, 남성)이 합쳐진 형태예요."}`
- 한 단계 위 어휘: `{"word": "Bäckerei", "meaning": "빵집", "confuse": null, "example": "Die **Bäckerei** um die Ecke öffnet um 7 Uhr.", "example_ko": "모퉁이의 빵집은 7시에 열어요."}`

## 결과물 만들기와 올리기

작업 디렉터리는 사이트 저장소 `chrisjo-dev/english-reading`의 clone입니다(main 브랜치). 날짜는 Asia/Seoul 기준 오늘 `YYYY-MM-DD`입니다. **반드시 맨 먼저 `TZ=Asia/Seoul date +%F`를 실행해 그 결과를 오늘 날짜로 쓰세요.**

1. **이미 올라간 날인지 확인**: `content/de/YYYY-MM-DD.json`이 이미 있으면 새로 만들지 말고 끝냅니다.
2. **content JSON 쓰기**: 위 형식 그대로 `content/de/YYYY-MM-DD.json`을 씁니다. 모든 문자열은 일반 텍스트(HTML 태그 금지). 명사 대문자와 Umlaut/ß 를 반드시 확인합니다.
3. **검증**: `python3 tools/render.py de YYYY-MM-DD`를 실행해 오류 없이 끝나는지 확인합니다. 그다음 `python3 tools/check_content.py de YYYY-MM-DD`를 실행합니다. `::error`가 나오면 JSON을 고쳐 다시 실행합니다.
4. **확인 후 되돌리기**: `git checkout -- . && git clean -fd -- de/YYYY-MM-DD`로 되돌린 뒤 content 파일만 남깁니다.
5. **push**: `git add content/de/YYYY-MM-DD.json && git -c user.name="chrisjo" -c user.email="wonsang.dev@gmail.com" commit -m "Add de YYYY-MM-DD: 주제어 Refs #9" && git push origin HEAD:main`. 커밋 메시지에 Co-Authored-By 같은 작성자 줄을 붙이지 마세요.
6. **마지막 답변**: 한두 문장과 페이지 주소 `https://read.wspace.ai.kr/de/YYYY-MM-DD/`. 실패했다면 원인을 분명히 적습니다.

## 주의사항
- 음성(TTS) 경로가 확정되지 않아 audio 파일이 없습니다. 페이지는 브라우저 내장 SpeechSynthesis(de-DE)로 동작합니다.
- Phase 1 동안 `noindex: true`, `email: false` 상태입니다. 검색엔진에 노출되지 않고, 메일도 발송되지 않습니다.
- 발행 후 페이지 `https://read.wspace.ai.kr/de/YYYY-MM-DD/`를 직접 열어 레이아웃, chunks, 번역 토글을 확인합니다.
