// node --test worker/  (의존 없음)
import test from 'node:test';
import assert from 'node:assert/strict';
import worker from './index.js';
import { kakaoToken } from './kakao.js';

const SITE = 'https://dokhaehanip.com';
const env = { KAKAO_REST_API_KEY: 'k', KAKAO_CLIENT_SECRET: 's' };
const req = (method, body, origin = SITE) => new Request('https://api.dokhaehanip.com/kakao/token', {
  method, headers: { Origin: origin, 'Content-Type': 'application/json' }, body,
});

test('preflight는 사이트 주소에만 열린다', async () => {
  const r = await kakaoToken(req('OPTIONS'), env);
  assert.equal(r.status, 204);
  assert.equal(r.headers.get('Access-Control-Allow-Origin'), SITE);
  const bad = await kakaoToken(req('OPTIONS', undefined, 'https://evil.example'), env);
  assert.equal(bad.status, 403);
  assert.equal(bad.headers.get('Access-Control-Allow-Origin'), null);
});

test('다른 출처의 POST는 거부하고 카카오를 부르지 않는다', async () => {
  let called = false;
  const r = await kakaoToken(req('POST', '{"code":"abc"}', 'https://evil.example'), env, async () => { called = true; });
  assert.equal(r.status, 403);
  assert.equal(called, false);
});

test('비밀값이 없으면 not_configured', async () => {
  const r = await kakaoToken(req('POST', '{"code":"abc"}'), {});
  assert.equal(r.status, 500);
});

test('잘못된 code는 400', async () => {
  for (const b of ['nope', '{"code":"a b"}', '{"code":1}', JSON.stringify({ code: 'x'.repeat(3000) })]) {
    const r = await kakaoToken(req('POST', b), env, async () => { throw new Error('should not call'); });
    assert.equal(r.status, 400, b.slice(0, 20));
  }
});

test('성공하면 id_token만 돌려주고 redirect_uri는 사이트 콜백이다', async () => {
  let sent;
  const r = await kakaoToken(req('POST', '{"code":"abc_DEF-1"}'), env, async (url, init) => {
    sent = Object.fromEntries(new URLSearchParams(init.body));
    return new Response(JSON.stringify({ id_token: 'idt', access_token: 'at', refresh_token: 'rt' }));
  });
  assert.equal(r.status, 200);
  assert.deepEqual(await r.json(), { id_token: 'idt' });
  assert.equal(r.headers.get('Access-Control-Allow-Origin'), SITE);
  assert.equal(sent.redirect_uri, SITE + '/join/callback/');
  assert.equal(sent.client_secret, 's');
});

test('카카오가 실패하거나 id_token이 없으면 400', async () => {
  const a = await kakaoToken(req('POST', '{"code":"abc"}'), env, async () => new Response('x', { status: 401 }));
  const b = await kakaoToken(req('POST', '{"code":"abc"}'), env, async () => new Response('{"access_token":"at"}'));
  assert.equal(a.status, 400);
  assert.equal(b.status, 400);
});

test('다른 경로는 404', async () => {
  const r = await worker.fetch(new Request('https://api.dokhaehanip.com/x'), env);
  assert.equal(r.status, 404);
});
