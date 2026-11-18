// 독해한입 API Worker(api.dokhaehanip.com). 지금은 카카오 토큰 교환 하나만 한다. 사이트 자체는 GitHub Pages 가 낸다.
import { kakaoToken } from './kakao.js';

export default {
  async fetch(request, env) {
    const { pathname } = new URL(request.url);
    if (pathname === '/kakao/token') return kakaoToken(request, env);
    return new Response('Not Found', { status: 404, headers: { 'Cache-Control': 'no-store' } });
  },
};
