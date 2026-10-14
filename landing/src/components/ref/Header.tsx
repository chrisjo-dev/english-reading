"use client";

import Link from "next/link";
import { useLatest } from "./latest";

const LINKS = [
  { label: "영어 지문", href: "/en/" },
  { label: "일본어 지문", href: "/ja/" },
  { label: "이용 방법", href: "#how" },
  { label: "자주 묻는 질문", href: "#faq" },
  { label: "wspace", href: "https://www.wspace.ai.kr/" },
];

export default function Header() {
  const d = useLatest();
  return (
    <>
      {/* Fixed top header */}
      <header className="hd">
        <Link className="hd-brand" href="/" prefetch={false}>
          매일 외국어 읽기
        </Link>
        <div className="hd-right">
          <nav className="hd-nav" aria-label="주요 메뉴">
            {LINKS.map((l) => (
              <a key={l.href} href={l.href}>
                {l.label}
              </a>
            ))}
          </nav>
          <a className="hd-sub" href="#subscribe">
            무료 구독 &#8600;
          </a>
        </div>
      </header>

      {/* Bottom fixed bar */}
      <div className="hd-bar">
        <span className="hd-count">
          지문 {d.langs.en?.count ?? 0}편 / {d.langs.ja?.count ?? 0}편
        </span>
        <div className="hd-chips">
          <span className="hd-chip">EN B1~B2</span>
          <span className="hd-chip">JA N4~N5</span>
        </div>
      </div>
    </>
  );
}
