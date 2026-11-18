// 위 메뉴 로그인 버튼(시안 design/kakao-login K15)이 이 기기 저장값에서 읽는 상태.
// 지문 페이지는 tools/gnb.py 의 SCRIPT 가 같은 규칙으로 그린다. 둘이 같은 답을 내는지는 tests/contract.test.mjs 가 본다.
// - 로그인 상태(dkh-auth), 닉네임(dkh-me), 공부한 날(drill:v1 의 days)
// - 연속 학습일: 오늘(또는 아직 안 했으면 어제)부터 거꾸로 이어진 날 수. assets/auth.js 의 streak().now 와 같다.
export type Me = { on: boolean; nick: string; streak: number };
type Store = Pick<Storage, "getItem">;

function ymd(t: Date) {
  return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
}

// store 를 주지 않으면 브라우저 localStorage 를 쓴다(저장소를 막은 브라우저에서 접근이 실패해도 로그아웃 상태로 본다)
export function readMe(store?: Store, today: Date = new Date()): Me {
  try {
    const s = store ?? window.localStorage;
    const on = s.getItem("dkh-auth") !== null;
    if (!on) return { on, nick: "", streak: 0 };
    const nick = String((JSON.parse(s.getItem("dkh-me") || "null") || {}).n || "");
    const days: string[] = (JSON.parse(s.getItem("drill:v1") || "null") || {}).days || [];
    const set = new Set(days);
    const d = new Date(today.getTime());
    if (!set.has(ymd(d))) d.setDate(d.getDate() - 1);
    let n = 0;
    while (set.has(ymd(d))) {
      n++;
      d.setDate(d.getDate() - 1);
    }
    return { on, nick, streak: n };
  } catch {
    return { on: false, nick: "", streak: 0 };
  }
}
