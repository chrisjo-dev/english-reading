// node --test worker/  (의존 없음)
import test from 'node:test';
import assert from 'node:assert/strict';
import { events, row } from './events.js';

const SITE = 'https://dokhaehanip.com';
const VID = 'a'.repeat(32);
const env = { SUPABASE_SERVICE_ROLE_KEY: 'sb_secret_x' };
const req = (body, origin = SITE, method = 'POST') => new Request('https://api.dokhaehanip.com/events', {
  method, headers: { Origin: origin, 'Content-Type': 'text/plain;charset=UTF-8', 'CF-Connecting-IP': '1.2.3.4' }, body,
});
const vote = { kind: 'topic_vote', vid: VID, lang: 'en', day: '2026-11-19', value: 'up', level: 'a', src: 'page' };

test('주제 반응은 같은 방문자, 같은 지문이면 덮어쓰도록 보낸다', async () => {
  const calls = [];
  const r = await events(req(JSON.stringify(vote)), env, async (url, init) => { calls.push({ url, init }); return new Response(null, { status: 201 }); });
  assert.equal(r.status, 204);
  assert.equal(r.headers.get('Access-Control-Allow-Origin'), SITE);
  assert.match(calls[0].url, /on_conflict=kind,vid,lang,day$/);
  assert.match(calls[0].init.headers.Prefer, /resolution=merge-duplicates/);
  assert.equal(calls[0].init.headers.apikey, 'sb_secret_x');
  assert.equal(calls[0].init.headers.Authorization, undefined);  // 새 형식 키는 apikey 만
  const sent = JSON.parse(calls[0].init.body);
  assert.deepEqual({ ...sent, at: undefined }, { kind: 'topic_vote', vid: VID, value: 'up', lang: 'en', day: '2026-11-19', level: 'a', src: 'page', at: undefined });
});

test('다른 출처, GET, 비밀값 없음, 횟수 초과는 DB 를 부르지 않는다', async () => {
  const no = async () => { throw new Error('should not call'); };
  assert.equal((await events(req(JSON.stringify(vote), 'https://evil.example'), env, no)).status, 403);
  assert.equal((await events(new Request('https://api.dokhaehanip.com/events', { headers: { Origin: SITE } }), env, no)).status, 405);
  assert.equal((await events(req(JSON.stringify(vote)), {}, no)).status, 500);
  const limited = { ...env, EVENTS_LIMIT: { limit: async ({ key }) => ({ success: key !== '1.2.3.4' }) } };
  assert.equal((await events(req(JSON.stringify(vote)), limited, no)).status, 429);
});

test('틀린 값은 400', async () => {
  const no = async () => { throw new Error('should not call'); };
  const bad = [
    'nope', JSON.stringify({ ...vote, kind: 'drop' }), JSON.stringify({ ...vote, vid: 'x' }), JSON.stringify({ ...vote, value: 'meh' }),
    JSON.stringify({ ...vote, lang: 'fr' }), JSON.stringify({ ...vote, day: '2026-13-01' }), JSON.stringify({ ...vote, day: undefined }),
    JSON.stringify({ kind: 'lang_request', vid: VID, value: '<script>' }), JSON.stringify({ kind: 'lang_request', vid: VID, value: 'x'.repeat(21) }),
    JSON.stringify({ kind: 'feedback', vid: VID, value: 'other' }), 'x'.repeat(2000),
  ];
  for (const b of bad) assert.equal((await events(req(b), env, no)).status, 400, b.slice(0, 40));
});

test('언어 요청과 건의는 언어, 날짜 없이 한 줄씩', () => {
  assert.deepEqual(row({ kind: 'lang_request', vid: VID, value: ' 스페인어 ', lang: 'en', day: '2026-11-19', src: 'landing' }),
    { kind: 'lang_request', vid: VID, value: '스페인어', lang: null, day: null, level: null, src: 'landing' });
  assert.equal(row({ kind: 'feedback', vid: VID, value: 'bug', src: 'Bad Src!' }).src, null);
});

test('DB 가 거절하면 502', async () => {
  const r = await events(req(JSON.stringify(vote)), env, async () => new Response('x', { status: 400 }));
  assert.equal(r.status, 502);
});
