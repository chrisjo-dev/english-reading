-- 메일 동기화(tools/sync_members.py, 서버 역할)가 쓰는 표에 권한을 명시한다(2026-11-19).
-- 이 프로젝트는 새 표에 service_role 권한이 자동으로 붙지 않아 첫 실행이 403(profiles 읽기 거부)으로 막혔다.
-- 동기화는 profiles 를 읽고 메일 칸(mail_opt_in, mail_lang, mail_level, mail_verified, mail_wait, mail_synced_at)을 고치며, mail_seats 를 고친다.
grant select on public.profiles to service_role;
grant update (mail_opt_in, mail_lang, mail_level, mail_verified, mail_wait, mail_synced_at) on public.profiles to service_role;
grant select, update on public.mail_seats to service_role;

-- 되돌리기: revoke all on public.profiles, public.mail_seats from service_role;
