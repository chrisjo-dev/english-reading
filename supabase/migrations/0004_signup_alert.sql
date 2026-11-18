-- 새 가입자가 생기면 Slack 으로 알린다. 보내는 것은 로그인 방식(카카오, Google)과 누적 가입자 수뿐이다(이름, 이메일은 보내지 않는다).
-- 웹훅 주소는 저장소에 넣지 않고 Vault 에 둔다. SQL Editor 에서 사용자가 직접 한 번 실행한다:
--   select vault.create_secret('<Slack 웹훅 주소>', 'slack_webhook_url');
-- 주소가 없거나 보내기가 실패해도 가입은 막지 않는다(pg_net 은 요청을 줄에 넣고 바로 돌아온다).
create extension if not exists pg_net;

create or replace function public.dkh_signup_alert() returns trigger
language plpgsql security definer set search_path = '' as $$
declare
  hook text;
  total bigint;
begin
  select decrypted_secret into hook from vault.decrypted_secrets where name = 'slack_webhook_url' limit 1;
  if hook is null then
    return new;
  end if;
  select count(*) into total from public.profiles;
  perform net.http_post(
    url := hook,
    body := jsonb_build_object('text', format('🎉 독해한입 새 가입: %s (누적 %s명)',
      case new.provider when 'kakao' then '카카오' when 'google' then 'Google' else '기타' end, total)),
    headers := '{"Content-Type": "application/json"}'::jsonb
  );
  return new;
exception when others then
  return new;
end $$;

revoke all on function public.dkh_signup_alert() from public, anon, authenticated;

drop trigger if exists dkh_signup_alert on public.profiles;
create trigger dkh_signup_alert after insert on public.profiles
  for each row execute function public.dkh_signup_alert();
