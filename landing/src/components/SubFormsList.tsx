"use client";

import React, { useRef, useState } from "react";
import { fireGtag } from "@/lib/gtag";
import { SUBSCRIBE } from "./forms";

const FORMS = [
  { lang: "en", name: "영어", label: "영어 지문 받기", level: "EN B1~B2", desc: "최근 소식과 생활 글로 읽는 영어 지문" },
  { lang: "ja", name: "일본어", label: "일본어 지문 받기", level: "JA N3 / 기초 N4~N5", desc: "일본의 소식과 문화, 생활을 다룬 일본어 지문" },
  { lang: "de", name: "독일어", label: "독일어 지문 받기", level: "DE B1~B2", desc: "독일의 소식과 문화, 생활을 다룬 독일어 지문" },
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

// 구독 폼 하나(design/sub-tabs 시안 A). 이메일 하나에 언어 하나(metadata.lang)라, 언어를 탭으로 고르게 해
// 여러 언어를 함께 받을 수 있는 것처럼 보이지 않게 한다. 수준은 언어를 바꿔도 유지하고 기본은 중급.
function SubForm({ style }: { style?: React.CSSProperties }) {
  const [i, setI] = useState(0);
  const [level, setLevel] = useState<"a" | "b">("b");
  const tabs = useRef<(HTMLButtonElement | null)[]>([]);
  const f = FORMS[i];
  const levels = LEVELS_BY_LANG[f.lang] ?? [];
  const pick = (n: number) => {
    const next = (n + FORMS.length) % FORMS.length;
    setI(next);
    tabs.current[next]?.focus();
  };
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
      <div
        className="sub-tabs"
        role="tablist"
        aria-label="받을 언어"
        onKeyDown={(e) => {
          if (e.key === "ArrowRight") pick(i + 1);
          else if (e.key === "ArrowLeft") pick(i - 1);
          else if (e.key === "Home") pick(0);
          else if (e.key === "End") pick(FORMS.length - 1);
          else return;
          e.preventDefault();
        }}
      >
        {FORMS.map((t, n) => (
          <button
            key={t.lang}
            ref={(el) => {
              tabs.current[n] = el;
            }}
            type="button"
            role="tab"
            id={`sub-tab-${t.lang}`}
            aria-selected={n === i}
            aria-controls="sub-panel"
            tabIndex={n === i ? 0 : -1}
            onClick={() => setI(n)}
          >
            {t.name}
          </button>
        ))}
      </div>
      <div id="sub-panel" role="tabpanel" aria-labelledby={`sub-tab-${f.lang}`}>
        <div className="mono k">
          <span>{f.level}</span>
          <span>{f.desc}</span>
        </div>
        <label className="sub-label" htmlFor="email-sub">
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
        <div className="row">
          <input id="email-sub" type="email" name="email" required placeholder="이메일 주소" autoComplete="email" />
          <button type="submit">구독하기</button>
        </div>
        <p className="sub-one">이메일 하나로 한 언어를 받아요. 나중에 같은 이메일로 다시 구독하면 언어와 수준이 바로 바뀌어요.</p>
      </div>
    </form>
  );
}

// 두 번째 칸: 다음에 추가할 언어 요청. 서버 없이 GA 이벤트 lang_request 로 언어별 요청 수만 센다.
const REQUEST_LANGS = ["중국어", "스페인어", "프랑스어", "베트남어", "러시아어", "이탈리아어"];

function LangRequest({ style }: { style?: React.CSSProperties }) {
  const [pick, setPick] = useState<string | null>(null);
  const [custom, setCustom] = useState("");
  const [sent, setSent] = useState(false);
  const other = pick === "기타";
  const lang = other ? custom.trim() : pick;
  return (
    <form
      className="sub-form lang-req rv"
      style={style}
      onSubmit={(e) => {
        e.preventDefault();
        if (!lang || sent) return;
        fireGtag("lang_request", { lang: lang.slice(0, 20), custom: other });
        setSent(true);
      }}
    >
      <div className="mono k">
        <span>? 다음 언어</span>
        <span>요청이 많은 언어부터 추가해요</span>
      </div>
      <span className="sub-label">언어 추가 요청하기</span>
      <fieldset className="lr-opts" disabled={sent}>
        <legend>어떤 언어를 읽고 싶으세요?</legend>
        <div className="lr-chips">
          {REQUEST_LANGS.map((l) => (
            <button key={l} type="button" className="lr-chip" aria-pressed={pick === l} onClick={() => setPick(l)}>
              {l}
            </button>
          ))}
          <button type="button" className="lr-chip etc" aria-pressed={other} onClick={() => setPick("기타")}>
            + 직접 쓰기
          </button>
        </div>
        {other && (
          <input
            className="lr-input"
            type="text"
            maxLength={20}
            placeholder="예: 포르투갈어"
            aria-label="요청할 언어"
            value={custom}
            onChange={(e) => setCustom(e.target.value)}
            autoFocus
          />
        )}
      </fieldset>
      <div className="lr-foot">
        <button type="submit" className="lr-send" disabled={!lang || sent}>
          {sent ? "요청을 보냈어요" : "요청 보내기"}
        </button>
        {sent ? (
          <p className="lr-thanks" role="status">고마워요. 요청이 많은 언어부터 추가할게요.</p>
        ) : (
          <p className="lr-hint">이메일 없이 보내져요. 어떤 언어가 많이 요청됐는지만 세요.</p>
        )}
      </div>
    </form>
  );
}


export default function SubFormsList() {
  return (
    <>
      <SubForm style={delay(0)} />
      <LangRequest style={delay(1)} />
    </>
  );
}
