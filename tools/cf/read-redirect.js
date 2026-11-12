// 예전 주소 read.wspace.ai.kr/* 를 받는 Cloudflare Worker(모듈 형식). 배포와 되돌리기는 tools/cf/README.md.
// - 사람이 여는 HTML 페이지(GET, Accept 에 text/html, 봇 아님): 작은 HTML 을 돌려준다. 그 페이지가 이 주소의 학습 기록
//   (localStorage)을 읽어 있으면 새 주소 + 경로 + 쿼리 + #mig=<base64url(JSON)> 로, 없으면 새 주소 + 경로 + 쿼리로 옮긴다.
//   새 주소의 머리 스크립트(tools/migrate.py)가 #mig= 를 받아 없는 키만 넣고 # 을 지운다.
// - 그 밖(봇, 이미지, 음성, xml, json, HEAD 등): 301 로 새 주소 + 경로 + 쿼리.
const NEW = "https://dokhaehanip.com";
// 받는 쪽 tools/migrate.py 의 KEYS, PREFIXES 와 같아야 한다(tools/cf/read-redirect.test.mjs 가 확인)
export const KEYS = ["drill:v1", "drill:pref", "read_speed", "read_level", "lily.justListen"];
export const PREFIXES = ["read_level:", "vote:"];
// 인코딩한 길이가 이보다 크면 가장 큰 drill:v1 은 빼고 나머지만 넘긴다(주소 길이 한도 대비)
export const MAX = 200000;
const BOT = /bot|crawl|spider|slurp|externalhit|scrap|preview|yeti|daumoa|daum\/|gptbot|claudebot|perplexity|google-|headless|lighthouse/i;

const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

export function page(target) {
  const cfg = JSON.stringify({ to: target, keys: KEYS, prefixes: PREFIXES, max: MAX }).replace(/</g, "\\u003c");
  const t = esc(target);
  return `<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex"><title>독해한입 새 주소로 이동</title><link rel="canonical" href="${t}">
<script>
(function () {
  var c = ${cfg}, data = {}, n = 0;
  try {
    for (var i = 0; i < localStorage.length; i++) {
      var k = localStorage.key(i), ok = c.keys.indexOf(k) >= 0;
      for (var j = 0; j < c.prefixes.length; j++) if (k.indexOf(c.prefixes[j]) === 0) ok = true;
      if (ok) { var v = localStorage.getItem(k); if (v !== null) { data[k] = v; n++; } }
    }
  } catch (e) { n = 0; }
  function enc(o) {
    var b = new TextEncoder().encode(JSON.stringify(o)), s = "";
    for (var i = 0; i < b.length; i += 8192) s += String.fromCharCode.apply(null, b.subarray(i, i + 8192));
    return btoa(s).replace(/\\+/g, "-").replace(/\\//g, "_").replace(/=+$/, "");
  }
  var to = c.to;
  try {
    if (n) {
      var e = enc(data);
      if (e.length > c.max && "drill:v1" in data) { delete data["drill:v1"]; n--; e = n ? enc(data) : ""; }
      if (e && e.length <= c.max) to += "#mig=" + e;
    }
  } catch (e2) {}
  location.replace(to);
})();
</script></head>
<body><p>독해한입 주소가 바뀌었어요. <a href="${t}">새 주소로 이동</a></p></body></html>
`;
}

export default {
  async fetch(request) {
    const url = new URL(request.url);
    const target = NEW + url.pathname + url.search;
    const accept = request.headers.get("accept") || "";
    const ua = request.headers.get("user-agent") || "";
    if (request.method === "GET" && accept.includes("text/html") && !BOT.test(ua)) {
      return new Response(page(target), {
        status: 200,
        headers: {
          "content-type": "text/html; charset=utf-8",
          "cache-control": "no-store",
          "x-robots-tag": "noindex",
          vary: "accept, user-agent",
        },
      });
    }
    return new Response(null, { status: 301, headers: { location: target, "cache-control": "public, max-age=3600" } });
  },
};
