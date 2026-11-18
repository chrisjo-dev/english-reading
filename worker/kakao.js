// 카카오 로그인 코드를 id_token 으로 바꿔 준다(릴리랑 worker/kakao.js 와 같은 방식).
// Client Secret 이 필요한 단계라 브라우저 대신 여기서 한다. 돌려주는 것은 id_token 하나뿐이다.
// 세션은 브라우저가 Supabase signInWithIdToken 으로 만든다.
// 비밀값: npx wrangler secret put KAKAO_REST_API_KEY, KAKAO_CLIENT_SECRET. 저장소에는 넣지 않는다.
// 사이트(dokhaehanip.com)와 주소가 달라서(api.dokhaehanip.com) CORS 를 사이트 한 곳에만 연다.
const TOKEN_URL = 'https://kauth.kakao.com/oauth/token';
const SITE = 'https://dokhaehanip.com';
const MAX_BODY = 2048;
const CODE_RE = /^[A-Za-z0-9_-]{1,512}$/;

function cors(origin) {
  return {
    'Access-Control-Allow-Origin': origin,
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age': '600',
    Vary: 'Origin',
  };
}

function json(status, obj, origin) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store', ...(origin ? cors(origin) : {}) },
  });
}

export async function kakaoToken(request, env, fetchImpl = fetch) {
  const origin = env.SITE_ORIGIN || SITE;
  const ok = request.headers.get('Origin') === origin;
  if (request.method === 'OPTIONS') {
    return ok ? new Response(null, { status: 204, headers: cors(origin) }) : json(403, { error: 'forbidden' });
  }
  if (request.method !== 'POST') return json(405, { error: 'method_not_allowed' }, ok ? origin : null);
  if (!ok) return json(403, { error: 'forbidden' });
  if (!env.KAKAO_REST_API_KEY || !env.KAKAO_CLIENT_SECRET) return json(500, { error: 'not_configured' }, origin);

  const text = await request.text();
  if (text.length > MAX_BODY) return json(400, { error: 'bad_request' }, origin);
  let code;
  try { code = JSON.parse(text).code; } catch { return json(400, { error: 'bad_request' }, origin); }
  if (typeof code !== 'string' || !CODE_RE.test(code)) return json(400, { error: 'bad_request' }, origin);

  let res;
  try {
    res = await fetchImpl(TOKEN_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8' },
      body: new URLSearchParams({
        grant_type: 'authorization_code',
        client_id: env.KAKAO_REST_API_KEY,
        client_secret: env.KAKAO_CLIENT_SECRET,
        redirect_uri: origin + '/join/callback/',
        code,
      }),
    });
  } catch { return json(400, { error: 'exchange_failed' }, origin); }
  if (!res.ok) return json(400, { error: 'exchange_failed' }, origin);
  let data;
  try { data = await res.json(); } catch { return json(400, { error: 'exchange_failed' }, origin); }
  if (!data || typeof data.id_token !== 'string' || !data.id_token) return json(400, { error: 'exchange_failed' }, origin);
  return json(200, { id_token: data.id_token }, origin);
}
