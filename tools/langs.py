"""언어별 설정. 새 언어를 추가할 때는 여기에 한 항목을 더하고 tools/ROUTINE.<code>.md 와 예약 작업을 만든다.

각 언어의 페이지는 /<code>/YYYY-MM-DD/, 내용은 content/<code>/YYYY-MM-DD.json 에 둔다.

언어별 플래그 (누락 시 기본값):
  email   — True: 구독자에게 메일 발송. False: 발송 차단 (숨김 운영 중).
  noindex — True: 검색엔진 noindex, 사이트맵/latest.json 에서 제외. False: 공개.
  chunks  — True: 끊어 읽기(chunks) 필수 및 렌더링. False: chunks 없음.
  levels  — True: levels.a 기초 지문 지원. False: 지원 안 함.
"""

LANGS = {
    "en": {
        "name": "영어",
        "site": "매일 영어 읽기",
        "level": "B1~B2",
        "hard_badge": "B2",              # 조금 어려운 문장(content 의 "b2": true)에 붙는 배지
        "intro": "매일 아침 새로 올라오는 B1~B2 영어 읽기예요.",
        "search_example": "satellite, 핵시계",
        "tts_lang": "en-US",             # 브라우저 내장 음성(대비책)
        "tts": "kokoro",                 # 음성 엔진: kokoro 또는 voicevox
        "voice": "af_heart",             # Kokoro 목소리
        "kokoro_lang": "en-us",
        "speed": 0.92,
        "credit": "",                    # 음성 엔진 사용 표기(페이지 하단)
        "copy_head": "나는 CEFR B1~B2 수준의 한국인 영어 학습자입니다. 아래는 오늘의 영어 읽기 연습 지문입니다.",
        "copy_weak": "자주 틀리는 부분(문장 끝의 시간, 수량 정보, 큰 숫자, 비슷하게 생긴 단어, 관사와 복수 -s, 숙어 의미)도 함께 짚어 주세요.",
        "head_extra": "",
        "tools_extra": "",
        "furi_btn": "",
        # 언어별 플래그
        "email": True,
        "noindex": False,
        "chunks": True,
        "levels": True,
    },
    "ja": {
        "name": "일본어",
        "site": "매일 일본어 읽기",
        "level": "JLPT N4~N5",
        "hard_badge": "N4",
        "intro": "매일 아침 새로 올라오는 JLPT N4~N5 일본어 읽기예요.",
        "search_example": "駅, 전철",
        "tts_lang": "ja-JP",
        # 일본어는 Kokoro 품질이 낮아 VOICEVOX 를 쓴다. 14 = 冥鳴ひまり(ノーマル). 이용 조건으로 크레딧 표기가 필요하다.
        "tts": "voicevox",
        "voice": 14,
        "speed": 0.9,
        "credit": "음성: VOICEVOX:冥鳴ひまり",
        "copy_head": "나는 JLPT N4~N5 수준의 한국인 일본어 학습자입니다. 아래는 오늘의 일본어 읽기 연습 지문입니다.",
        "copy_weak": "자주 틀리는 부분(조사 は・が・を・に・で, 동사 활용과 시제, 한자 읽기, 숫자와 조수사)도 함께 짚어 주세요.",
        # 지문은 일본어 글꼴로, 후리가나(<rt>)는 작게. 끄기 버튼은 템플릿 스크립트가 처리한다.
        "head_extra": '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@500;700&display=swap">\n'
                      "<style>.en, .adv .ex, .word .w, .adv .w { font-family: \"Noto Sans JP\", Pretendard, sans-serif; } "
                      ".en, .adv .ex { word-break: normal; line-break: strict; } .en { line-height: 2.2; } rt { font-size: 0.55em; font-weight: 500; color: var(--sub); }</style>",
        "tools_extra": "",
        "furi_btn": '\n      <button class="tool" id="furi" type="button" aria-pressed="true">후리가나 끄기</button>',
        # 언어별 플래그
        "email": True,
        "noindex": False,
        "chunks": False,
        "levels": False,
    },
    "de": {
        "name": "독일어",
        "site": "매일 독일어 읽기",
        "level": "B1~B2",
        "hard_badge": "B2",
        "intro": "매일 아침 새로 올라오는 B1~B2 독일어 읽기예요.",
        "search_example": "Umwelt, 환경",
        "tts_lang": "de-DE",             # 브라우저 내장 음성(대비책)
        # TTS 엔진: "qwen" 플레이스홀더. 실제 경로(GitHub Actions CPU vs Mac)는 Phase 1 후 확정.
        # 훅: audio.py 의 qwen 분기에서 NotImplementedError 를 발생시켜 페이지는 SpeechSynthesis 폴백으로 동작한다.
        "tts": "qwen",
        "voice": "",                     # Qwen3-TTS 1.7B CustomVoice Serena (경로 확정 후 채움)
        "speed": 0.9,
        "credit": "",                    # 라이선스상 표기 불필요하면 빈 문자열
        "copy_head": "나는 CEFR B1~B2 수준의 한국인 독일어 학습자입니다. 아래는 오늘의 독일어 읽기 연습 지문입니다.",
        "copy_weak": "자주 틀리는 부분(명사 성(der/die/das), 격변화(Kasus), 분리동사(trennbare Verben), 문장 끝 동사 위치(Verbstellung), 복합 명사)도 함께 짚어 주세요.",
        "head_extra": "",                # Pretendard 가 Latin Extended 포함, 추가 폰트 불필요
        "tools_extra": "",
        "furi_btn": "",
        # 언어별 플래그
        "email": False,                  # Phase 1: 메일 발송 차단. Phase 2에서 True 로 전환.
        "noindex": True,                 # Phase 1: 검색엔진 숨김. Phase 2에서 False 로 전환.
        "chunks": True,                  # 독일어 어순 끊어 읽기 활성화
        "levels": True,                  # 기초(A2~B1) levels.a 지문 활성화
        "level_a_label": "기초 A2~B1",  # chips-a 에 표시할 수준 레이블
    },
}

DEFAULT = "en"


def get(code):
    if code not in LANGS:
        raise SystemExit(f"알 수 없는 언어: {code} (가능: {', '.join(LANGS)})")
    return LANGS[code]
