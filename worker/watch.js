// 사이트 감시와 Slack 알림(Cloudflare cron). GitHub 예약 실행은 몇 시간씩 늦게 돌 때가 있어서
// (2026-11-18 catchup 이 5시간 늦음) 감시는 여기서 한다. 발행 워크플로 실패 알림은 .github/workflows/notify.yml 이 한다.
// - 5분마다: 첫 화면과 latest.json 이 열리는지. 두 번 연속 실패하면 "안 열림", 다시 열리면 "복구"를 한 번씩 보낸다.
// - 매일 08:40 KST: 오늘 지문이 언어마다 latest.json 에 올라왔는지. 빠진 언어가 있으면 보낸다.
// 상태는 KV(ALERTS)에 둔다. 비밀값: npx wrangler secret put SLACK_WEBHOOK_URL (없으면 아무것도 보내지 않는다)
const SITE = 'https://dokhaehanip.com';
const ACTIONS = 'https://github.com/chrisjo-dev/english-reading/actions';
export const DAILY = { en: '영어', ja: '일본어', de: '독일어' };
export const CRON_PUBLISHED = '40 23 * * *'; // 08:40 KST
const FAILS_TO_ALERT = 2;

export async function slack(env, text, fetchImpl = fetch) {
  if (!env.SLACK_WEBHOOK_URL) return false;
  try {
    const r = await fetchImpl(env.SLACK_WEBHOOK_URL, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text }),
    });
    return r.ok;
  } catch (e) {
    return false;
  }
}

function get(url, fetchImpl) {
  return fetchImpl(url, { redirect: 'follow', signal: AbortSignal.timeout(15000), headers: { 'Cache-Control': 'no-cache' } });
}

// 실패 이유를 돌려준다. 정상이면 빈 문자열
export async function probe(fetchImpl = fetch, now = Date.now()) {
  try {
    const home = await get(SITE + '/?watch=' + now, fetchImpl);
    if (!home.ok) return `첫 화면 HTTP ${home.status}`;
    if (!(await home.text()).includes('독해한입')) return '첫 화면 내용이 비어 있음';
    const latest = await get(SITE + '/latest.json?watch=' + now, fetchImpl);
    if (!latest.ok) return `latest.json HTTP ${latest.status}`;
    await latest.json();
    return '';
  } catch (e) {
    return '연결 실패(' + ((e && e.name) || 'error') + ')';
  }
}

export async function checkUp(env, fetchImpl = fetch, now = Date.now()) {
  const why = await probe(fetchImpl, now);
  let prev = { fails: 0, down: false };
  try { prev = { ...prev, ...JSON.parse((await env.ALERTS.get('up')) || '{}') }; } catch (e) {}
  let next;
  if (why) {
    next = { ...prev, fails: prev.fails + 1, why };
    if (!prev.down && next.fails >= FAILS_TO_ALERT) {
      next.down = true;
      next.since = now;
      await slack(env, `🔴 독해한입 사이트가 열리지 않아요: ${why}. 5분마다 다시 확인하고 열리면 알려 드릴게요. ${SITE}/`, fetchImpl);
    }
  } else {
    if (prev.down) {
      const min = Math.max(1, Math.round((now - (prev.since || now)) / 60000));
      await slack(env, `🟢 독해한입 사이트가 다시 열려요. 약 ${min}분 동안 열리지 않았어요(${prev.why || '이유 모름'}).`, fetchImpl);
    }
    next = { fails: 0, down: false };
  }
  if (JSON.stringify(next) !== JSON.stringify(prev)) await env.ALERTS.put('up', JSON.stringify(next));
  return next;
}

export function kstDate(now) {
  return new Date(now + 9 * 3600 * 1000).toISOString().slice(0, 10);
}

export async function checkPublished(env, fetchImpl = fetch, now = Date.now()) {
  const today = kstDate(now);
  let langs = null;
  try {
    const r = await get(SITE + '/latest.json?watch=' + now, fetchImpl);
    if (r.ok) langs = (await r.json()).langs || {};
  } catch (e) {}
  if (!langs) {
    await slack(env, `🟠 오늘(${today}) 발행 확인 실패: latest.json 을 읽지 못했어요. ${ACTIONS}`, fetchImpl);
    return ['?'];
  }
  const missing = Object.keys(DAILY).filter((l) => !(langs[l] && langs[l].latest === today));
  if (missing.length) {
    const list = missing.map((l) => `${DAILY[l]}(마지막 ${(langs[l] && langs[l].latest) || '없음'})`).join(', ');
    await slack(env, `🟠 오늘(${today}) 지문이 아직 안 올라온 언어: ${list}. 발행 기록: ${ACTIONS}`, fetchImpl);
  }
  return missing;
}

export async function scheduled(event, env) {
  if (event.cron === CRON_PUBLISHED) await checkPublished(env);
  else await checkUp(env);
}
