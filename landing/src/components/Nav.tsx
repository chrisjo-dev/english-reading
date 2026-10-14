"use client";

import Link from "next/link";
import { useLatest } from "./ref/latest";

export default function Nav() {
  const en = useLatest().langs.en;
  return (
    <header className="nav">
      <div className="wrap nav-in">
        <Link className="brand" href="/" prefetch={false}>
          <i className="brand-mark" aria-hidden="true" />
          매일 외국어 읽기
        </Link>
        <nav className="nav-links" aria-label="주요 메뉴">
          <a href={en ? `/en/${en.latest}/` : "/en/"}>오늘의 지문</a>
          <a href="/en/">지난 지문</a>
          <a href="#how">이용 안내</a>
        </nav>
        <a className="nav-cta" href="#subscribe">
          무료로 시작하기
        </a>
      </div>
    </header>
  );
}
