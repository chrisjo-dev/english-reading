"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { fireGtag } from "@/lib/gtag";
import { useLatest } from "./ref/latest";

// 위 메뉴(GNB) 시안 A(design/gnb-mobile G01, G02, G03). 지문 페이지와 같은 마크업, 같은 CSS(../app/gnb.css)를 쓴다.
// 첫 화면은 언어가 정해지지 않아 칩 문구를 "언어"로 두고, 시트에는 언어별 단어 복습 줄을 넣지 않는다.
const LANGS = [
  { code: "en", name: "영어", level: "B1~B2" },
  { code: "ja", name: "일본어", level: "JLPT N3" },
  { code: "de", name: "독일어", level: "B1~B2" },
];

// 시트가 열린 동안 iOS 상태 표시줄도 어둡게: 흰 바탕 위 rgba(16,24,40,.40) 합성색. 돌려주는 함수가 원래대로 되돌린다(없었으면 지운다)
const SHEET_THEME = "#9fa3a9";
function tintThemeColor(): () => void {
  let m = document.querySelector<HTMLMetaElement>('meta[name="theme-color"]');
  const prev = m ? m.getAttribute("content") : null;
  if (!m) {
    m = document.createElement("meta");
    m.name = "theme-color";
    document.head.appendChild(m);
  }
  m.setAttribute("content", SHEET_THEME);
  const meta = m;
  return () => {
    if (prev === null) meta.remove();
    else meta.setAttribute("content", prev);
  };
}

const plain = (t: string) => t.replace(/\{([^{}|]+)\|[^{}|]+\}/g, "$1");

const Down = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="M6 9l6 6 6-6" />
  </svg>
);
const Right = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="M9 6l6 6-6 6" />
  </svg>
);

export default function Nav() {
  const data = useLatest().langs;
  const [open, setOpen] = useState(false);
  const chip = useRef<HTMLButtonElement>(null);
  const sheet = useRef<HTMLDivElement>(null);
  const today = (c: string) => (data[c]?.latest ? `/${c}/${data[c].latest}/` : `/${c}/`);

  const close = useCallback(() => {
    setOpen(false);
    chip.current?.focus();
  }, []);

  useEffect(() => {
    if (!open) return;
    const root = document.documentElement;
    root.classList.add("gnb-lock");
    const untint = tintThemeColor();
    // 포커스는 시트 자체로(링크로 옮기면 iOS Safari가 파란 테두리를 그린다)
    sheet.current?.focus();
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        close();
        return;
      }
      if (e.key !== "Tab" || !sheet.current) return;
      const f = Array.from(sheet.current.querySelectorAll<HTMLAnchorElement>("a[href]"));
      if (!f.length) return;
      const a = f[0];
      const z = f[f.length - 1];
      if (document.activeElement === sheet.current) {
        e.preventDefault();
        (e.shiftKey ? z : a).focus();
      } else if (e.shiftKey && document.activeElement === a) {
        e.preventDefault();
        z.focus();
      } else if (!e.shiftKey && document.activeElement === z) {
        e.preventDefault();
        a.focus();
      } else if (!sheet.current.contains(document.activeElement)) {
        e.preventDefault();
        a.focus();
      }
    };
    document.addEventListener("keydown", key);
    return () => {
      document.removeEventListener("keydown", key);
      root.classList.remove("gnb-lock");
      untint();
    };
  }, [open, close]);

  return (
    <>
      <header className="gnb">
        <div className="gnb-in">
          <Link className="gnb-brand" href="/" prefetch={false}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/assets/brand/duck-lying-64.png" alt="" width={40} height={26} />
            <span>독해한입</span>
          </Link>
          <nav className="gnb-seg" aria-label="언어">
            {LANGS.map((l) => (
              <a key={l.code} href={today(l.code)} onClick={() => fireGtag("read_today_click", { lang: l.code })}>
                {l.name}
              </a>
            ))}
          </nav>
          <a className="gnb-past" href="#past">
            지난 지문
          </a>
          <button
            ref={chip}
            className="gnb-tap gnb-chip"
            id="gnb-chip"
            type="button"
            aria-haspopup="dialog"
            aria-expanded={open}
            aria-controls="gnb-sheet"
            aria-label="언어 고르기"
            onClick={() => {
              if (open) close();
              else {
                setOpen(true);
                fireGtag("gnb_sheet_open", { lang: "" });
              }
            }}
          >
            <span className="gnb-pill">
              언어
              <Down />
            </span>
          </button>
          <a className="gnb-tap gnb-mail" href="#subscribe">
            <span className="gnb-pill">메일로 받기</span>
          </a>
        </div>
      </header>
      <div className="gnb-scrim" id="gnb-scrim" hidden={!open} onClick={close} />
      <div
        ref={sheet}
        className="gnb-sheet"
        id="gnb-sheet"
        role="dialog"
        aria-modal="true"
        aria-labelledby="gnb-sheet-h"
        tabIndex={-1}
        hidden={!open}
      >
        <div className="gs-handle" />
        <h2 id="gnb-sheet-h">어떤 언어를 읽을까요?</h2>
        <p className="gs-hint">언어를 누르면 그 언어의 오늘 지문으로 가요</p>
        {LANGS.map((l) => (
          <div className="gs-row" key={l.code}>
            <a className="gs-tx" href={today(l.code)} onClick={() => fireGtag("read_today_click", { lang: l.code })}>
              <span className="gs-badge" aria-hidden="true">
                {l.code.toUpperCase()}
              </span>
              <span className="gs-tt">
                <span className="gs-nm">{l.name}</span>
                <span className="gs-ds">
                  {data[l.code]?.topic ? `${l.level}, 오늘은 ${plain(data[l.code].topic)}` : `${l.level} ${l.name} 읽기`}
                </span>
              </span>
            </a>
            <a className="gs-past" href={`/${l.code}/archive/`} aria-label={`${l.name} 지난 지문`}>
              지난 지문
              <Right />
            </a>
          </div>
        ))}
      </div>
    </>
  );
}
