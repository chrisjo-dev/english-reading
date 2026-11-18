-- 메일은 가입한 사람만 받는다(2026-11-18, 계획 supabase/PLAN-join-subscribe.md, 시안 design/kakao-login K20~K26).
-- 받을 언어와 수준은 가입자가 고른다. 대기 여부와 동기화 시각은 동기화(tools/sync_members.py, 서비스 키)만 쓴다.
-- 선착순 무료 자리는 mail_seats 한 줄로 공개한다(다 찼는지 화면이 읽는다). 숫자는 화면에 보여 주지 않는다.

alter table public.profiles
  add column mail_lang      text not null default 'en' check (mail_lang in ('en', 'ja', 'de')),
  add column mail_level     text not null default 'b'  check (mail_level in ('a', 'b')),
  add column mail_wait      boolean not null default false,
  add column mail_synced_at timestamptz;

-- 클라이언트는 언어와 수준만 더 고칠 수 있다(mail_wait, mail_synced_at, mail_verified 는 쓰기 권한 없음)
grant update (mail_lang, mail_level) on public.profiles to authenticated;

create table public.mail_seats (
  id         smallint primary key default 1 check (id = 1),
  taken      integer not null default 0,
  cap        integer not null default 100,
  updated_at timestamptz not null default now()
);
alter table public.mail_seats enable row level security;
revoke all on public.mail_seats from anon, authenticated;
grant select on public.mail_seats to anon, authenticated;
create policy mail_seats_read on public.mail_seats for select to anon, authenticated using (true);
insert into public.mail_seats (id) values (1);

-- 되돌리기(필요할 때만, 동기화 워크플로를 먼저 끈다):
--   drop table public.mail_seats;
--   alter table public.profiles drop column mail_lang, drop column mail_level, drop column mail_wait, drop column mail_synced_at;
