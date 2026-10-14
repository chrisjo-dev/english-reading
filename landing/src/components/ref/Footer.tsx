"use client";

import { totalCount, useLatest } from "./latest";

const W = "https://www.wspace.ai.kr";

export default function Footer() {
  const n = totalCount(useLatest());
  const columns: { dt: string; items: { label: string; href?: string }[] }[] = [
    {
      dt: "서비스",
      items: [
        { label: "영어 지문", href: "/en/" },
        { label: "일본어 지문", href: "/ja/" },
      ],
    },
    { dt: "구독", items: [{ label: "무료 구독", href: "#subscribe" }] },
    {
      dt: "wspace",
      items: [
        { label: "홈", href: `${W}/` },
        { label: "소개", href: `${W}/about/` },
        { label: "개인정보처리방침", href: `${W}/privacy/` },
        { label: "연락처", href: `${W}/contact/` },
      ],
    },
    { dt: "정보", items: [{ label: `지문 ${n}편` }, { label: "운영 Chris Jo" }] },
  ];

  return (
    <footer className="ft">
      {/* Left copy */}
      <div className="ft-copy">매일 아침 한 편, 외국어로 읽는 세상.</div>

      {/* Four columns */}
      {columns.map((col) => (
        <dl key={col.dt} className="ft-col">
          <dt>{col.dt}</dt>
          {col.items.map((it) => (
            <dd key={it.label}>{it.href ? <a href={it.href}>{it.label}</a> : <span>{it.label}</span>}</dd>
          ))}
        </dl>
      ))}
    </footer>
  );
}
