-- 사이트 반응을 DB에 쌓는다(2026-11-19): 오늘 주제 반응(topic_vote), 언어 추가 요청(lang_request), 기능 건의와 버그 제보 누름(feedback).
-- 쓰는 곳은 api Worker(worker/events.js, 서비스 키) 하나뿐이다. Worker 가 출처와 값을 검사하고 IP 마다 횟수를 제한한다.
-- 브라우저(anon, authenticated)는 이 표를 읽지도 쓰지도 못한다(0003 에서 비로그인 이벤트 쓰기를 닫은 이유와 같다).
-- vid 는 브라우저가 만든 익명 방문 번호(localStorage dkh-vid)다. 이름, 이메일, IP 는 남기지 않는다.
create table public.site_events (
  id    bigint generated always as identity primary key,
  at    timestamptz not null default now(),
  kind  text not null check (kind in ('topic_vote', 'lang_request', 'feedback')),
  vid   text not null check (vid ~ '^[a-f0-9]{32}$'),
  lang  text check (lang is null or lang in ('en', 'ja', 'de')),
  day   date,
  value text not null check (char_length(value) between 1 and 20),
  level text check (level is null or level in ('a', 'b')),
  src   text check (src is null or src ~ '^[a-z]{1,12}$'),
  check (kind <> 'topic_vote' or (lang is not null and day is not null and value in ('up', 'down'))),
  -- 같은 방문자가 같은 지문에 다시 누르면 새 줄 대신 고친다(Worker 가 on_conflict 로 덮어쓴다). 나머지 종류는 lang, day 가 비어 겹치지 않는다
  constraint site_events_once unique (kind, vid, lang, day)
);
create index site_events_kind_at_idx on public.site_events (kind, at);

alter table public.site_events enable row level security;
revoke all on public.site_events from anon, authenticated;

-- 되돌리기(필요할 때만, Worker 의 /events 를 먼저 끈다): drop table public.site_events;
