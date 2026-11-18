-- 독해한입 로그인과 단어 기록: 첫 스키마 (릴리랑 supabase/migrations/0001_init.sql 과 같은 원칙)
-- 원칙
--   1. 모든 테이블 RLS. 정책은 authenticated 역할과 auth.uid() = user_id 로만.
--   2. 클라이언트에는 anon(publishable) 키만 둔다. service role 키는 어디에도 쓰지 않는다.
--   3. IP와 기기 정보는 저장하지 않는다. 학습 기록은 브라우저의 drill:v1 값을 그대로 한 행에 둔다.
--   4. 권한(GRANT)은 필요한 것만 주고, 정책은 그 위에 한 겹 더 막는다.
-- 가입자 수: select count(*) from public.profiles;

-- 이벤트 이름 목록(이 밖은 거부). 바꿀 때는 assets/auth.js 의 EVENTS 도 같이 바꾼다.
create or replace function public.dkh_event_name_ok(n text)
returns boolean
language sql
immutable
set search_path = ''
as $$
  select n in ('signup', 'login', 'logout', 'delete_account', 'gate_shown', 'gate_join_click');
$$;

-- 테이블 ---------------------------------------------------------------

create table public.profiles (
  user_id    uuid primary key references auth.users (id) on delete cascade,
  nickname   text check (nickname is null or char_length(nickname) between 1 and 20),
  provider   text check (provider is null or provider in ('kakao', 'google')),
  created_at timestamptz not null default now()
);

-- 단어 기록: 사람마다 한 행. data 는 drill:v1 모양({"items": {...}, "days": [...]}), 크기는 512KB 까지.
create table public.drill_state (
  user_id    uuid primary key references auth.users (id) on delete cascade,
  data       jsonb not null default '{"items": {}}'::jsonb
             check (jsonb_typeof(data) = 'object' and pg_column_size(data) < 524288),
  updated_at timestamptz not null default now()
);

create table public.events (
  id      bigint generated always as identity primary key,
  user_id uuid references auth.users (id) on delete cascade,
  name    text not null check (public.dkh_event_name_ok(name)),
  lang    text check (lang is null or lang ~ '^[a-z]{2}$'),
  at      timestamptz not null default now()
);
create index events_user_id_idx on public.events (user_id);
create index events_name_at_idx on public.events (name, at);

-- 권한 -----------------------------------------------------------------
revoke all on public.profiles, public.drill_state, public.events from anon, authenticated;

-- profiles: 행은 트리거가 만들고 탈퇴 함수가 지운다. 클라이언트는 읽기와 닉네임 고치기만.
grant select on public.profiles to authenticated;
grant update (nickname) on public.profiles to authenticated;

grant select, insert, update on public.drill_state to authenticated;

-- 이벤트는 본인도 지우지 못한다. 탈퇴 때는 delete_my_account 가 definer 권한으로 지운다.
grant select, insert on public.events to authenticated;
-- 비로그인은 이벤트 기록만. user_id 칸은 쓸 수 없다(칸 단위 권한).
grant insert (name, lang) on public.events to anon;

revoke all on function public.dkh_event_name_ok(text) from public;
grant execute on function public.dkh_event_name_ok(text) to anon, authenticated;

-- RLS ------------------------------------------------------------------
alter table public.profiles    enable row level security;
alter table public.drill_state enable row level security;
alter table public.events      enable row level security;

create policy profiles_select on public.profiles for select to authenticated
  using ((select auth.uid()) = user_id);
create policy profiles_update on public.profiles for update to authenticated
  using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);

create policy drill_select on public.drill_state for select to authenticated
  using ((select auth.uid()) = user_id);
create policy drill_insert on public.drill_state for insert to authenticated
  with check ((select auth.uid()) = user_id);
create policy drill_update on public.drill_state for update to authenticated
  using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);

create policy events_select on public.events for select to authenticated
  using ((select auth.uid()) = user_id);
create policy events_insert on public.events for insert to authenticated
  with check ((select auth.uid()) = user_id);
create policy events_insert_anon on public.events for insert to anon
  with check (user_id is null and public.dkh_event_name_ok(name));

-- user_id 바꾸기 막기 ----------------------------------------------------
create or replace function public.dkh_keep_user_id()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if new.user_id is distinct from old.user_id then
    raise exception 'user_id cannot be changed' using errcode = '42501';
  end if;
  return new;
end;
$$;
revoke all on function public.dkh_keep_user_id() from public, anon, authenticated;

create trigger profiles_keep_user_id before update on public.profiles
  for each row execute function public.dkh_keep_user_id();
create trigger drill_keep_user_id before update on public.drill_state
  for each row execute function public.dkh_keep_user_id();

-- 가입하면 profiles 행 만들기 ---------------------------------------------
-- 닉네임은 카카오 닉네임 또는 Google 이름을 20자까지. 이메일은 profiles 에 옮기지 않는다.
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
  insert into public.profiles (user_id, nickname, provider)
  values (new.id, nick, case when prov in ('kakao', 'google') then prov end)
  on conflict (user_id) do nothing;
  return new;
end;
$$;
revoke all on function public.dkh_handle_new_user() from public, anon, authenticated;

create trigger on_auth_user_created after insert on auth.users
  for each row execute function public.dkh_handle_new_user();

-- 탈퇴 -----------------------------------------------------------------
-- 호출한 본인의 행과 auth 사용자를 지운다. 탈퇴 기록은 누구인지 남기지 않는 한 줄로만 남긴다.
create or replace function public.delete_my_account()
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  uid uuid := auth.uid();
begin
  if uid is null then
    raise exception 'not signed in' using errcode = '42501';
  end if;
  delete from public.events      where user_id = uid;
  delete from public.drill_state where user_id = uid;
  delete from public.profiles    where user_id = uid;
  delete from auth.users         where id = uid;
  insert into public.events (name) values ('delete_account');
end;
$$;
revoke all on function public.delete_my_account() from public, anon;
grant execute on function public.delete_my_account() to authenticated;
