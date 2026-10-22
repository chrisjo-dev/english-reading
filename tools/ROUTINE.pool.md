# 비축분(pool) 보충 절차

비상 발행 시스템이 pool 파일을 꺼내 쓴다. pool 이 소진되면 당일 발행이 중단된다.
매주 1회(또는 비상 발행 이슈가 올라온 뒤) 이 절차를 따라 보충한다.

작업 디렉터리는 `chrisjo-dev/english-reading` 저장소(main 브랜치)의 clone 이다.

---

## 1. 현재 pool 상태 확인

```bash
ls pool/en/ | grep -v .gitkeep | wc -l   # 영어 비축 파일 수
ls pool/ja/ | grep -v .gitkeep | wc -l   # 일본어 비축 파일 수
```

각 언어 목표는 **14개**다. 14개 미만이면 부족한 만큼 생성하되, 한 번에 최대 3개씩 만든다.

---

## 2. 기존 pool 과 recent content 주제 파악

중복 방지를 위해 아래 두 곳의 주제(`topic` 필드)를 확인한다.

```bash
python3 -c "
import json, sys
from pathlib import Path

root = Path('.')
for p in sorted(root.glob('pool/*/*.json')):
    c = json.loads(p.read_text())
    print(f'pool  {p.parent.name}  {p.name}  {c.get(\"topic\",\"?\")}')
"
```

```bash
python3 -c "
import json, datetime
from pathlib import Path

cutoff = datetime.date.today() - datetime.timedelta(days=90)
for p in sorted(Path('content').glob('*/*.json')):
    try:
        d = datetime.date.fromisoformat(p.stem)
    except ValueError:
        continue
    if d >= cutoff:
        c = json.loads(p.read_text())
        print(f'content {p.parent.name} {p.stem} {c.get(\"topic\",\"?\")}')
" | sort
```

---

## 3. 지문 생성 규칙

ROUTINE.md(영어) 와 ROUTINE.ja.md(일본어)의 **난이도, 형식, 후리가나 규칙**을 그대로 따른다.
단, 다음 항목은 pool 지문에 **적용하지 않는다**:

- 오늘의 날짜, 요일, 뉴스 검색
- `date` 필드는 반드시 `""` (빈 문자열)로 둔다

**주제 선정 기준:**
- 위에서 확인한 pool 과 최근 content 의 주제와 겹치지 않는다
- 시사, 특정 날짜, 계절에 종속되지 않는 **에버그린(evergreen) 주제**로 쓴다
  - 예: 수면, 식물, 도서관, 우편, 자전거, 화산, 산호초, 조수, 우주탐사 일반론
  - 피해야 할 것: "이번 주 발표된 연구", 특정 올림픽, 선거, 재난

**끊어 읽기(영어만):**
- 영어 비축분은 모든 문장에 `chunks`를 넣는다. 없으면 `check_content.py --pool`이 오류를 낸다. 일본어 비축분에는 넣지 않는다.
- 규칙은 ROUTINE.md 의 `sentences[].chunks` 설명과 같다: 보통 2~6단어씩 구와 절의 경계에서 끊고, `**단어**` 표시는 한 덩어리 안에 두며,
  덩어리를 공백 하나로 이으면 문장(`en`)과 정확히 같아야 한다. 뜻은 영어 순서대로 읽는 짧은 한국어(직독직해)로 쓴다.
- 예: `{"en": "Fireflies use their flashes mainly to find a **partner**.", "b2": false, "chunks": [["Fireflies use their flashes", "반딧불이는 깜박임을 쓴다"], ["mainly to find a **partner**.", "주로 짝을 찾으려고"]]}`

**기초 수준 병행 지문(영어만):**
- 영어 비축분은 `levels.a` 필드도 넣는다. 없으면 `check_content.py --pool`이 오류를 낸다. 일본어 비축분에는 넣지 않는다.
- 규칙은 ROUTINE.md 의 `levels` 필드 설명과 같다: main 과 동일한 수의 문장(1:1 대응), 각 문장 약 15단어 이하, A2~B1 수준, 능동태 위주, 사실/이름/수치 유지, main 의 `**형광펜**` 단어는 자연스러우면 유지. chunks 는 항상 필수.

**사실 확인:**
- 구체적 수치(숫자, 비율)를 넣으려면 검색으로 출처를 확인하고 `source` 에 넣는다
- 출처를 달기 어려운 지어낸 이야기라면 `"example": true` 를 넣는다

---

## 4. 파일 이름 규칙

```
pool/<언어>/<YYYY-MM-DD>.json
```

파일 이름의 날짜 = **오늘 날짜(KST)**. `fallback.py` 가 파일명 순(오래된 것부터)으로 꺼내므로,
일찍 만들어 둔 파일이 먼저 사용된다.

---

## 5. 검증

파일을 만든 뒤 반드시 아래 두 검증을 통과해야 한다.

```bash
# 1. 마크다운 오류, 출처 누락 수치, 영어 끊어 읽기(chunks) 검사
python3 tools/check_content.py --pool

# 2. render.py 로 HTML 생성 검사 (날짜는 임시값 사용, 생성 파일 정리)
TMPDAY="2099-12-31"
cp pool/en/<파일명>.json content/en/$TMPDAY.json
python3 tools/render.py en $TMPDAY && echo "ok"
rm -f content/en/$TMPDAY.json en/$TMPDAY/index.html
rmdir en/$TMPDAY 2>/dev/null || true
```

일본어도 같은 방법으로 검증한다(경로를 `ja` 로 바꾼다).

---

## 6. 커밋 및 push

pool 파일만 커밋한다. content/ 나 렌더링 결과물은 넣지 않는다.

```bash
git add pool/
git commit --author="chrisjo <wonsang.dev@gmail.com>" \
  -m "Add pool passages: <언어> <주제1>, <주제2>"
git push origin main
```

커밋 메시지에 Claude, AI, Generated 같은 AI 표기를 넣지 않는다.

새 비축분에도 `title_ko`와 `headline`을 넣는다. 형식은 `tools/ROUTINE.md`(영어), `tools/ROUTINE.ja.md`(일본어)의 필드 설명과 같다. 없으면 짧은 주제어가 제목으로 대신 쓰인다.
