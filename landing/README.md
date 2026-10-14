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

- `src/app/page.tsx`: 섹션 순서와 문구(이용 방법, 서비스 한눈에 보기, 자주 묻는 질문)
- `src/components/ref/`: 헤더, 첫 화면, 서막, 장(Chapter), 푸터, 실시간 갱신(latest)
- `src/lib/reading.ts`: 빌드 때 content JSON 읽기
- 글꼴: Inter Tight, JetBrains Mono(next/font), 한글은 Pretendard(cdnjs)
