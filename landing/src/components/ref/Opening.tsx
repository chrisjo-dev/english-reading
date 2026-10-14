"use client";

import { useState } from "react";
import { koDate, Markup, useLatest } from "./latest";

const TICKS = ["en", "ja"] as const;

export default function Opening() {
  const d = useLatest();
  const [lang, setLang] = useState<(typeof TICKS)[number]>("en");
  const first = d.langs[lang]?.sentences[0] ?? "";

  return (
    <section className="op">
      {/* Faint outlined glyphs, decorative */}
      <div className="op-glyph" aria-hidden="true">
        <span className="op-glyph-a">A</span>
        <span className="op-glyph-ja">あ</span>
      </div>

      <div className="op-metas">
        {/* Top-left meta */}
        <div className="op-meta-l">
          <div>매일 외국어 읽기</div>
          <div>한국인 학습자를 위한 영어, 일본어 지문</div>
        </div>

        {/* Top-right meta */}
        <div className="op-meta-r">
          <div>No. {d.langs.en?.count ?? 0} — 오늘</div>
          <div>{koDate(d.date)}</div>
        </div>
      </div>

      <h1 className="op-title">
        {/* Title line 1 + superscript */}
        <span className="op-l1">
          <span className="op-l1-main">Read the</span>
          <span className="op-l1-sup">daily</span>
        </span>
        {/* Title line 2 */}
        <span className="op-l2">World Slowly</span>
      </h1>

      <div className="op-bottom">
        {/* Left caption */}
        <div className="op-caption">하루 5분, 짧은 지문 하나.</div>

        {/* Center block */}
        <div className="op-ctl">
          <div className="op-ctl-label">
            <span>언어를 바꿔 보세요</span>
            <span style={{ fontSize: "14px" }}>&#8596;</span>
          </div>
          <div className="op-ctl-line">
            <div className="op-ctl-dot" data-lang={lang} />
          </div>
          <div className="op-ctl-ticks" role="group" aria-label="지문 언어">
            {TICKS.map((t) => (
              <button key={t} type="button" aria-pressed={lang === t} onClick={() => setLang(t)}>
                {t.toUpperCase()}
              </button>
            ))}
          </div>
          <p className="op-ctl-text" lang={lang} aria-live="polite">
            <Markup text={first} />
          </p>
          <div className="op-ctl-desc">
            EN: {d.langs.en?.topic}&nbsp;&nbsp;JA: {d.langs.ja?.topic}
          </div>
        </div>

        {/* Right: label + circle button */}
        <div className="op-go">
          <span>읽기 시작</span>
          <a className="op-btn" href="#languages" aria-label="오늘의 지문으로 이동">
            <span>&#8600;</span>
          </a>
        </div>
      </div>
    </section>
  );
}
