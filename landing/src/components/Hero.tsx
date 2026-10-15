"use client";

import { Fragment } from "react";
import { fireGtag } from "@/lib/gtag";
import HeroForm from "./HeroForm";
import Phone from "./Phone";
import { useLatest } from "./ref/latest";
import { head, keyMeaning } from "./util";

// 한 단어씩 아래에서 올라오도록 단어마다 가림 상자로 감싼다.
function Words({ text }: { text: string }) {
  return (
    <>
      {text.split(" ").map((w, i) => (
        <Fragment key={i}>
          {i > 0 && " "}
          <span className="wm">
            <span style={{ animationDelay: `${120 + i * 90}ms`, transitionDelay: `${i * 90}ms` }}>{w}</span>
          </span>
        </Fragment>
      ))}
    </>
  );
}

// 모범 해석에서 핵심 단어의 뜻을 밑줄로.
function Underlined({ text, word }: { text: string; word: string }) {
  const at = word ? text.indexOf(word) : -1;
  if (at < 0) return <>{text}</>;
  return (
    <>
      {text.slice(0, at)}
      <u>{word}</u>
      {text.slice(at + word.length)}
    </>
  );
}

export default function Hero() {
  const d = useLatest();
  const en = d.langs.en;
  const ja = d.langs.ja;
  const words = en?.words ?? [];
  const answer = en?.answer ?? "";
  const draft = answer.split(" ").slice(0, 4).join(" ");
  const stats = `EN ${en?.count ?? 0}편 / JA ${ja?.count ?? 0}편 / 단어 ${d.words_total ?? 0}개, 언제든 해지할 수 있어요`;
  const topics = d.recent;

  return (
    <section className="c3" aria-labelledby="c3-h">
      <div className="c3-in">
        <span className="c3-axis" aria-hidden="true" />
        <span className="c3-deg mono" aria-hidden="true">
          ROTATE <b data-deg>-6°</b> → 0°
        </span>
        <h1 id="c3-h" className="sr">
          하루 5분, 매일 아침.
        </h1>
        <p className="c3-h1 rise" aria-hidden="true">
          <Words text="하루 5분," />
        </p>
        <p className="c3-sub">
          출근길에 외국어 지문 하나.
          <br />
          읽고, 듣고, AI에게 해석 피드백을 받아요.
        </p>

        {answer && (
          <figure className="frag f-tr">
            <figcaption className="mono k">
              <span>모범 해석 / 문장 01</span>
              <span>KO</span>
            </figcaption>
            <p>
              <Underlined text={answer} word={keyMeaning(answer, words)} />
            </p>
          </figure>
        )}

        {en && (
          <a
            className="c3-phone"
            href={`/en/${en.latest}/`}
            aria-label={`오늘의 영어 지문 읽기: ${en.topic}`}
            data-phone
            onClick={() => fireGtag("read_today_click", { lang: "en" })}
          >
            <Phone date={en.latest} topic={en.topic} chips={en.chips ?? []} sentences={en.sentences} draft={draft} />
          </a>
        )}

        <div className="frag f-mail" role="img" aria-label={`메일 알림: 매일 영어 읽기, 오늘은 ${en?.topic} 이야기예요, 07:02`}>
          <span className="ic">
            <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true">
              <rect x="2.5" y="4.5" width="15" height="11" rx="1.5" fill="none" stroke="currentColor" strokeWidth="1.5" />
              <path d="M3 5.5l7 5.5 7-5.5" fill="none" stroke="currentColor" strokeWidth="1.5" />
            </svg>
          </span>
          <div>
            <b>매일 영어 읽기</b>
            <span className="t">오늘은 {en?.topic} 이야기예요</span>
          </div>
          <span className="mono">07:02</span>
        </div>

        {words.length > 0 && (
          <div className="frag f-words">
            <div className="mono k">
              <span>핵심 단어 / 오늘</span>
              <span>
                {Math.min(4, words.length)} / {words.length}
              </span>
            </div>
            <ul className="chips" lang="en">
              {words.slice(0, 4).map(([w, m], i) => (
                <li key={w} className={i === 0 ? "on" : undefined}>
                  <b>{w}</b>
                  <em lang="ko">{head(m)}</em>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="frag f-sun">
          <b>일요일, 주간 단어 복습 메일</b>
          <span className="mono">SUN 07:00</span>
        </div>

        <p className="c3-h2" aria-hidden="true" data-sweep>
          <Words text="매일 아침." />
          <span className="c3-sweep">
            <i />
          </span>
        </p>

        <HeroForm stats={stats} />
      </div>

      <div className="c3-band">
        <span className="lab">최근 지문</span>
        <div className="marq">
          {[0, 1].map((k) => (
            <ul key={k} className="marq-set" aria-hidden={k === 1 ? true : undefined} aria-label={k === 0 ? "최근 지문 주제" : undefined}>
              {topics.map((r) => (
                <li key={`${r.lang}-${r.day}`}>
                  <i>{r.lang.toUpperCase()}</i>
                  {r.topic}
                </li>
              ))}
            </ul>
          ))}
        </div>
      </div>
    </section>
  );
}
