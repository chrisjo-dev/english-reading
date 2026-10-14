"use client";

import { useLatest } from "./ref/latest";
import { dotDate, iso, shortDate, utc, weekday } from "./util";

// 가장 최근 지문 날짜가 든 주(월~일). 지난 날은 실제 주제, 앞으로 올 날은 공개 예정으로 둔다.
export function useWeek() {
  const d = useLatest();
  const today = utc(d.date);
  const monday = new Date(today);
  monday.setUTCDate(today.getUTCDate() - ((today.getUTCDay() + 6) % 7));
  const days = Array.from({ length: 7 }, (_, i) => {
    const t = new Date(monday);
    t.setUTCDate(monday.getUTCDate() + i);
    const day = iso(t);
    return { day, items: d.recent.filter((r) => r.day === day), future: day > d.date, today: day === d.date };
  });
  return { days, count: days.reduce((n, x) => n + x.items.length, 0) };
}

export function WeekMeta() {
  const { days, count } = useWeek();
  return (
    <>
      {dotDate(days[0].day)} ~ {shortDate(days[6].day)} / 지금까지 {count}편
    </>
  );
}

export default function Week() {
  const { days } = useWeek();
  return (
    <ol className="week">
      {days.map((x, i) => (
        <li
          key={x.day}
          className={`day rv${x.today ? " today" : ""}${i === 6 ? " sun" : ""}`}
          style={{ transitionDelay: `${i * 60}ms` }}
        >
          <div className="day-h">
            <b>{weekday(x.day)}</b>
            <span className="mono">{shortDate(x.day)}</span>
            {x.today && <span className="tag">오늘</span>}
          </div>
          <ul>
            {x.items.map((r) => (
              <li key={r.lang}>
                <span className="mono lang">{r.lang.toUpperCase()}</span>
                <a href={`/${r.lang}/${r.day}/`}>{r.topic}</a>
              </li>
            ))}
            {!x.items.length && <li className="empty mono">{x.future ? "07:00 공개 예정" : "지문 없음"}</li>}
            {i === 6 && <li className="review">주간 단어 복습 메일</li>}
          </ul>
        </li>
      ))}
    </ol>
  );
}
