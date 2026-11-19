// 사이트 반응을 DB(site_events)에 보낸다. 지문 페이지와 같은 방식(tools/siteevent.py): 익명 방문 번호와 sendBeacon.
export function sendEvent(o: { kind: "lang_request" | "feedback"; value: string; src?: string }): void {
  try {
    const k = "dkh-vid";
    let v = localStorage.getItem(k) || "";
    if (!/^[a-f0-9]{32}$/.test(v)) {
      v = Array.from(crypto.getRandomValues(new Uint8Array(16)), (b) => b.toString(16).padStart(2, "0")).join("");
      localStorage.setItem(k, v);
    }
    navigator.sendBeacon("https://api.dokhaehanip.com/events", JSON.stringify({ ...o, vid: v }));
  } catch {}
}
