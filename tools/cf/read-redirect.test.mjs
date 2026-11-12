// Worker fetch 핸들러를 직접 불러 상태와 Location 을 확인한다. 실행: node --test tools/cf/read-redirect.test.mjs
import test from "node:test";
import assert from "node:assert/strict";
import vm from "node:vm";
import worker, { MAX, page } from "./read-redirect.js";

const CHROME = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1";
const HTML = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8";
const req = (path, { method = "GET", accept = HTML, ua = CHROME } = {}) =>
  worker.fetch(new Request("https://read.wspace.ai.kr" + path, { method, headers: { accept, "user-agent": ua } }));

test("브라우저 HTML 은 200 이동 페이지", async () => {
  const r = await req("/en/2026-11-12/?level=a");
  assert.equal(r.status, 200);
  assert.match(r.headers.get("content-type"), /text\/html/);
  assert.equal(r.headers.get("x-robots-tag"), "noindex");
  const body = await r.text();
  assert.match(body, /<meta name="robots" content="noindex">/);
  assert.match(body, /<link rel="canonical" href="https:\/\/dokhaehanip\.com\/en\/2026-11-12\/\?level=a">/);
  assert.match(body, /<a href="https:\/\/dokhaehanip\.com\/en\/2026-11-12\/\?level=a">/);
});

for (const [name, path, opt, loc] of [
  ["Googlebot", "/en/2026-11-12/", { ua: "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)" }, "https://dokhaehanip.com/en/2026-11-12/"],
  ["Yeti", "/", { ua: "Mozilla/5.0 (compatible; Yeti/1.1; +https://naver.me/spd)" }, "https://dokhaehanip.com/"],
  ["GPTBot", "/ja/", { ua: "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; GPTBot/1.2" }, "https://dokhaehanip.com/ja/"],
  ["mp3", "/en/2026-11-12/audio/s1.mp3", { accept: "*/*" }, "https://dokhaehanip.com/en/2026-11-12/audio/s1.mp3"],
  ["sitemap", "/sitemap.xml", { accept: "application/xml" }, "https://dokhaehanip.com/sitemap.xml"],
  ["HEAD", "/en/", { method: "HEAD" }, "https://dokhaehanip.com/en/"],
  ["쿼리 유지", "/en/2026-10-29/?vote=up&from=email", { ua: "Mozilla/5.0 (compatible; bingbot/2.0)" }, "https://dokhaehanip.com/en/2026-10-29/?vote=up&from=email"],
  ["이미지", "/en/2026-11-12/thumb.png", { accept: "image/avif,image/webp,*/*" }, "https://dokhaehanip.com/en/2026-11-12/thumb.png"],
]) {
  test(`${name} 는 301`, async () => {
    const r = await req(path, opt);
    assert.equal(r.status, 301);
    assert.equal(r.headers.get("location"), loc);
  });
}

// 이동 페이지의 스크립트를 가짜 localStorage 로 돌려 location.replace 주소를 받는다
function run(target, store) {
  const html = page(target);
  const js = html.match(/<script>([\s\S]*?)<\/script>/)[1];
  const keys = Object.keys(store);
  let to = null;
  const ctx = {
    localStorage: { get length() { return keys.length; }, key: (i) => keys[i], getItem: (k) => (k in store ? store[k] : null) },
    location: { replace: (u) => { to = u; } },
    TextEncoder, btoa, String, JSON,
  };
  vm.runInNewContext(js, ctx);
  return to;
}
const decode = (u) => JSON.parse(Buffer.from(u.split("#mig=")[1].replace(/-/g, "+").replace(/_/g, "/"), "base64").toString("utf8"));

test("기록이 없으면 해시 없이 이동", () => {
  assert.equal(run("https://dokhaehanip.com/en/", { other: "x" }), "https://dokhaehanip.com/en/");
});

test("기록이 있으면 #mig= 로 정해진 키만", () => {
  const to = run("https://dokhaehanip.com/en/?a=1", { "drill:v1": '{"猫":1}', "read_level:de": "a", "vote:en/2026-11-01": "up", other: "x" });
  assert.ok(to.startsWith("https://dokhaehanip.com/en/?a=1#mig="));
  assert.deepEqual(decode(to), { "drill:v1": '{"猫":1}', "read_level:de": "a", "vote:en/2026-11-01": "up" });
});

test("너무 크면 drill:v1 은 빼고 나머지만", () => {
  const to = run("https://dokhaehanip.com/", { "drill:v1": "x".repeat(MAX), read_speed: "1.2" });
  assert.deepEqual(decode(to), { read_speed: "1.2" });
});

test("drill:v1 하나만 있고 너무 크면 해시 없이", () => {
  assert.equal(run("https://dokhaehanip.com/", { "drill:v1": "x".repeat(MAX) }), "https://dokhaehanip.com/");
});

test("보내는 쪽과 받는 쪽(tools/migrate.py) 왕복", async () => {
  const { execFileSync } = await import("node:child_process");
  const JS = execFileSync("python3", ["-c", "import sys; sys.path.insert(0, 'tools'); import migrate; print(migrate.JS, end='')"], { encoding: "utf8" });
  const src = { "drill:v1": '{"단어":{"n":2}}', "drill:pref": '{"m":1}', read_level: "a", "read_level:ja": "b", "lily.justListen": "1" };
  const to = run("https://dokhaehanip.com/ja/2026-11-01/", src);
  const u = new URL(to), store = new Map([["read_level:ja", "a"]]);
  let replaced = null;
  vm.runInNewContext(JS, {
    location: { hash: u.hash, pathname: u.pathname, search: u.search },
    localStorage: { getItem: (k) => (store.has(k) ? store.get(k) : null), setItem: (k, v) => store.set(k, v) },
    history: { replaceState: (a, b, x) => { replaced = x; } },
    atob, TextDecoder, Uint8Array, JSON, Object,
  });
  assert.deepEqual(Object.fromEntries(store), { ...src, "read_level:ja": "a" });
  assert.equal(replaced, "/ja/2026-11-01/");
});
