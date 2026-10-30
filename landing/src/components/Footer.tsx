const W = "https://www.wspace.ai.kr";

const LINKS = [
  { label: "홈", href: `${W}/` },
  { label: "소개", href: `${W}/about/` },
  { label: "개인정보처리방침", href: `${W}/privacy/` },
  { label: "연락처", href: `${W}/contact/` },
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
        <span className="mono foot-url">read.wspace.ai.kr</span>
      </div>
    </footer>
  );
}
