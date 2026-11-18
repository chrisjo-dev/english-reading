-- 아침 지문 메일 수신(선택, 시안 design/kakao-login K16~K18)
-- Google 가입자는 로그인한 이메일을 쓰고(확인된 주소), 카카오 가입자는 직접 적는다(확인 메일 전까지 mail_verified=false).
-- 클라이언트는 email, mail_opt_in 만 고칠 수 있다. mail_verified 는 트리거와 나중의 발송 서비스(서버)만 바꾼다.
-- 발송 대상(같은 주소는 한 번만, 주소 중복은 막지 않는다: 막으면 다른 사람이 그 주소를 쓰는지 드러난다):
--   select distinct lower(email) from public.profiles where mail_opt_in and mail_verified and email is not null;

alter table public.profiles
  add column email        text check (email is null or (char_length(email) <= 254 and email ~ '^[^@\s]+@[^@\s]+\.[^@\s]+$')),
  add column mail_opt_in  boolean not null default false,
  add column mail_verified boolean not null default false,
  add column mail_opt_at  timestamptz;

grant update (email, mail_opt_in) on public.profiles to authenticated;

-- 주소가 바뀌면 다시 확인이 필요하다. Google 로그인 이메일과 같으면 확인된 것으로 본다. 수신을 켠 시각을 남긴다.
create or replace function public.dkh_profile_mail()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  auth_email text;
  prov text;
begin
  if new.email is distinct from old.email then
    select u.email, u.raw_app_meta_data ->> 'provider' into auth_email, prov from auth.users u where u.id = new.user_id;
    new.mail_verified := new.email is not null and prov = 'google' and lower(new.email) = lower(auth_email);
  end if;  -- mail_verified 칸은 클라이언트에 쓰기 권한이 없다(칸 단위 GRANT)
  if new.mail_opt_in and not old.mail_opt_in then
    new.mail_opt_at := now();
  end if;
  return new;
end;
$$;
revoke all on function public.dkh_profile_mail() from public, anon, authenticated;

create trigger profiles_mail before update on public.profiles
  for each row execute function public.dkh_profile_mail();

-- Google 가입자는 가입할 때 로그인 이메일을 넣어 둔다(수신은 꺼진 채)
create or replace function public.dkh_handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  nick text := nullif(left(btrim(coalesce(
    new.raw_user_meta_data ->> 'nickname',
    new.raw_user_meta_data ->> 'name',
    new.raw_user_meta_data ->> 'full_name', '')), 20), '');
  prov text := new.raw_app_meta_data ->> 'provider';
begin
  insert into public.profiles (user_id, nickname, provider, email, mail_verified)
  values (new.id, nick, case when prov in ('kakao', 'google') then prov end,
          case when prov = 'google' then new.email end, prov = 'google' and new.email is not null)
  on conflict (user_id) do nothing;
  return new;
end;
$$;
revoke all on function public.dkh_handle_new_user() from public, anon, authenticated;

-- 이미 가입한 Google 사용자도 같은 규칙으로 채운다
update public.profiles p set email = u.email
from auth.users u
where p.user_id = u.id and p.provider = 'google' and p.email is null and u.email is not null;
