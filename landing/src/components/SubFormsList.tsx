"use client";

import React, { useState } from "react";
import { fireGtag } from "@/lib/gtag";
import { SUBSCRIBE } from "./forms";

const FORMS = [
  { lang: "en", label: "영어 지문 받기", level: "EN B1~B2", desc: "최근 소식을 바탕으로 쓴 영어 지문" },
  { lang: "ja", label: "일본어 지문 받기", level: "JA N3 / 기초 N4~N5", desc: "일본의 생활과 문화를 다룬 일본어 지문" },
  { lang: "de", label: "독일어 지문 받기", level: "DE B1~B2", desc: "독일의 생활과 사회를 다룬 독일어 지문" },
];

// levels=True 언어: 수준 선택 라디오를 표시한다(en, de, ja).
const LEVELS_BY_LANG: Record<string, { value: "a" | "b"; title: string; range: string; desc: string }[]> = {
  en: [
    { value: "a", title: "기초", range: "A2~B1", desc: "짧고 쉬운 문장. 영어 읽기를 다시 시작한다면" },
    { value: "b", title: "중급", range: "B1~B2", desc: "뉴스 기사에 가까운 문장. 긴 문장도 읽어 보고 싶다면" },
  ],
  de: [
    { value: "a", title: "기초", range: "A2~B1", desc: "짧고 쉬운 문장. 독일어 읽기를 막 시작했다면" },
    { value: "b", title: "중급", range: "B1~B2", desc: "조금 긴 문장과 B2 문법도 읽어 보고 싶다면" },
  ],
  ja: [
    { value: "a", title: "기초", range: "N4~N5", desc: "짧고 쉬운 문장. 일본어 읽기를 막 시작했다면" },
    { value: "b", title: "중급", range: "N3", desc: "조금 긴 문장과 N3 문법도 읽어 보고 싶다면" },
  ],
};

const delay = (i: number) => ({ transitionDelay: `${i * 60}ms` });

// levels=True 언어(en, de, ja)에 쓰는 수준 선택 포함 폼. 기본 선택은 중급.
// de, ja는 기초 지문이 이미 매일 있으므로 "기초 지문은 준비 중" 안내를 표시하지 않는다.
function LeveledForm({ f, style }: { f: (typeof FORMS)[0]; style?: React.CSSProperties }) {
  const [level, setLevel] = useState<"a" | "b">("b");
  const levels = LEVELS_BY_LANG[f.lang] ?? [];
  const showLevelNote = f.lang === "en" && level === "a";
  return (
    <form
      className="sub-form rv"
      style={style}
      action={SUBSCRIBE}
      method="post"
      target="_blank"
      rel="noopener noreferrer"
      onSubmit={() => fireGtag("subscribe_submit", { lang: f.lang, level, placement: "section" })}
    >
      <div className="mono k">
        <span>{f.level}</span>
        <span>{f.desc}</span>
      </div>
      <label className="sub-label" htmlFor={`email-${f.lang}`}>
        {f.label}
      </label>
      <input type="hidden" name="metadata__lang" value={f.lang} />
      <fieldset className="lv-opts">
        <legend>수준을 골라 주세요</legend>
        {levels.map((lv) => (
          <label key={lv.value} className="lv-opt">
            <input
              type="radio"
              name="metadata__level"
              value={lv.value}
              checked={level === lv.value}
              onChange={() => setLevel(lv.value)}
            />
            <span className="lv-t">
              {lv.title}
              <span className="lv-chk">✓</span>
            </span>
            <span className="lv-r">{lv.range}</span>
            <span className="lv-d">{lv.desc}</span>
          </label>
        ))}
      </fieldset>
      {showLevelNote && (
        <p className="lv-level-note" style={{ display: "block" }}>
          기초 지문은 준비 중이에요. 준비되면 기초 지문으로 보내 드려요. 그전에는 중급 지문이 가요.
        </p>
      )}
      <div className="row">
        <input id={`email-${f.lang}`} type="email" name="email" required placeholder="이메일 주소" autoComplete="email" />
        <button type="submit">구독하기</button>
      </div>
    </form>
  );
}

export default function SubFormsList() {
  return (
    <>
      {FORMS.map((f, i) =>
        f.lang in LEVELS_BY_LANG ? (
          <LeveledForm key={f.lang} f={f} style={delay(i)} />
        ) : (
          <form
            key={f.lang}
            className="sub-form rv"
            style={delay(i)}
            action={SUBSCRIBE}
            method="post"
            target="_blank"
            rel="noopener noreferrer"
            onSubmit={() => fireGtag("subscribe_submit", { lang: f.lang, placement: "section" })}
          >
            <div className="mono k">
              <span>{f.level}</span>
              <span>{f.desc}</span>
            </div>
            <label className="sub-label" htmlFor={`email-${f.lang}`}>
              {f.label}
            </label>
            <input type="hidden" name="metadata__lang" value={f.lang} />
            <div className="row">
              <input id={`email-${f.lang}`} type="email" name="email" required placeholder="이메일 주소" autoComplete="email" />
              <button type="submit">구독하기</button>
            </div>
          </form>
        )
      )}
    </>
  );
}
