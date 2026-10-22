"use client";

import React, { useState } from "react";
import { fireGtag } from "@/lib/gtag";
import { SUBSCRIBE } from "./forms";

const FORMS = [
  { lang: "en", label: "영어 지문 받기", level: "EN B1~B2", desc: "최근 소식을 바탕으로 쓴 영어 지문" },
  { lang: "ja", label: "일본어 지문 받기", level: "JA N4~N5", desc: "일본의 생활과 문화를 다룬 일본어 지문" },
];

const LEVELS: { value: "a" | "b"; title: string; range: string; desc: string }[] = [
  { value: "a", title: "기초", range: "A2~B1", desc: "짧고 쉬운 문장. 영어 읽기를 다시 시작한다면" },
  { value: "b", title: "중급", range: "B1~B2", desc: "뉴스 기사에 가까운 문장. 긴 문장도 읽어 보고 싶다면" },
];

const delay = (i: number) => ({ transitionDelay: `${i * 60}ms` });

function EnForm({ f, style }: { f: (typeof FORMS)[0]; style?: React.CSSProperties }) {
  const [level, setLevel] = useState<"a" | "b">("b");
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
        {LEVELS.map((lv) => (
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
      {level === "a" && (
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
        f.lang === "en" ? (
          <EnForm key={f.lang} f={f} style={delay(i)} />
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
