"use client";

import Link from "next/link";
import { fireGtag } from "@/lib/gtag";
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
          <a
            href={en ? `/en/${en.latest}/` : "/en/"}
            onClick={() => fireGtag("read_today_click", { lang: "en" })}
          >오늘의 지문</a>
          <a href="/en/archive/">영어 지문</a>
          <a href="/ja/archive/">일본어 지문</a>
          <a href="#how">이용 안내</a>
        </nav>
        {/* 휴대폰은 위 메뉴가 숨어 있어 지난 지문 입구를 따로 둔다(이슈 #19) */}
        <a className="nav-m" href="#past">지난 지문</a>
        <a className="nav-cta" href="#subscribe">
          무료로 시작하기
        </a>
      </div>
    </header>
  );
}
