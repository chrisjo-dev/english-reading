// 사이트 주소. 도메인을 옮길 때는 여기 한 곳과 tools/langs.py 의 SITE 를 같이 바꾼다.
export const SITE = "https://read.wspace.ai.kr";
// 화면에 보이는 주소 표기(https:// 없이)
export const SITE_HOST = new URL(SITE).host;
