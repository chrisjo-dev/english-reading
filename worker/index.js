// 독해한입 API Worker(api.dokhaehanip.com). 카카오 토큰 교환과 사이트 감시(watch.js, cron)를 한다. 사이트 자체는 GitHub Pages 가 낸다.
import { kakaoToken } from './kakao.js';
import { scheduled } from './watch.js';

export default {
  async fetch(request, env) {
    const { pathname } = new URL(request.url);
    if (pathname === '/kakao/token') return kakaoToken(request, env);
    return new Response('Not Found', { status: 404, headers: { 'Cache-Control': 'no-store' } });
  },
  async scheduled(event, env, ctx) {
    ctx.waitUntil(scheduled(event, env));
  },
};
