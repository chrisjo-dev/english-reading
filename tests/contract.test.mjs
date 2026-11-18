// node --test tests/contract.test.mjs : 같은 규칙을 여러 곳에 둔 코드가 같은 답을 내는지 본다.
// 위 메뉴 로그인 버튼은 두 곳에서 그린다: 지문 페이지(tools/gnb.py 의 SCRIPT)와 첫 화면(landing/src/lib/me.ts).
// 마이페이지 숫자는 assets/auth.js 의 streak 로 센다. 저장 키(dkh-auth, dkh-me, drill:v1)나
// 연속 학습일 규칙이 한 곳만 바뀌면 여기서 깨진다. 마크업이 같은지는 tests/test_login.py 의 HeaderMeTest 가 본다.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const { readMe } = await import('../landing/src/lib/me.ts');

// 이 기기 시간대의 고정 시각. 인자 없는 new Date() 만 이 시각을 돌려준다
function clock(y, m, d) {
  const now = new Date(y, m - 1, d, 12, 0, 0).getTime();
  return class extends Date {
    constructor(...a) { if (a.length) super(...a); else super(now); }
    static now() { return now; }
  };
}
function storeOf(obj) {
  return { getItem: (k) => (k in obj ? obj[k] : null), setItem: () => {}, removeItem: () => {} };
}
function state({ on = true, nick = '', days = [] } = {}) {
  const s = {};
  if (on) s['dkh-auth'] = '{}';
  if (nick) s['dkh-me'] = JSON.stringify({ n: nick });
  s['drill:v1'] = JSON.stringify({ items: {}, days });
  return s;
}

const GNB = (() => {
  const src = fs.readFileSync(new URL('../tools/gnb.py', import.meta.url), 'utf8');
  const m = src.match(/SCRIPT = r"""<script id="gnb-js">([\s\S]*?)<\/script>\n"""/);
  assert.ok(m, 'tools/gnb.py 에서 SCRIPT 를 찾지 못함');
  return m[1];
})();

// 지문 페이지 위 메뉴: SCRIPT 를 가짜 버튼에 돌려 그린 결과를 읽는다(시트 부분은 요소가 없어 바로 끝난다)
function gnbHeader(store, Date, path = '/en/2026-11-18/') {
  const kids = { '.gm-av': { textContent: '' }, '.gm-t': { textContent: '로그인' }, '.gm-b': { textContent: '', hidden: true } };
  const attrs = { 'aria-label': '로그인' }, cls = [];
  const me = { href: '/join/', classList: { add: (c) => cls.push(c) }, setAttribute: (k, v) => { attrs[k] = v; }, querySelector: (q) => kids[q] };
  const document = { getElementById: (id) => (id === 'gnb-me' ? me : null), documentElement: {} };
  vm.runInNewContext(GNB, { document, localStorage: storeOf(store), location: { pathname: path }, Date, JSON, String, encodeURIComponent });
  const n = /연속 (\d+)일/.exec(attrs['aria-label']);
  return {
    on: cls.includes('in'), href: me.href, streak: n ? Number(n[1]) : 0,
    initial: kids['.gm-av'].textContent, badge: kids['.gm-b'].hidden ? '' : kids['.gm-b'].textContent,
  };
}
function authStreak(days, Date) {
  const window = { DKH_AUTH_CONFIG: { supabaseUrl: '', supabaseAnonKey: '', kakaoClientId: '' } };
  vm.runInNewContext(fs.readFileSync(new URL('../assets/auth.js', import.meta.url), 'utf8'),
    { window, console, atob, URLSearchParams, Promise, JSON, Date, location: { pathname: '/' }, localStorage: storeOf({}) });
  return window.dkhAuth.streak(days).now;
}

const CASES = [
  [[2026, 11, 18], []],
  [[2026, 11, 18], ['2026-11-18']],
  [[2026, 11, 18], ['2026-11-17']],                            // 오늘 아직 안 했으면 어제부터
  [[2026, 11, 18], ['2026-11-16']],                            // 이틀 전에서 끊기면 0
  [[2026, 11, 18], ['2026-11-18', '2026-11-17', '2026-11-15']],
  [[2026, 11, 18], ['2026-11-14', '2026-11-17', '2026-11-16', '2026-11-16']], // 순서가 섞이고 겹쳐도
  [[2026, 12, 1], ['2026-11-29', '2026-11-30', '2026-12-01']], // 달이 바뀌어도
  [[2027, 1, 1], ['2026-12-30', '2026-12-31']],                // 해가 바뀌어도
];

test('연속 학습일: 지문 페이지 위 메뉴, 첫 화면, 마이페이지(auth.js)가 같은 수를 센다', () => {
  for (const [ymd, days] of CASES) {
    const D = clock(...ymd), s = state({ days });
    const g = gnbHeader(s, D), l = readMe(storeOf(s), new D()), a = authStreak(days, D);
    const at = `${ymd.join('-')} ${JSON.stringify(days)}`;
    assert.equal(l.streak, a, `첫 화면과 auth.js 가 다름: ${at}`);
    assert.equal(g.streak, a, `지문 페이지와 auth.js 가 다름: ${at}`);
    assert.equal(g.badge, a ? `🔥${a}` : '', `지문 페이지 배지: ${at}`);
  }
});

test('로그인 상태와 닉네임: 두 위 메뉴가 같은 저장 키를 읽는다', () => {
  const D = clock(2026, 11, 18);
  for (const nick of ['원상', '']) {
    const s = state({ nick, days: ['2026-11-18'] });
    const g = gnbHeader(s, D), l = readMe(storeOf(s), new D());
    assert.equal(g.on, true); assert.equal(l.on, true);
    assert.equal(g.href, '/me/');
    assert.equal(l.nick, nick);
    assert.equal(g.initial, nick ? nick.charAt(0) : '나'); // 첫 화면은 Nav.tsx 가 같은 규칙(nick.charAt(0) || "나")으로 그린다
  }
  const off = state({ on: false, nick: '원상', days: ['2026-11-18'] });
  const g = gnbHeader(off, D), l = readMe(storeOf(off), new D());
  assert.equal(g.on, false); assert.equal(l.on, false); assert.equal(l.streak, 0);
  assert.equal(g.href, '/join/?next=' + encodeURIComponent('/en/2026-11-18/'));
});

test('저장 키: 로그인 흐름이 쓰는 키와 위 메뉴가 읽는 키가 같다', () => {
  const auth = fs.readFileSync(new URL('../assets/auth.js', import.meta.url), 'utf8');
  assert.match(auth, /var STORAGE_KEY = "dkh-auth";/);
  assert.match(auth, /var DRILL_KEY = "drill:v1";/);
  assert.match(fs.readFileSync(new URL('../assets/drill.js', import.meta.url), 'utf8'), /var KEY = 'drill:v1'/);
  for (const f of ['../assets/join-callback.js', '../assets/me.js']) {
    assert.match(fs.readFileSync(new URL(f, import.meta.url), 'utf8'), /localStorage\.setItem\("dkh-me", JSON\.stringify\(\{ n: /, f);
  }
});
