"use client";

import { fireGtag } from "@/lib/gtag";
import { SUBSCRIBE } from "./forms";

const FORMS = [
  { lang: "en", label: "영어 지문 받기", level: "EN B1~B2", desc: "최근 소식을 바탕으로 쓴 영어 지문" },
  { lang: "ja", label: "일본어 지문 받기", level: "JA N4~N5", desc: "일본의 생활과 문화를 다룬 일본어 지문" },
];

const delay = (i: number) => ({ transitionDelay: `${i * 60}ms` });

export default function SubFormsList() {
  return (
    <>
      {FORMS.map((f, i) => (
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
      ))}
    </>
  );
}
