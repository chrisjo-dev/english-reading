import Feedback from "./Feedback";
import { SITE_HOST } from "@/lib/site";

// 독해한입 자체 안내 페이지(tools/publish.py FOOTER_PAGES 와 같게, 시안 design/own-pages O05). 첫 화면 가기는 위 메뉴 로고가 맡는다
const LINKS = [
  { label: "소개", href: "/about/" },
  { label: "개인정보처리방침", href: "/privacy/" },
  { label: "연락처", href: "/contact/" },
];

export default function Footer() {
  return (
    <footer className="foot">
      <div className="wrap foot-in">
        <div className="foot-brand">
          <b>
            <i className="brand-mark" aria-hidden="true" />
            독해한입
          </b>
          <span>매일 아침 한 편, 외국어로 읽는 세상.</span>
          <Feedback />
        </div>
        <nav className="foot-links" aria-label="하단 메뉴">
          <a href="/en/">영어 지문</a>
          <a href="/ja/">일본어 지문</a>
          <a href="/de/">독일어 지문</a>
          {LINKS.map((l) => (
            <a key={l.label} href={l.href}>
              {l.label}
            </a>
          ))}
        </nav>
        <span className="mono foot-url">{SITE_HOST}</span>
      </div>
    </footer>
  );
}
