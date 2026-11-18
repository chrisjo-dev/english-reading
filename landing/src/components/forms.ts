"use client";
import { useEffect, useState } from "react";
import { readMe } from "@/lib/me";

// 메일은 가입한 사람만 받는다(2026-11-18, 시안 design/kakao-login K20). 구독 버튼은 가입 화면으로 보낸다.
// 고른 언어와 수준을 가입 화면(K21)이 그대로 채운다. 이미 로그인했으면 마이페이지 메일 칸으로 보낸다.
export function joinHref(lang: string, level: string): string {
  if (readMe().on) return "/me/#mailcard";
  return "/join/?" + new URLSearchParams({ mail: "1", lang, level, next: "/", from: "landing" }).toString();
}

export const SEATS_NOTE = "카카오나 Google 계정으로 가입해요. 무료예요.";
export const FULL_NOTE = "선착순 100명이 다 찼어요. 지금 가입하면 대기 명단에 올려 드려요.";

// 선착순 무료 자리(public.mail_seats, 동기화가 매시 갱신). 읽지 못하면 다 안 찬 것으로 본다.
const SEATS = "https://kfprgssvigujxphfmlth.supabase.co/rest/v1/mail_seats?select=taken,cap&id=eq.1";
const ANON = "sb_publishable_cyzW-kfuGUNsm1mDeyKm1Q_dmlOxt9U";

export function useMailFull(): boolean {
  const [full, setFull] = useState(false);
  useEffect(() => {
    fetch(SEATS, { headers: { apikey: ANON } })
      .then((r) => (r.ok ? r.json() : []))
      .then((rows: { taken: number; cap: number }[]) => setFull(!!rows[0] && rows[0].taken >= rows[0].cap))
      .catch(() => {});
  }, []);
  return full;
}

// 로그인 여부는 브라우저에서만 안다. 처음 그릴 때는 가입 주소로 두고, 화면이 뜬 뒤 바꾼다.
export function useJoinHref(lang: string, level: string): string {
  const base = "/join/?" + new URLSearchParams({ mail: "1", lang, level, next: "/", from: "landing" }).toString();
  const [href, setHref] = useState(base);
  useEffect(() => setHref(joinHref(lang, level)), [lang, level]);
  return href;
}
