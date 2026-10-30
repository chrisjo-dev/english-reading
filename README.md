# 독해한입: 매일 외국어 읽기

한국인 학습자를 위한 하루 한 단락 외국어 읽기. 매일 아침 새로 쓴 지문과 문장별 음성, 주요 단어, 모범 해석을 올리고 구독자에게 메일로 보냅니다.

| 언어 | 주소 | 수준 | 음성 |
|---|---|---|---|
| 영어 | `/en/YYYY-MM-DD/` | CEFR B1~B2 | Kokoro (af_heart) |
| 일본어 | `/ja/YYYY-MM-DD/` | JLPT N3 (기초 N4~N5, 2026-10-29부터) | VOICEVOX:冥鳴ひまり |

- 첫 화면 `/`은 언어 선택, `/<언어>/archive/`는 지난 지문, `/<언어>/review/YYYY-MM-DD/`는 일요일 주간 단어 복습입니다.
- 지문은 기사 문장을 옮기지 않고 새로 쓴 글이며, 바탕이 된 기사는 각 페이지에 출처로 표기합니다.

## 흐름

1. 언어별 예약 작업이 `tools/ROUTINE.md`(영어) 또는 `tools/ROUTINE.ja.md`(일본어)를 따라 `content/<언어>/YYYY-MM-DD.json`을 main에 push합니다.
2. `.github/workflows/publish.yml`이 음성(`tools/audio.py`), 페이지(`tools/render.py`, `tools/publish.py`)를 만들어 커밋하고, 페이지가 열리면 그 언어 구독자에게 메일(`tools/send_email.py`)을 보냅니다.
3. `.github/workflows/weekly.yml`이 일요일 08:30(KST)에 언어별 주간 복습 페이지와 메일을 만듭니다.

언어별 설정은 `tools/langs.py`에 있습니다. 메일은 Buttondown 구독자의 `metadata.lang`으로 언어를 나눠 보냅니다.
