// node --test tests/mine.test.mjs : assets/mine.js 의 기록, 모으기, 파일로 옮기기
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

function load(store = {}, full) {
  const ls = { getItem: (k) => (k in store ? store[k] : null), removeItem: (k) => { delete store[k]; },
    setItem: (k, v) => { if (full && full(k)) throw new Error('quota'); store[k] = String(v); } };
  const ctx = { window: { addEventListener() {} }, localStorage: ls, console, navigator: {}, setTimeout,
    document: { addEventListener() {}, querySelectorAll: () => [] } };
  vm.runInNewContext(fs.readFileSync(new URL('../assets/mine.js', import.meta.url), 'utf8'), ctx);
  return { M: ctx.window.mineNotes, store };
}
const now = Date.now(), old = now - 30 * 864e5;
const seed = () => ({ 'mine:v1': JSON.stringify({
  'en/2026-11-24/b': { t: 'QR', u: now, n: 6, s: { 0: { v: '하나', st: false, e: 'One.' }, 1: { v: '', st: true, e: 'Two.' } } },
  'en/2026-10-20/b': { t: 'Old', u: old, s: { 2: { v: '셋', st: true, e: 'Three.' } } },
  'de/2026-11-23/a': { t: 'De', u: now, s: { 0: { v: '독', st: false, e: 'Eins.' } } } }) });
const plain = (x) => JSON.parse(JSON.stringify(x));

test('모으기: 언어, 최근 7일, 헷갈림, 날짜 범위', () => {
  const { M } = load(seed());
  assert.equal(M.size({}), 3);
  assert.equal(M.size({ lang: 'en', week: true }), 1);
  assert.equal(M.size({ lang: 'en', star: true }), 2);
  assert.deepEqual(plain(M.pick({ lang: 'en' }).map((d) => d.d)), ['2026-10-20', '2026-11-24']);
  assert.equal(M.size({ from: '2026-11-23', to: '2026-11-29' }), 2);
});

test('문장 고치기는 다른 값을 지우지 않고, 남은 것이 없으면 뺀다', () => {
  const { M } = load(seed());
  M.edit('en/2026-11-24/b', 1, (s) => { s.st = false; });
  assert.deepEqual(Object.keys(M.load()['en/2026-11-24/b'].s), ['0']);
  assert.equal(M.load()['en/2026-11-24/b'].u, now);  // 최근 7일 계산이 흔들리지 않는다
  M.edit('en/2026-11-24/b', 0, (s) => { s.v = ''; });
  assert.equal(M.load()['en/2026-11-24/b'], undefined);
  assert.ok(M.load()['de/2026-11-23/a']);
});

test('질문 글: 범위와 학습 언어', () => {
  const { M } = load(seed());
  const t = M.compose({ lang: 'en', id: 'en/2026-11-24/b' }, 'star', 'fix');
  assert.match(t, /2\. Two\.\n내 해석: \(아직 못 씀\) \(헷갈림\)/);
  assert.match(t, /3\. Three\./);
  assert.doesNotMatch(t, /독/);
});

test('내보낸 파일을 다른 기기에서 가져오면 그대로, 두 번 가져와도 늘지 않는다', () => {
  const a = load(seed()).M;
  a.addAi('en/2026-11-24/b', '답'); a.addAi('en/~', '묶음');
  const { M } = load();
  assert.deepEqual(plain(M.restore(a.dump())), { days: 3, answers: 2 });
  assert.deepEqual(plain(M.restore(a.dump())), { days: 0, answers: 0 });
  assert.equal(M.size({}), 3); assert.equal(M.aiCount({}), 2);
});

test('가져오기: 문장마다 합치고, 파일 시각이 미래여도 이 기기에 쓴 글을 덮지 않는다', () => {
  const file = load(seed()).M.dump();
  const { M } = load(seed());
  M.edit('en/2026-11-24/b', 0, (s) => { s.v = '새로'; });
  const f = JSON.parse(file), d = f.mine['en/2026-11-24/b'];
  d.u = d.m = now + 864e5; d.s[0].v = '다른 기기'; d.s[1].v = '채움'; d.s[5] = { v: '여섯', st: false, e: 'Six.' };
  assert.equal(M.restore(JSON.stringify(f)).days, 1);
  const s = M.load()['en/2026-11-24/b'].s;
  assert.deepEqual([s[0].v, s[1].v, s[5].v], ['새로', '채움', '여섯']);
});

test('가져오기: 모양이 다른 파일과 값은 받지 않는다', () => {
  const { M } = load();
  for (const bad of ['', 'x', '[]', 'null', '{"app":"other","mine":{}}', '{"app":"dokhaehanip-mine"}']) assert.equal(M.restore(bad), null);
  M.restore(JSON.stringify({ app: 'dokhaehanip-mine', mine: {
    '__proto__x': { s: { 0: { v: 'a' } } }, 'en/2026-11-24/c': { s: { 0: { v: 'a' } } },
    'en/2026-11-24/b': { t: 5, u: 9e15, n: '<b>', s: { 0: { v: 'ok', st: 'yes', e: {} }, x: { v: 'a' }, 1: null } } }, ai: { 'en/~': [{ v: 3 }, null, { v: ' ' }], 'zz': [{ v: 'a' }] } }));
  const all = M.load();
  assert.deepEqual(Object.keys(all), ['en/2026-11-24/b']);
  assert.deepEqual(plain(all['en/2026-11-24/b'].s), { 0: { v: 'ok', st: false, e: '' } });
  assert.ok(all['en/2026-11-24/b'].u <= Date.now());
  assert.deepEqual(plain(M.loadAi()), {});
});

test('저장 공간이 모자라면 반만 들어가지 않는다', () => {
  const src = load(seed()).M; src.addAi('en/~', '답');
  const { M, store } = load({}, (k) => k === 'mine:ai');
  assert.deepEqual(plain(M.restore(src.dump())), { failed: true });
  assert.equal(store['mine:v1'], undefined);
});

test('AI 답: 같은 지문에 여러 번 붙이고 하나만 지운다', () => {
  const { M } = load({ 'mine:ai': JSON.stringify({ 'en/~': [{ v: 'a', u: 1 }, { v: 'b', u: 2 }] }) });
  M.delAi('en/~', 1);
  assert.deepEqual(plain(M.loadAi()), { 'en/~': [{ v: 'b', u: 2 }] });
  M.delAi('en/~', 2);
  assert.deepEqual(plain(M.loadAi()), {});
});

test('기록이 사라진 지문에도 별표를 다시 켤 수 있다', () => {
  const { M } = load({ 'mine:v1': JSON.stringify({ 'en/2026-11-24/b': { t: 'QR', u: 5, n: 6, s: { 0: { v: '', st: true, e: 'One.' } } } }) });
  M.edit('en/2026-11-24/b', 0, (s) => { s.st = false; });
  assert.equal(M.load()['en/2026-11-24/b'], undefined);
  assert.equal(M.edit('en/2026-11-24/b', 0, (s) => { s.st = true; s.e = 'One.'; }, { t: 'QR', u: 5, n: 6 }), true);
  assert.deepEqual(plain(M.load()['en/2026-11-24/b'].s[0]), { v: '', st: true, e: 'One.' });
});

test('지난 주 복습에서 물으면 그 주 문장만', () => {
  const { M } = load(seed());
  const t = M.compose({ lang: 'en', from: '2026-10-19', to: '2026-10-25' }, 'week', 'fix');
  assert.match(t, /Three\./); assert.doesNotMatch(t, /One\./);
});

test('붙인 답 나누기: "N번"만 쓰고 소제목 번호는 문장 번호로 보지 않는다', () => {
  const src = fs.readFileSync(new URL('../assets/notes.js', import.meta.url), 'utf8');
  const part = vm.runInNewContext('(' + src.slice(src.indexOf('function part('), src.indexOf('  function aiHtml')) + ')');
  assert.equal(part('1번: 좋아요.\n2번: 시제.\n이어서.\n3번: x\n', 2), '2번: 시제.\n이어서.');
  assert.equal(part('1) 잘 잡은 것: a\n2) 짚을 것:\n- 2번: 시제\n3) 오늘 하나만: b', 2), '- 2번: 시제');
  assert.equal(part('1) 잘 잡은 것\n2) 짚을 것: 전반', 2), '');
  assert.equal(part('**1번 문장**\n1. 주어 찾기\n2. 동사 찾기', 2), '');
  assert.equal(part('12번: 열둘', 2), '');
});

// linewrite.js 를 흉내 낸 화면에서 돌려 저장만 본다
function passage(store) {
  const el = (x = {}) => { const h = {}; return Object.assign({ value: '', style: {}, attrs: {}, hidden: false, scrollHeight: 10, textContent: '', classList: { toggle() {}, contains: () => false, add() {}, remove() {} },
    addEventListener(n, f) { (h[n] ||= []).push(f); }, fire(n) { (h[n] || []).forEach((f) => f({})); }, focus() {}, blur() {}, scrollIntoView() {},
    setAttribute(k, v) { this.attrs[k] = v; }, getAttribute(k) { return this.attrs[k]; }, querySelector: () => el(), querySelectorAll: () => [el(), el()], appendChild() {}, remove() {} }, x); };
  const { M } = load(store);
  const ta = [el(), el()], st = [el(), el()], ids = {};
  const rows = [0, 1].map((i) => ({ querySelector: (q) => (q === '.lw textarea' ? ta[i] : q === '.lw-star' ? st[i] : q === '.lw-cmp' ? el() : null) }));
  const win = el({ mineNotes: M });
  const document = el({ documentElement: el(), body: el(), activeElement: null, createElement: () => el(), getElementById: (i) => (ids[i] ||= el()), querySelector: () => el({ textContent: 'QR' }) });
  vm.runInNewContext(fs.readFileSync(new URL('../assets/linewrite.js', import.meta.url), 'utf8'), { window: win, document, rows, location: { pathname: '/en/2026-11-24/' }, localStorage: { setItem() {} },
    isLevelA: () => false, sentenceText: (r) => ['One.', 'Two.'][rows.indexOf(r)], gaEvent() {}, getSelection: () => '', MutationObserver: class { observe() {} }, setTimeout: () => 0, clearTimeout() {}, matchMedia: null });
  return { M, ta, st, save: () => win.fire('pagehide') };
}
test('지문 저장은 이 탭에서 바꾼 칸만: 다른 탭이 푼 별표와 쓴 글, 다시 쓴 해석을 되돌리지 않는다', () => {
  const store = { 'mine:v1': JSON.stringify({ 'en/2026-11-24/b': { t: 'QR', u: 1, n: 2, s: { 0: { v: '', st: true, e: 'One.' } } } }) };
  const p = passage(store);
  p.M.edit('en/2026-11-24/b', 0, (s) => { s.st = false; s.v = '다른 탭'; s.r = { v: '다시', u: 2 }; });
  p.ta[1].value = '둘째'; p.ta[1].fire('input'); p.save();
  const s = plain(p.M.load()['en/2026-11-24/b'].s);
  assert.deepEqual(s[0], { v: '다른 탭', st: false, e: 'One.', r: { v: '다시', u: 2 } });
  assert.equal(s[1].v, '둘째');
  p.ta[1].value = ''; p.ta[1].fire('input'); p.st[0].fire('click'); p.save();
  const s2 = plain(p.M.load()['en/2026-11-24/b'].s);
  assert.equal(s2[1], undefined);
});
