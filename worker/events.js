// 사이트 반응을 Supabase public.site_events 에 쌓는다(supabase/migrations/0006_site_events.sql).
// 받는 것: 오늘 주제 반응(topic_vote), 언어 추가 요청(lang_request), 기능 건의와 버그 제보 누름(feedback).
// 브라우저는 navigator.sendBeacon(text/plain)으로 보낸다. 사이트 출처만 받고, IP 마다 1분에 EVENTS_LIMIT 번까지만 받는다.
// 비밀값: npx wrangler secret put SUPABASE_SERVICE_ROLE_KEY. 브라우저에는 이 표의 권한이 없다.
const SUPABASE = 'https://kfprgssvigujxphfmlth.supabase.co/rest/v1/site_events?on_conflict=kind,vid,lang,day';
const SITE = 'https://dokhaehanip.com';
const MAX_BODY = 1024;
const VID = /^[a-f0-9]{32}$/;
const LANG = /^(en|ja|de)$/;
const DAY = /^20\d\d-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$/;
const SRC = /^[a-z]{1,12}$/;
const VALUE = {
  topic_vote: (v) => v === 'up' || v === 'down',
  feedback: (v) => v === 'idea' || v === 'bug',
  // 언어 이름(목록 또는 직접 적은 것). 제어 문자와 꺾쇠는 받지 않는다
  lang_request: (v) => v.length >= 1 && v.length <= 20 && !/[\u0000-\u001f\u007f<>]/.test(v),
};

function reply(status, origin) {
  const h = { 'Cache-Control': 'no-store' };
  if (origin) { h['Access-Control-Allow-Origin'] = origin; h.Vary = 'Origin'; }
  return new Response(null, { status, headers: h });
}

// 받은 값을 표의 한 줄로 바꾼다. 틀리면 null
export function row(o) {
  if (!o || typeof o !== 'object' || !VALUE[o.kind] || typeof o.vid !== 'string' || !VID.test(o.vid)) return null;
  const value = typeof o.value === 'string' ? o.value.trim() : '';
  if (!VALUE[o.kind](value)) return null;
  const r = { kind: o.kind, vid: o.vid, value, lang: null, day: null, level: null, src: null };
  if (o.kind === 'topic_vote') {
    if (!LANG.test(o.lang) || !DAY.test(o.day)) return null;
    r.lang = o.lang; r.day = o.day;
    if (o.level === 'a' || o.level === 'b') r.level = o.level;
  }
  if (typeof o.src === 'string' && SRC.test(o.src)) r.src = o.src;
  return r;
}

export async function events(request, env, fetchImpl = fetch) {
  const origin = env.SITE_ORIGIN || SITE;
  if (request.method !== 'POST') return reply(405);
  if (request.headers.get('Origin') !== origin) return reply(403);
  if (env.EVENTS_LIMIT) {
    const ip = request.headers.get('CF-Connecting-IP') || 'none';
    const { success } = await env.EVENTS_LIMIT.limit({ key: ip });
    if (!success) return reply(429, origin);
  }
  if (!env.SUPABASE_SERVICE_ROLE_KEY) return reply(500, origin);
  const text = await request.text();
  if (text.length > MAX_BODY) return reply(400, origin);
  let r;
  try { r = row(JSON.parse(text)); } catch { r = null; }
  if (!r) return reply(400, origin);
  const key = env.SUPABASE_SERVICE_ROLE_KEY;
  const headers = { apikey: key, 'Content-Type': 'application/json', Prefer: 'resolution=merge-duplicates,return=minimal' };
  if (!key.startsWith('sb_')) headers.Authorization = `Bearer ${key}`;  // 예전 JWT 형식 키
  // 다시 누르면(같은 방문자, 같은 지문) 값과 시각을 고친다
  let res;
  try {
    res = await fetchImpl(SUPABASE, { method: 'POST', headers, body: JSON.stringify({ ...r, at: new Date().toISOString() }) });
  } catch { return reply(502, origin); }
  return reply(res.ok ? 204 : 502, origin);
}
