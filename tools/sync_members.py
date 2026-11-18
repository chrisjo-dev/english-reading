"""가입자의 아침 메일 설정(Supabase profiles)을 Buttondown 구독자로 맞춘다. 메일은 가입한 사람만 받는다(2026-11-18).

계획: supabase/PLAN-join-subscribe.md. 워크플로 .github/workflows/sync-members.yml 이 매시 돌린다.
비밀값: SUPABASE_SERVICE_ROLE_KEY(profiles 읽기와 서버 칸 쓰기), BUTTONDOWN_API_KEY.

- 선착순 CAP 명(Buttondown 의 regular + unactivated, 기존 구독자 포함)까지만 넣고, 넘으면 대기(mail_wait).
- 확인된 주소(Google)는 확인 메일 없이 regular 로, 직접 적은 주소(카카오)는 확인 메일이 가는 unactivated 로 넣는다.
- 가입자가 넣은 구독자에는 metadata.account="1" 을 붙인다. 이 표시가 없는 기존 구독자는 끄거나 지우지 않는다.
- 메일 하단에서 수신거부한 사람은 다시 넣지 않고 profiles.mail_opt_in 을 끈다.
  단, 마지막 동기화 뒤에 마이페이지에서 다시 켰으면(mail_opt_at > mail_synced_at) 다시 넣는다.
- 바뀐 것만 쓴다. 매시 한 번이라 스위치를 여러 번 눌러도 Buttondown 에는 한 번만 반영된다(빠른 구독/해지 반복 방지).
"""
import datetime
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import send_email  # noqa: E402

SUPABASE = "https://kfprgssvigujxphfmlth.supabase.co/rest/v1"
CAP = 100
LIVE = ("regular", "unactivated")
GONE = ("unsubscribed", "complained", "blocked", "undeliverable")
FIELDS = "user_id,email,mail_opt_in,mail_verified,mail_lang,mail_level,mail_wait,mail_opt_at,mail_synced_at"


def _ts(v):
    try:
        t = datetime.datetime.fromisoformat((v or "").replace("Z", "+00:00"))
        return t if t.tzinfo else t.replace(tzinfo=datetime.timezone.utc)
    except ValueError:
        return None


def plan(profiles, subs, cap=CAP):
    """할 일을 정한다(순수 함수). profiles 는 mail_opt_at 순서.
    돌려주는 값: (buttondown 작업 목록, profiles 고칠 것 {user_id: patch}, taken)
    작업: ("create", email, body, collision) / ("meta", email, metadata) / ("unsub", email) / ("delete", email)
    """
    by = {}
    for s in subs:
        by[(s.get("email_address") or s.get("email") or "").lower()] = s
    taken = sum(1 for s in by.values() if s.get("type") in LIVE)
    ops, fix, seen = [], {}, set()
    # 주소가 같은 계정이 여럿이면(주소 중복은 막지 않는다) 하나라도 켜 둔 동안은 끄지 않는다
    wanted = {p["email"].lower() for p in profiles if p.get("email") and p.get("mail_opt_in")}
    for p in profiles:
        if not p.get("email"):
            continue
        e = p["email"].lower()
        seen.add(e)
        s = by.get(e)
        meta = {"lang": p.get("mail_lang") or "en", "level": p.get("mail_level") or "b", "account": "1"}
        patch = {}
        if p.get("mail_opt_in"):
            if s and s.get("type") in LIVE:
                old = s.get("metadata") or {}
                if old.get("account") != "1" and not p.get("mail_synced_at"):
                    # 기존 구독자가 처음 가입으로 연결될 때: Buttondown 에서 받던 언어, 수준을 그대로 두고 계정 쪽을 맞춘다
                    if old.get("lang") in ("en", "ja", "de") and old["lang"] != meta["lang"]:
                        patch["mail_lang"] = meta["lang"] = old["lang"]
                    if old.get("level") in ("a", "b") and old["level"] != meta["level"]:
                        patch["mail_level"] = meta["level"] = old["level"]
                if any(old.get(k) != v for k, v in meta.items()):
                    ops.append(("meta", e, {**old, **meta}))
                    patch["mail_synced_at"] = True
                if p.get("mail_wait"):
                    patch["mail_wait"] = False
                if s.get("type") == "regular" and not p.get("mail_verified"):
                    patch["mail_verified"] = True
            else:
                again = s is not None
                if again:
                    opt, synced = _ts(p.get("mail_opt_at")), _ts(p.get("mail_synced_at"))
                    fresh = s.get("type") == "unsubscribed" and (synced is None or (opt is not None and opt > synced))
                    if not fresh:
                        # 메일 하단에서 끊었다(또는 반송, 신고). 다시 넣지 않고 사이트 설정도 끈다.
                        fix[p["user_id"]] = {"mail_opt_in": False, "mail_wait": False, "mail_synced_at": True}
                        continue
                if taken < cap:
                    body = {"email_address": p["email"], "metadata": meta}
                    if p.get("mail_verified"):
                        body["type"] = "regular"  # 확인된 주소(Google): 확인 메일 없이
                    elif again:
                        body["type"] = "unactivated"  # 다시 넣는데 확인 전 주소면 확인 메일부터
                    ops.append(("create", e, body, again))
                    by[e] = {"type": body.get("type", "unactivated"), "metadata": meta}  # 같은 주소의 다음 계정은 이미 있는 것으로
                    taken += 1
                    patch.update({"mail_wait": False, "mail_synced_at": True})
                elif not p.get("mail_wait"):
                    patch["mail_wait"] = True
        else:
            if e not in wanted and s and (s.get("metadata") or {}).get("account") == "1" and s.get("type") in LIVE:
                ops.append(("unsub", e) if s.get("type") == "regular" else ("delete", e))
                taken -= 1
                patch["mail_synced_at"] = True
            if p.get("mail_wait"):
                patch["mail_wait"] = False
        if patch:
            fix[p["user_id"]] = patch
    # 가입자가 넣었는데 이제 어느 계정에도 없는 주소(탈퇴, 주소 바꿈)는 지운다
    for e, s in by.items():
        if e and e not in seen and (s.get("metadata") or {}).get("account") == "1" and s.get("type") in LIVE + ("unsubscribed",):
            ops.append(("delete", e))
            if s.get("type") in LIVE:
                taken -= 1
    return ops, fix, taken


def _sb(method, path, body=None):
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    headers = {"apikey": key, "Content-Type": "application/json", "Prefer": "return=minimal"}
    if not key.startswith("sb_"):
        headers["Authorization"] = f"Bearer {key}"  # 예전 JWT 형식 키
    req = urllib.request.Request(SUPABASE + path, method=method, headers=headers,
                                 data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Supabase {method} {path.split('?')[0]} -> {e.code}: {e.read().decode()[:300]}")


def _bd(method, path, body=None, collision=False):
    headers = {"Authorization": f"Token {os.environ['BUTTONDOWN_API_KEY']}", "Content-Type": "application/json"}
    if collision:
        headers["X-Buttondown-Collision-Behavior"] = "add"
    req = urllib.request.Request(send_email.API + path, method=method, headers=headers,
                                 data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Buttondown {method} {path.split('?')[0]} -> {e.code}: {e.read().decode()[:300]}")


def all_subscribers():
    """수신거부 등 모든 타입을 읽는다. 목록이 type 필터를 무시해도 id 로 겹치지 않게 모은다."""
    out = {}
    for t in LIVE + GONE:
        path = f"/subscribers?page_size=100&type={t}"
        try:
            while path:
                data = _bd("GET", path)
                for s in data["results"]:
                    out[s["id"]] = s
                nxt = data.get("next")
                path = nxt.split("/v1", 1)[1] if nxt else None
        except SystemExit as e:
            if t in ("regular", "unactivated", "unsubscribed"):
                raise  # 이 셋을 못 읽으면 자리 계산과 수신거부 존중이 틀어진다
            print(f"::warning::{t} 구독자 목록을 읽지 못해 건너뜀: {e}")
    return list(out.values())


def all_profiles():
    """PostgREST 는 한 번에 최대 1000줄이라 끝까지 나눠 읽는다(빠진 계정의 주소를 지우지 않게)."""
    out, page = [], 1000
    while True:
        rows = _sb("GET", f"/profiles?select={FIELDS}&email=not.is.null&order=mail_opt_at.asc.nullslast,user_id.asc"
                          f"&limit={page}&offset={len(out)}") or []
        out += rows
        if len(rows) < page:
            return out


def run():
    from urllib.parse import quote
    profiles = all_profiles()
    ops, fix, taken = plan(profiles, all_subscribers())
    # 주소 하나가 실패해도(Buttondown 이 거절하는 주소 등) 나머지는 계속한다. 실패한 주소의 계정은 고치지 않고 끝에 실패로 드러낸다
    failed = set()
    for op in ops:
        e = quote(op[1], safe="")
        try:
            if op[0] == "create":
                _bd("POST", "/subscribers", op[2], collision=op[3])
            elif op[0] == "meta":
                _bd("PATCH", f"/subscribers/{e}", {"metadata": op[2]})
            elif op[0] == "unsub":
                _bd("PATCH", f"/subscribers/{e}", {"type": "unsubscribed"})
            else:
                _bd("DELETE", f"/subscribers/{e}")
        except SystemExit as err:
            failed.add(op[1])
            if op[0] == "create":
                taken -= 1
            print(f"::warning::{op[0]} 실패: {err}")
    skip = {p["user_id"] for p in profiles if (p.get("email") or "").lower() in failed}
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    for uid, patch in fix.items():
        if uid in skip:
            continue
        patch = {k: (now if v is True and k == "mail_synced_at" else v) for k, v in patch.items()}
        _sb("PATCH", f"/profiles?user_id=eq.{uid}", patch)
    _sb("PATCH", "/mail_seats?id=eq.1", {"taken": max(taken, 0), "cap": CAP, "updated_at": now})
    print(f"동기화: Buttondown 작업 {len(ops)}건(실패 {len(failed)}), 계정 고침 {len(fix) - len(skip & set(fix))}건, 자리 {max(taken, 0)}/{CAP}")
    if failed:
        raise SystemExit(f"Buttondown 작업 {len(failed)}건 실패(나머지는 반영함). 위 경고를 확인하세요.")


if __name__ == "__main__":
    run()
