// 첫 화면에서 쓰는 작은 표기 도우미(빌드와 브라우저 양쪽에서 쓴다).
const DAYS = "일월화수목금토";

// "2026-10-14" -> Date(UTC). 요일 계산을 시간대와 무관하게 하려고 UTC 로 둔다.
export function utc(iso: string) {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d));
}

export const iso = (d: Date) => d.toISOString().slice(0, 10);
export const weekday = (iso: string) => DAYS[utc(iso).getUTCDay()];
export const dotDate = (iso: string) => iso.replace(/-/g, ".");
export const shortDate = (iso: string) => iso.slice(5).replace("-", ".");

// "나타나다, ~로 보이다" -> "나타나다". 뜻풀이의 첫 덩어리만 칩에 쓴다.
export const head = (meaning: string) => meaning.split(/[,(]/)[0].trim();

// 오늘 단어 가운데 모범 해석에 그대로 나오는 첫 뜻을 찾는다(해석 속 밑줄 위치).
export function keyMeaning(answer: string, words: [string, string][]) {
  for (const [, m] of words) {
    const h = head(m);
    if (h && answer.includes(h)) return h;
  }
  return "";
}
