"use client";

import { ArchiveHead } from "./Chapter";
import { koDate, Markup, useLatest } from "./latest";

const LANG_ROWS = [
  { code: "en", name: "영어", level: "CEFR B1~B2" },
  { code: "ja", name: "일본어", level: "JLPT N4~N5" },
];

export function TodayStatement() {
  const d = useLatest();
  return <>오늘은 {d.langs.en?.topic} 이야기예요.</>;
}

export function TodayDate() {
  return <>{koDate(useLatest().date)}</>;
}

export function TodayLeft() {
  const en = useLatest().langs.en;
  const href = en ? `/en/${en.latest}/` : "/en/";
  return (
    <>
      <a className="ch-link" href={href}>
        오늘 지문 전체 읽기 &#8599;
      </a>
      <a className="ch-listen" href={href}>
        &#9655; 문장별 음성으로 듣기
      </a>
      <div className="ch-note">원어민 합성 음성, 문장마다 따로 들을 수 있어요</div>
    </>
  );
}

export function TodayRight() {
  const d = useLatest();
  return (
    <>
      {/* Body text: today's first three English sentences */}
      <p className="ch-body" lang="en">
        {(d.langs.en?.sentences ?? []).map((s, i) => (
          <span key={i}>
            {i > 0 && " "}
            <Markup text={s} />
          </span>
        ))}
      </p>

      <ArchiveHead left="지난 지문" right="최근 6편" />
      {d.recent.map((r) => (
        <a key={`${r.lang}-${r.day}`} className="ch-row" href={`/${r.lang}/${r.day}/`}>
          <span className="ch-row-k">{r.day}</span>
          <span className="ch-row-t">
            <span className="ch-tag">{r.lang.toUpperCase()}</span>
            {r.topic}
          </span>
          <span className="ch-row-a">&#8599;</span>
        </a>
      ))}

      {/* Language index */}
      <div className="ch-idx">
        <div className="ch-idx-row ch-idx-head">
          <span>No.</span>
          <span>언어</span>
          <span>수준</span>
          <span>지문 수</span>
          <span className="ch-idx-topic">오늘의 주제</span>
          <span />
        </div>
        {LANG_ROWS.map((l, i) => (
          <a key={l.code} className="ch-idx-row" href={`/${l.code}/`}>
            <span className="ch-row-k">0{i + 1}</span>
            <span>{l.name}</span>
            <span className="ch-idx-level">{l.level}</span>
            <span>{d.langs[l.code]?.count ?? 0}편</span>
            <span className="ch-idx-topic">{d.langs[l.code]?.topic}</span>
            <span className="ch-row-a">&rarr;</span>
          </a>
        ))}
      </div>
    </>
  );
}
