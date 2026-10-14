"use client";

import { createContext, Fragment, useContext, useEffect, useState } from "react";
import type { LatestData } from "@/lib/latest-types";

const Ctx = createContext<LatestData | null>(null);

const total = (d: LatestData) => Object.values(d.langs).reduce((n, l) => n + l.count, 0);

// 빌드 때 넣은 데이터로 먼저 그리고, /latest.json 이 더 새로우면 바꾼다(다음 빌드 전까지 최신 유지).
export function LatestProvider({ initial, children }: { initial: LatestData; children: React.ReactNode }) {
  const [data, setData] = useState(initial);
  useEffect(() => {
    let off = false;
    fetch("/latest.json", { cache: "no-store" })
      .then((r) => (r.ok ? r.json() : null))
      .then((j: LatestData | null) => {
        if (off || !j?.langs || !Array.isArray(j.recent) || !j.date) return;
        if (j.date > initial.date || (j.date === initial.date && total(j) > total(initial))) setData(j);
      })
      .catch(() => {});
    return () => {
      off = true;
    };
  }, [initial]);
  return <Ctx.Provider value={data}>{children}</Ctx.Provider>;
}

export function useLatest() {
  const d = useContext(Ctx);
  if (!d) throw new Error("LatestProvider missing");
  return d;
}

export { total as totalCount };

const DAYS = "일월화수목금토";
export function koDate(iso: string) {
  const [y, m, d] = iso.split("-").map(Number);
  return `${m}월 ${d}일 ${DAYS[new Date(Date.UTC(y, m - 1, d)).getUTCDay()]}요일`;
}

// {漢字|かな} 후리가나 표기를 ruby 로.
function ruby(text: string) {
  const out: React.ReactNode[] = [];
  let last = 0;
  for (const m of text.matchAll(/\{([^{}|]+)\|([^{}|]+)\}/g)) {
    out.push(text.slice(last, m.index));
    out.push(
      <ruby key={m.index}>
        {m[1]}
        <rt>{m[2]}</rt>
      </ruby>,
    );
    last = m.index! + m[0].length;
  }
  out.push(text.slice(last));
  return out;
}

// **word** 는 강조 밑줄로.
export function Markup({ text }: { text: string }) {
  return (
    <>
      {text.split(/(\*\*[^*]+\*\*)/g).map((p, i) =>
        p.length > 4 && p.startsWith("**") && p.endsWith("**") ? (
          <span key={i} className="mark">
            {ruby(p.slice(2, -2))}
          </span>
        ) : (
          <Fragment key={i}>{ruby(p)}</Fragment>
        ),
      )}
    </>
  );
}
