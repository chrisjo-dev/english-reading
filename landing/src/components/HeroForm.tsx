"use client";

import { useState } from "react";
import { fireGtag } from "@/lib/gtag";
import { CONFIRM_NOTE, SUBSCRIBE } from "./forms";

const HELP = {
  en: "영어 지문 / CEFR B1~B2, 최근 소식을 바탕으로 써요",
  ja: "일본어 지문 / JLPT N4~N5, 일본의 생활과 문화를 다뤄요",
  de: "독일어 지문 / CEFR B1~B2, 독일의 생활과 사회를 다뤄요",
} as const;

type Lang = keyof typeof HELP;
type Level = "a" | "b";

// levels=True 언어: 수준 선택 라디오를 표시한다.
const LEVELS_LANGS: Lang[] = ["en", "de"];

const LEVELS_BY_LANG: Record<string, { value: Level; title: string; range: string; desc: string }[]> = {
  en: [
    { value: "a", title: "기초", range: "A2~B1", desc: "짧고 쉬운 문장. 영어 읽기를 다시 시작한다면" },
    { value: "b", title: "중급", range: "B1~B2", desc: "뉴스 기사에 가까운 문장. 긴 문장도 읽어 보고 싶다면" },
  ],
  de: [
    { value: "a", title: "기초", range: "A2~B1", desc: "짧고 쉬운 문장. 독일어 읽기를 막 시작했다면" },
    { value: "b", title: "중급", range: "B1~B2", desc: "조금 긴 문장과 B2 문법도 읽어 보고 싶다면" },
  ],
};

// 첫 화면 구독 폼. 언어 전환은 숨은 metadata__lang 값과 안내 문구만 바꾼다.
// en, de 선택 시 수준 선택 카드(기초/중급)가 표시된다. ja는 수준 선택 없음.
// de는 기초 지문이 이미 매일 있으므로 "기초 지문은 준비 중" 안내를 표시하지 않는다.
// 스크립트가 없으면 전환 버튼은 숨겨지고 영어로 구독된다(다른 언어는 아래 구독 섹션에서 고를 수 있다).
export default function HeroForm({ stats }: { stats: string }) {
  const [lang, setLang] = useState<Lang>("en");
  const [level, setLevel] = useState<Level>("b");
  const hasLevels = LEVELS_LANGS.includes(lang);
  const levels = LEVELS_BY_LANG[lang] ?? [];
  return (
    <form
      className="c3-form"
      action={SUBSCRIBE}
      method="post"
      target="_blank"
      rel="noopener noreferrer"
      onSubmit={() => fireGtag("subscribe_submit", { lang, level: hasLevels ? level : undefined, placement: "hero" })}
    >
      <div className="c3-form-top">
        <label className="mono" htmlFor="hero-email">
          무료 구독 / 매일 07:00 전후
        </label>
        <div className="sw" role="group" aria-label="받을 언어">
          {(["en", "ja", "de"] as const).map((l) => (
            <button
              key={l}
              type="button"
              aria-pressed={lang === l}
              onClick={() => {
                setLang(l);
                fireGtag("lang_switch", { lang: l });
              }}
            >
              {l.toUpperCase()}
            </button>
          ))}
        </div>
      </div>
      <input type="hidden" name="metadata__lang" value={lang} />
      {hasLevels && (
        <>
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
          {lang === "en" && level === "a" && (
            <p className="lv-level-note" style={{ display: "block" }}>
              기초 지문은 준비 중이에요. 준비되면 기초 지문으로 보내 드려요. 그전에는 중급 지문이 가요.
            </p>
          )}
        </>
      )}
      <div className="row">
        <input id="hero-email" type="email" name="email" required placeholder="이메일 주소" autoComplete="email" />
        <button type="submit">무료로 시작하기</button>
      </div>
      <p className="mono c3-help" aria-live="polite">
        {HELP[lang]}
      </p>
      <p className="mono c3-stats">{stats}</p>
      <p className="confirm-note">{CONFIRM_NOTE}</p>
    </form>
  );
}
