# 첫 화면(랜딩) 소스

read.wspace.ai.kr 첫 화면을 만드는 Next.js 프로젝트다. 정적 빌드한 `index.html`과 `_next/`를 저장소 루트로 복사해 배포한다.

- 빌드할 때 `../content/{en,ja}/*.json`을 읽어 지문 수, 오늘 주제, 첫 문장, 최근 지문을 HTML에 넣는다(검색엔진용).
- 매일 바뀌는 값은 publish.py가 쓰는 `/latest.json`을 화면이 읽어 갱신한다. 그래서 지문이 올라올 때마다 다시 빌드할 필요는 없다.
- 디자인을 고쳤을 때만 다시 빌드해 배포한다.

## 다시 배포하기

```bash
cd landing
npm ci
npm run build
bash scripts/deploy-landing.sh
```

`deploy-landing.sh`는 `out/index.html`과 `out/_next/`만 저장소 루트로 복사한다. 404.html 등 다른 파일은 건드리지 않는다. 복사한 뒤 루트의 `index.html`, `_next/`를 커밋한다.

## 구성

- `src/app/page.tsx`: 섹션 순서와 문구(이용 방법, 이번 주 지문, 서비스 한눈에 보기, 자주 묻는 질문, 구독)
- `src/components/`: Nav, Hero(폰, 조각, 구독 폼, 주제 띠), Week(이번 주 달력), Footer, Motion(스크롤 회전과 나타나기)
- `src/components/ref/latest.tsx`: latest.json 실시간 갱신과 `**단어**`, 후리가나 표기
- `src/lib/reading.ts`: 빌드 때 content JSON 읽기(publish.py `rebuild_root()`와 같은 규칙)
- 글꼴: 모두 Pretendard(cdnjs). 작은 라벨은 시스템 고정폭 글꼴
- 디자인 기준: `preview/c3-b2.html`
- 기본 강조색(확정): 파랑 `#2a52d4`, 누를 때 `#2143ad`. `src/app/globals.css`의 `--blue`, `--blue-h`. 바탕 `#ffffff`, 먹색 `#0a0a0a`, 보조 `#6b6b6b`, 구분선 `#e6e6e6`
