// 사이트 주소. 도메인을 옮길 때는 여기 한 곳과 tools/langs.py 의 SITE 를 같이 바꾼다.
export const SITE = "https://dokhaehanip.com";
// 화면에 보이는 주소 표기(https:// 없이)
export const SITE_HOST = new URL(SITE).host;
// 다른 이름과 운영 주체의 공식 외부 주소. tools/langs.py 의 ALT_NAMES, SAME_AS 와 같은 값이어야 한다(tests/test_seo.py 가 확인).
export const ALT_NAMES = ["한입독해", "독해 한입", "Dokhaehanip", "dokhaehanip", "매일 외국어 읽기"];
export const SAME_AS = ["https://buttondown.com/english-reading/archive/"];
