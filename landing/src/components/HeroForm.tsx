"use client";

import { useState } from "react";
import { fireGtag } from "@/lib/gtag";
import { CONFIRM_NOTE, SUBSCRIBE } from "./forms";

const HELP = {
  en: "영어 지문 / CEFR B1~B2, 최근 소식을 바탕으로 써요",
  ja: "일본어 지문 / JLPT N4~N5, 일본의 생활과 문화를 다뤄요",
} as const;

type Lang = keyof typeof HELP;

// 첫 화면 구독 폼. 언어 전환은 숨은 metadata__lang 값과 안내 문구만 바꾼다.
// 스크립트가 없으면 전환 버튼은 숨겨지고 영어로 구독된다(일본어는 아래 구독 섹션에서 고를 수 있다).
export default function HeroForm({ stats }: { stats: string }) {
  const [lang, setLang] = useState<Lang>("en");
  return (
    <form
      className="c3-form"
      action={SUBSCRIBE}
      method="post"
      target="_blank"
      rel="noopener noreferrer"
      onSubmit={() => fireGtag("subscribe_submit", { lang, placement: "hero" })}
    >
      <div className="c3-form-top">
        <label className="mono" htmlFor="hero-email">
          무료 구독 / 매일 07:00 전후
        </label>
        <div className="sw" role="group" aria-label="받을 언어">
          {(["en", "ja"] as const).map((l) => (
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
