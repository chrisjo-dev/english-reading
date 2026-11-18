// node --test tests/auth.test.mjs : assets/auth.js 의 기록 합치기와 연속 학습일
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

function load(config) {
  const store = {};
  const window = { DKH_AUTH_CONFIG: config };
  const ctx = { window, console, atob, URLSearchParams, Promise, JSON, Date, location: { pathname: '/en/2026-11-17/' },
    localStorage: { getItem: (k) => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); }, removeItem: (k) => { delete store[k]; } } };
  vm.runInNewContext(fs.readFileSync(new URL('../assets/auth.js', import.meta.url), 'utf8'), ctx);
  return { A: window.dkhAuth, store };
}
const OFF = { supabaseUrl: '', supabaseAnonKey: '', kakaoClientId: '' };
const anon = 'x.' + Buffer.from(JSON.stringify({ role: 'anon' })).toString('base64') + '.y';
const svc = 'x.' + Buffer.from(JSON.stringify({ role: 'service_role' })).toString('base64') + '.y';

test('설정이 비면 ready=false, 세션 없음', () => {
  const { A } = load(OFF);
  assert.equal(A.ready, false);
  assert.equal(A.hasSession(), false);
});

test('anon 키만 받는다', () => {
  assert.equal(load({ supabaseUrl: 'https://abc.supabase.co', supabaseAnonKey: anon }).A.ready, true);
  const err = console.error; console.error = () => {};
  assert.equal(load({ supabaseUrl: 'https://abc.supabase.co', supabaseAnonKey: svc }).A.ready, false);
  assert.equal(load({ supabaseUrl: 'https://abc.supabase.co', supabaseAnonKey: 'sb_secret_x' }).A.ready, false);
  console.error = err;
});

test('합치기: 같은 단어는 나중에 고친 쪽, 없는 쪽은 그대로, 날짜는 합집합', () => {
  const { A } = load(OFF);
  const local = { items: { a: { w: 'a', t: '2026-11-18T01:00:00Z', due: 'L' }, b: { w: 'b' } }, days: ['2026-11-18', '2026-11-16'] };
  const remote = { items: { a: { w: 'a', t: '2026-11-17T01:00:00Z', due: 'R' }, c: { w: 'c' }, b: { w: 'b', t: '2026-11-10T00:00:00Z', due: 'R' } }, days: ['2026-11-17', '2026-11-16', 'bad'] };
  const m = A.merge(local, remote);
  assert.equal(m.items.a.due, 'L');
  assert.equal(m.items.b.due, 'R'); // 시간이 있는 서버 기록이 시간 없는 옛 기록보다 새것
  assert.ok(m.items.c);
  assert.deepEqual([...m.days], ['2026-11-16', '2026-11-17', '2026-11-18']);
  assert.deepEqual(Object.keys(A.merge(null, undefined).items), []);
});

test('연속 학습일: 오늘 또는 어제부터 이어진 날, 최고 기록', () => {
  const { A } = load(OFF);
  const pad = (n) => String(n).padStart(2, '0');
  const ago = (n) => { const d = new Date(); d.setDate(d.getDate() - n); return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`; };
  assert.deepEqual({ ...A.streak([ago(0), ago(1), ago(2), ago(5)]) }, { now: 3, best: 3 });
  assert.equal(A.streak([ago(1), ago(2)]).now, 2); // 오늘 아직 안 했으면 어제까지
  assert.equal(A.streak([ago(2)]).now, 0);
  assert.deepEqual({ ...A.streak([]) }, { now: 0, best: 0 });
});

test('safeNext 는 같은 사이트 경로와 #drill 만', () => {
  const { A } = load(OFF);
  assert.equal(A.safeNext('/en/2026-11-17/#drill'), '/en/2026-11-17/#drill');
  for (const bad of ['https://evil.example', '//evil.example', '/a/../b', '/a#x', 'javascript:alert(1)', 5]) assert.equal(A.safeNext(bad), '/');
  assert.equal(A.joinUrl('/en/2026-11-17/#drill', 'entry'), '/join/?next=%2Fen%2F2026-11-17%2F%23drill&from=entry');
});
