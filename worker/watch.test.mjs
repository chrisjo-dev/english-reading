// node --test worker/watch.test.mjs : 사이트 감시와 Slack 알림(watch.js)
import test from 'node:test';
import assert from 'node:assert/strict';
import { checkUp, checkPublished, kstDate, CRON_PUBLISHED, scheduled } from './watch.js';

const HOOK = 'https://hooks.slack.example/T/B/x';
function kv() {
  const m = new Map();
  return { get: async (k) => (m.has(k) ? m.get(k) : null), put: async (k, v) => { m.set(k, v); }, m };
}
// site: { home: 200|500|'throw', latest: {...} | 500 }
function fakeFetch(site, sent) {
  return async (url, opts = {}) => {
    if (url === HOOK) { sent.push(JSON.parse(opts.body).text); return new Response('ok'); }
    if (url.startsWith('https://dokhaehanip.com/?')) {
      if (site.home === 'throw') throw Object.assign(new Error('timeout'), { name: 'TimeoutError' });
      return new Response(site.home === 200 ? '<title>독해한입</title>' : 'err', { status: site.home });
    }
    if (url.startsWith('https://dokhaehanip.com/latest.json?')) {
      return typeof site.latest === 'number' ? new Response('x', { status: site.latest }) : new Response(JSON.stringify(site.latest));
    }
    throw new Error('unexpected ' + url);
  };
}
const T0 = Date.UTC(2026, 10, 18, 3, 0); // 2026-11-18 12:00 KST

test('한 번 실패는 알리지 않고, 두 번 연속이면 한 번만, 복구도 한 번만 알린다', async () => {
  const env = { SLACK_WEBHOOK_URL: HOOK, ALERTS: kv() }, sent = [];
  const site = { home: 500, latest: { langs: {} } };
  await checkUp(env, fakeFetch(site, sent), T0);
  assert.equal(sent.length, 0);
  await checkUp(env, fakeFetch(site, sent), T0 + 5 * 60000);
  assert.equal(sent.length, 1);
  assert.match(sent[0], /열리지 않아요: 첫 화면 HTTP 500/);
  await checkUp(env, fakeFetch(site, sent), T0 + 10 * 60000);
  assert.equal(sent.length, 1); // 계속 다운이어도 다시 보내지 않는다
  site.home = 200;
  await checkUp(env, fakeFetch(site, sent), T0 + 20 * 60000);
  assert.equal(sent.length, 2);
  assert.match(sent[1], /다시 열려요\. 약 15분/);
  await checkUp(env, fakeFetch(site, sent), T0 + 25 * 60000);
  assert.equal(sent.length, 2);
});

test('중간에 한 번 살아나면 연속 실패 수를 다시 센다', async () => {
  const env = { SLACK_WEBHOOK_URL: HOOK, ALERTS: kv() }, sent = [];
  const site = { home: 'throw', latest: { langs: {} } };
  await checkUp(env, fakeFetch(site, sent), T0);
  site.home = 200;
  await checkUp(env, fakeFetch(site, sent), T0 + 1);
  site.home = 'throw';
  await checkUp(env, fakeFetch(site, sent), T0 + 2);
  assert.equal(sent.length, 0);
  await checkUp(env, fakeFetch(site, sent), T0 + 3);
  assert.match(sent[0], /연결 실패\(TimeoutError\)/);
});

test('정상일 때는 KV 에 쓰지 않는다(무료 쓰기 한도)', async () => {
  const env = { SLACK_WEBHOOK_URL: HOOK, ALERTS: kv() }, sent = [];
  let puts = 0; const put = env.ALERTS.put; env.ALERTS.put = async (k, v) => { puts++; return put(k, v); };
  for (let i = 0; i < 3; i++) await checkUp(env, fakeFetch({ home: 200, latest: { langs: {} } }, sent), T0 + i);
  assert.equal(puts, 0);
  assert.equal(sent.length, 0);
});

test('오늘 지문 확인: 빠진 언어만 알린다', async () => {
  const sent = [], env = { SLACK_WEBHOOK_URL: HOOK, ALERTS: kv() };
  const today = kstDate(T0);
  assert.equal(today, '2026-11-18');
  const all = { langs: { en: { latest: today }, ja: { latest: today }, de: { latest: today } } };
  assert.deepEqual(await checkPublished(env, fakeFetch({ home: 200, latest: all }, sent), T0), []);
  assert.equal(sent.length, 0);
  const some = { langs: { en: { latest: today }, ja: { latest: '2026-11-17' } } };
  assert.deepEqual(await checkPublished(env, fakeFetch({ home: 200, latest: some }, sent), T0), ['ja', 'de']);
  assert.match(sent[0], /일본어\(마지막 2026-11-17\), 독일어\(마지막 없음\)/);
  await checkPublished(env, fakeFetch({ home: 200, latest: 503 }, sent), T0);
  assert.match(sent[1], /latest\.json 을 읽지 못했어요/);
});

test('KST 날짜는 자정 경계에서 바뀐다', () => {
  assert.equal(kstDate(Date.UTC(2026, 10, 17, 14, 59)), '2026-11-17');
  assert.equal(kstDate(Date.UTC(2026, 10, 17, 15, 0)), '2026-11-18');
});

test('웹훅이 없으면 아무것도 보내지 않고, cron 에 따라 할 일을 고른다', async () => {
  const env = { ALERTS: kv() };
  const orig = globalThis.fetch, urls = [];
  globalThis.fetch = async (url) => { urls.push(url); return new Response('err', { status: 500 }); };
  try {
    await scheduled({ cron: '*/5 * * * *' }, env);
    await scheduled({ cron: '*/5 * * * *' }, env);
    await scheduled({ cron: CRON_PUBLISHED }, env);
  } finally { globalThis.fetch = orig; }
  assert.ok(urls.every((u) => u.startsWith('https://dokhaehanip.com/')));
  assert.equal(urls.filter((u) => u.includes('latest.json')).length, 1); // 5분 점검 두 번은 첫 화면에서 멈춤, 08:40 점검 한 번
  assert.equal(JSON.parse(env.ALERTS.m.get('up')).down, true);
});
