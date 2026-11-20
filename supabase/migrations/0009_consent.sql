-- 필수 동의(만 14세 이상, 개인정보 수집)를 서버에 남긴다(2026-11-20, 시안 design/kakao-login K32, K33).
-- 로그인 화면(/login/)은 동의 칸이 없어서, 처음인 계정이 동의 화면(K33)을 그냥 떠나면 동의 없는 계정이 남았다.
-- 이제 agreed_at 이 비어 있으면 콜백과 마이페이지가 동의 화면으로 보내고, 메일 동기화(tools/sync_members.py)는 넣지 않는다.
-- 클라이언트는 칸을 직접 쓰지 못하고 agree_terms() 로만 "지금" 시각을 한 번 남긴다(앞당기거나 지우지 못한다).

alter table public.profiles add column agreed_at timestamptz;

-- 로그인 화면이 나오기 전(2026-11-19 15:00:37 UTC, 9a7bbf6d 배포)에 만든 계정은 가입 화면의 필수 동의를 거쳤다
update public.profiles set agreed_at = created_at
where agreed_at is null and created_at < timestamptz '2026-11-19 15:00:37+00';

create or replace function public.agree_terms()
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
  update public.profiles set agreed_at = coalesce(agreed_at, now()) where user_id = uid;
end;
$$;
revoke all on function public.agree_terms() from public, anon;
grant execute on function public.agree_terms() to authenticated;

-- 되돌리기(필요할 때만, 콜백, 마이페이지, 동기화를 먼저 되돌린다):
--   drop function public.agree_terms();
--   alter table public.profiles drop column agreed_at;
