// 독해한입 API Worker(api.dokhaehanip.com). 카카오 토큰 교환, 사이트 반응 저장(events.js), 사이트 감시(watch.js, cron)를 한다. 사이트 자체는 GitHub Pages 가 낸다.
import { kakaoToken } from './kakao.js';
import { events } from './events.js';
import { scheduled } from './watch.js';

export default {
  async fetch(request, env) {
    const { pathname } = new URL(request.url);
    if (pathname === '/kakao/token') return kakaoToken(request, env);
    if (pathname === '/events') return events(request, env);
    return new Response('Not Found', { status: 404, headers: { 'Cache-Control': 'no-store' } });
  },
  async scheduled(event, env, ctx) {
    ctx.waitUntil(scheduled(event, env));
  },
};
