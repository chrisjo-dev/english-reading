// 첫 화면 "03 / 단어 연습"(시안 design/kakao-login K09). 로그인하면 단어 기록이 계정에 남는다는 것을 보여 주고 가입 화면으로 보낸다.
// 버튼은 /join/ 으로만 간다(동의는 가입 화면에서 받는다). 아이콘은 tools/drill.py 의 KAKAO_ICON, GOOGLE_ICON 과 같은 모양.

const JOIN = "/join/?next=%2F&from=home";

function KakaoIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path fill="currentColor" d="M12 3C6.48 3 2 6.5 2 10.8c0 2.78 1.87 5.22 4.68 6.6l-.95 3.48c-.08.3.26.55.52.38l4.15-2.74c.52.06 1.06.1 1.6.1 5.52 0 10-3.5 10-7.82S17.52 3 12 3z" />
    </svg>
  );
}

function GoogleIcon() {
  return (
    <svg viewBox="0 0 48 48" aria-hidden="true">
      <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
      <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
      <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
      <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
    </svg>
  );
}

export default function LoginSection() {
  return (
    <section className="sec words" id="words" data-reveal aria-labelledby="words-h">
      <div className="wrap">
        <div className="sec-head">
          <span className="mono">03 / 단어 연습</span>
          <h2 id="words-h">
            읽은 지문의 단어,
            <br />내 것으로 만들어요.
          </h2>
        </div>
        <div className="words-body">
          <p className="words-lead rv">
            지문마다 핵심 단어 10개. 카드로 외우고 문제로 확인하면, 잊을 때쯤 복습 날짜에 다시 보여 드려요.
          </p>
          <div className="words-mini rv" aria-hidden="true">
            <span className="mono k">오늘 결과</span>
            <div className="words-score">
              <b>8</b>
              <span>/ 10개 한 번에 맞혔어요</span>
            </div>
            <div className="words-saved">
              ✓ 기록을 저장했어요<span>🔥 연속 5일</span>
            </div>
          </div>
          <div className="words-cta rv">
            <a className="btn-kakao" href={JOIN} data-login="kakao">
              <KakaoIcon />
              카카오로 3초 만에 시작
            </a>
            <a className="btn-google" href={JOIN} data-login="google">
              <GoogleIcon />
              Google로 시작하기
            </a>
            <p className="words-note">무료예요. 로그인에 필요한 정보만 받아요.</p>
          </div>
        </div>
      </div>
    </section>
  );
}
