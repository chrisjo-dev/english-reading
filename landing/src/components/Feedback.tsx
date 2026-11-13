"use client";

import { fireGtag } from "@/lib/gtag";
import { SITE } from "@/lib/site";

// 의견 보내기(이슈 #21, 시안 F03). tools/feedback.py 와 같은 메일 양식이다.
// 버그 제보는 누르는 순간 페이지 주소, 기기와 브라우저, 화면 크기를 본문에 넣는다.
const MAIL = "hello@dokhaehanip.com";
const IDEA_BODY = "어떤 기능이 있으면 좋을까요?\n\n\n왜 필요한가요? (어떤 때 불편했는지)";
const BUG_HEAD = "무슨 일이 있었나요?\n(예: 음성이 안 나와요, 글자가 겹쳐 보여요)\n\n\n----\n";

function mailto(subject: string, body: string) {
  return `mailto:${MAIL}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body.replace(/\n/g, "\r\n"))}`;
}

function device() {
  const u = navigator.userAgent;
  let d = "Windows";
  let b = "Safari";
  if (/iPhone/.test(u)) d = "iPhone";
  else if (/iPad/.test(u) || (/Macintosh/.test(u) && navigator.maxTouchPoints > 1)) d = "iPad";
  else if (/Android/.test(u)) d = "Android";
  else if (/Macintosh/.test(u)) d = "Mac";
  else if (!/Windows/.test(u)) d = "기타";
  if (/KAKAOTALK/i.test(u)) b = "카카오톡";
  else if (/NAVER/.test(u)) b = "네이버";
  else if (/SamsungBrowser/.test(u)) b = "Samsung Internet";
  else if (/Edg/.test(u)) b = "Edge";
  else if (/FxiOS|Firefox/.test(u)) b = "Firefox";
  else if (/CriOS|Chrome/.test(u)) b = "Chrome";
  return `${d}, ${b}`;
}

const IDEA_HREF = mailto("[독해한입] 기능 건의", IDEA_BODY);
const BUG_HREF = mailto("[독해한입] 버그 제보", `${BUG_HEAD}페이지: ${SITE}/\n기기: \n화면 크기: `);

export default function Feedback() {
  return (
    <div className="fb-row">
      <a className="fb-btn" href={IDEA_HREF} onClick={() => fireGtag("feedback", { type: "idea" })}>
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M9 18h6M10 21h4M12 3a6 6 0 0 0-3.6 10.8c.6.5 1 1.2 1 2V16h5.2v-.2c0-.8.4-1.5 1-2A6 6 0 0 0 12 3z" />
        </svg>
        기능 건의
      </a>
      <a
        className="fb-btn"
        href={BUG_HREF}
        onClick={(e) => {
          e.currentTarget.href = mailto(
            "[독해한입] 버그 제보",
            `${BUG_HEAD}페이지: ${location.href}\n기기: ${device()}\n화면 크기: ${window.innerWidth} x ${window.innerHeight}`,
          );
          fireGtag("feedback", { type: "bug" });
        }}
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <rect x="7" y="8" width="10" height="12" rx="5" />
          <path d="M9 8a3 3 0 0 1 6 0M3 13h4M17 13h4M4 7l3 2M20 7l-3 2M4 19l3-2M20 19l-3-2M12 11v8" />
        </svg>
        버그 제보
      </a>
    </div>
  );
}
