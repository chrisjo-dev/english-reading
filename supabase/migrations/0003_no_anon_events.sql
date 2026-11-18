-- 비로그인 이벤트 기록을 닫는다(보안 리뷰 2026-11-18: 횟수 제한이 없어 숫자를 부풀릴 수 있었다).
-- 잠금 노출과 클릭은 Google Analytics 이벤트(word_gate_shown, word_gate_click)로 센다. 로그인한 사람의 이벤트는 그대로 남긴다.
drop policy if exists events_insert_anon on public.events;
revoke insert on public.events from anon;
