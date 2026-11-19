-- 0006 의 site_events 에 서버 역할(service_role) 쓰기 권한을 명시한다(2026-11-19).
-- 새 표는 service_role 에 권한이 자동으로 붙지 않아 Worker 의 기록이 403(권한 없음)으로 막혔다.
-- 브라우저 역할(anon, authenticated)은 그대로 권한 없음.
grant select, insert, update on public.site_events to service_role;

-- 되돌리기: revoke all on public.site_events from service_role;
