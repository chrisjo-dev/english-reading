"""배포된 날짜 페이지를 확인한 뒤 Buttondown 으로 구독자에게 메일을 보낸다.

사용: BUTTONDOWN_API_KEY=... python3 tools/send_email.py en 2026-10-12
      BUTTONDOWN_API_KEY=... python3 tools/send_email.py ja 2026-10-18 --weekly   (주간 단어 복습)
      BUTTONDOWN_API_KEY=... python3 tools/send_email.py en 2026-10-14 --catchup  (그날 메일을 못 받은 구독자에게만 다시 보냄)
- 페이지와 썸네일이 200 으로 열리고 페이지에 주제어가 보일 때만 보낸다(최대 10분 대기).
- 같은 언어와 날짜로 이미 만든 메일(metadata.lang, metadata.day)이 있으면 보내지 않는다. 다시 실행해도 중복 발송되지 않는다.
- 받는 사람은 구독자 metadata.lang 으로 거른다. 영어는 "ja 등 다른 언어가 아닌" 구독자 전부.
- Buttondown 필터는 lang 값이 없는 구독자를 not_equals 에서도 빼므로, 보내기 전에 lang 이 없는 구독자를 기본 언어(en)로 채운다.
"""
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_email  # noqa: E402
import langs  # noqa: E402

API = "https://api.buttondown.com/v1"


def call(method, path, body=None):
    req = urllib.request.Request(
        API + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Token {os.environ['BUTTONDOWN_API_KEY']}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Buttondown {method} {path} -> {e.code}: {e.read().decode()[:300]}")


def wait_live(url, text, extra=None):
    """url 이 200 으로 열리고 text 가 보이며, extra(썸네일 등)도 200 일 때까지 최대 10분 기다린다."""
    for _ in range(40):
        try:
            with urllib.request.urlopen(url + f"?v={time.time():.0f}", timeout=15) as r:
                page = r.read().decode("utf-8")
            extra_ok = True
            if extra:
                with urllib.request.urlopen(extra, timeout=15) as r:
                    extra_ok = r.status == 200
            if text in page and extra_ok:
                return
        except urllib.error.URLError:
            pass
        time.sleep(15)
    raise SystemExit(f"페이지가 열리지 않아 메일을 보내지 않음: {url}")


def audience(lang, level="b"):
    """구독자 언어+수준 필터.
    기본 언어(영어)는 다른 언어로 표시된 구독자만 빼고, 수준 필터를 추가한다.
    level="a": level=="a" 구독자만.
    level="b"(기본): level!="a" 구독자. fill_missing_level() 호출 후에 사용해야 한다.
    level=None: 수준 필터 없음 (단계적 배포 초기 등 level 기능 이전 호환).
    """
    if lang == langs.DEFAULT:
        rules = [{"field": "subscriber.metadata.lang", "operator": "not_equals", "value": other} for other in langs.LANGS if other != lang]
    else:
        rules = [{"field": "subscriber.metadata.lang", "operator": "equals", "value": lang}]
    if level == "a":
        rules.append({"field": "subscriber.metadata.level", "operator": "equals", "value": "a"})
    elif level == "b":
        rules.append({"field": "subscriber.metadata.level", "operator": "not_equals", "value": "a"})
    # level=None: 수준 필터 추가 안 함
    return {"predicate": "and", "groups": [], "filters": rules}


def subscribers():
    path = "/subscribers?page_size=100"
    while path:
        data = call("GET", path)
        yield from data["results"]
        nxt = data.get("next")
        path = nxt.split("/v1", 1)[1] if nxt else None


def fill_missing_lang():
    """구독 폼을 거치지 않은 구독자(기본 구독 페이지, 예전 폼)는 lang 이 없어 필터에서 빠진다. 기본 언어로 채운다."""
    for sub in subscribers():
        meta = sub.get("metadata") or {}
        if sub.get("type") in ("regular", "unactivated") and not meta.get("lang"):
            call("PATCH", f"/subscribers/{sub['id']}", {"metadata": {**meta, "lang": langs.DEFAULT}})
            print(f"lang 채움: {sub['id']} -> {langs.DEFAULT}")


def fill_missing_level():
    """level 키가 없는 구독자는 not_equals 필터에서 빠진다. 기본 수준(b)으로 채운다.
    주의: 최초 실행 시 기존 구독자 전원에게 level='b' 를 씁니다. 배포 시 사용자 승인 필요.
    """
    for sub in subscribers():
        meta = sub.get("metadata") or {}
        if sub.get("type") in ("regular", "unactivated") and not meta.get("level"):
            call("PATCH", f"/subscribers/{sub['id']}", {"metadata": {**meta, "level": "b"}})
            print(f"level 채움: {sub['id']} -> b")


def recent_emails(pages=5):
    path = "/emails?ordering=-creation_date"
    for _ in range(pages):
        data = call("GET", path)
        yield from data["results"]
        nxt = data.get("next")
        if not nxt:
            return
        path = nxt.split("/v1", 1)[1]


# 수준 필터 없이(기초 구독자 포함) 보낸 메일은 metadata.level 에 이 값을 적는다. Buttondown 이 null 값을 지울 수 있어 문자열로 남긴다.
LEVEL_ALL = "all"


def meta_level(level):
    return LEVEL_ALL if level is None else level


def same_issue(meta, lang, key, value, level="b"):
    """예전(언어 구분 전) 메일은 metadata.lang 이 없고 모두 영어였다. level 키 없는 기존 메일은 중급(b)으로 취급."""
    return (meta.get(key) == value
            and meta.get("lang", langs.DEFAULT) == lang
            and (meta.get("level") or "b") == meta_level(level))


def send(mail, lang, key, value, level="b", extra_meta=None):
    """같은 언어+수준, 같은 key 값의 메일이 이미 있으면 보내지 않는다. 다시 실행해도 중복 발송되지 않는다."""
    draft = None
    for e in recent_emails():
        if not same_issue(e.get("metadata") or {}, lang, key, value, level):
            continue
        if e["status"] == "draft":
            # 지난 실행이 초안만 만들고 실패한 경우: 그 초안을 최신 내용으로 고쳐 다시 보낸다.
            draft = call("PATCH", f"/emails/{e['id']}", {**mail, "template": "naked", "filters": audience(lang, level)})
            break
        if e["status"] in ("errored", "throttled"):
            # 일부 구독자에게 나갔을 수 있으므로 자동으로 다시 보내지 않고 실패로 드러낸다.
            raise SystemExit(f"Buttondown 발송 오류 상태라 확인 필요: {e['id']} ({e['status']})")
        print(f"이미 처리한 메일이 있어 건너뜀: {e['id']} ({e['status']})")
        return
    fill_missing_lang()
    if level is not None:
        fill_missing_level()
    metadata = {"lang": lang, key: value, "level": meta_level(level)}
    if extra_meta:
        metadata.update(extra_meta)
    if draft is None:
        draft = call("POST", "/emails", {**mail, "status": "draft", "template": "naked",
                                          "filters": audience(lang, level), "metadata": metadata})
    call("PATCH", f"/emails/{draft['id']}", {"status": "about_to_send"})
    for _ in range(30):
        status = call("GET", f"/emails/{draft['id']}")["status"]
        if status == "sent":
            print(f"sent {draft['id']}")
            return
        time.sleep(10)
    raise SystemExit(f"발송 상태 확인 실패: {draft['id']} ({status})")


def wants(sub, lang, level="b"):
    """audience() 와 같은 기준으로, 이 구독자가 lang+level 메일을 받아야 하는지."""
    if sub.get("type") != "regular":
        return False
    sub_lang = (sub.get("metadata") or {}).get("lang") or langs.DEFAULT
    sub_level = (sub.get("metadata") or {}).get("level") or "b"
    # 언어 필터
    if lang == langs.DEFAULT:
        if sub_lang in set(langs.LANGS) - {lang}:
            return False
    elif sub_lang != lang:
        return False
    # 수준 필터
    if level == "a":
        return sub_level == "a"
    elif level is None:
        return True  # 수준 필터 없음: 해당 언어 구독자 전체
    else:
        return sub_level != "a"


def reached(email_id):
    """이 메일에 대해 Buttondown 이벤트(전달, 반송 등)가 하나라도 남은 구독자. 반송된 주소도 다시 보내지 않는다."""
    path = f"/events?email_id={email_id}"
    seen = set()
    while path:
        data = call("GET", path)
        seen.update(e["subscriber_id"] for e in data["results"] if e.get("subscriber_id"))
        nxt = data.get("next")
        path = nxt.split("/v1", 1)[1] if nxt else None
    return seen


def recently_sent(sent_at: str, now: datetime.datetime) -> bool:
    """본 메일 발송 시각이 now 기준 30분 이내이면 True 를 반환한다(테스트 가능한 순수 함수).

    sent_at 은 Buttondown API 의 publish_date 또는 creation_date 문자열(ISO 8601).
    """
    try:
        sent = datetime.datetime.fromisoformat(sent_at.replace("Z", "+00:00"))
        if sent.tzinfo is None:
            sent = sent.replace(tzinfo=datetime.timezone.utc)
        now_utc = now.astimezone(datetime.timezone.utc) if now.tzinfo else now.replace(tzinfo=datetime.timezone.utc)
        return (now_utc - sent).total_seconds() < 1800
    except (ValueError, TypeError, AttributeError):
        return False


def catchup(lang, day, level="b"):
    """그날 본 메일과 이전 보충 메일을 받지 못한 구독자에게만 같은 지문을 보낸다.

    본 메일 발송 직후에는 전달 이벤트가 늦게 쌓일 수 있으므로, 발송 뒤 충분히 지나서 수동으로 실행한다.
    기초 지문이 없어 본 메일을 level=None(전체 대상)으로 보낸 경우도 같이 인식한다.
    """
    L = langs.LANGS.get(lang, {})
    if not L.get("email", True):
        print(f"이 언어는 아직 메일을 보내지 않습니다 (email=False, {lang}). 종료합니다.")
        return
    catchup_tag_prefix = f"{lang}:{day}:{level}"

    def _is_main(meta):
        return (same_issue(meta, lang, "day", day, level) or
                same_issue(meta, lang, "day", day, None))

    issues = [e for e in recent_emails(pages=10)
              if e["status"] == "sent" and (
                  _is_main(e.get("metadata") or {})
                  or (e.get("metadata") or {}).get("catchup_of") == catchup_tag_prefix)]
    if not any(_is_main(e.get("metadata") or {}) for e in issues):
        raise SystemExit(f"{lang} {day} level={level} 본 메일이 없어 보충 발송하지 않음. 본 발송부터 하세요.")

    # 본 메일이 30분 이내에 발송됐으면 전달 이벤트가 아직 쌓이는 중일 수 있다. 건너뜀.
    main_emails = [e for e in issues if _is_main(e.get("metadata") or {})]
    # 실제 발송된 level 확인: level=None 이면 기초 지문 없어 전체 대상으로 보낸 경우
    effective_level = (main_emails[0].get("metadata") or {}).get("level", level) if main_emails else level
    if effective_level == LEVEL_ALL:
        effective_level = None
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    for mi in main_emails:
        sent_at = mi.get("publish_date") or mi.get("creation_date") or ""
        if recently_sent(sent_at, now_utc):
            print("본 메일 발송 30분 이내라 이번 보충은 건너뜀")
            return
    fill_missing_lang()
    got = set().union(*(reached(e["id"]) for e in issues))
    targets = [sub for sub in subscribers() if wants(sub, lang, effective_level) and sub["id"] not in got]
    if not targets:
        print(f"보충 대상 없음 ({lang} {day} level={level})")
        return
    tag = f"{lang}:{day}:{level}:{len(issues)}"
    for sub in targets:
        call("PATCH", f"/subscribers/{sub['id']}", {"metadata": {**(sub.get("metadata") or {}), "catchup": tag}})
    try:
        mail = build_email.build(lang, day, level)
        if mail is None:
            print(f"기초 콘텐츠 없음, 보충 건너뜀 ({lang} {day} level={level})")
            return
        note = ('<p style="max-width:560px;margin:0 auto 8px;font-size:13px;color:#6b7684;text-align:center;">'
                '아침에 받지 못하신 분께 다시 보내 드려요.</p>\n')
        mail["body"] = mail["body"].replace('<table role="presentation"', note + '<table role="presentation"', 1)
        draft = call("POST", "/emails", {**mail, "status": "draft", "template": "naked",
                                          "filters": {"predicate": "and", "groups": [], "filters": [
                                              {"field": "subscriber.metadata.catchup", "operator": "equals", "value": tag}]},
                                          "metadata": {"lang": lang, "level": meta_level(effective_level), "catchup_of": catchup_tag_prefix}})
        call("PATCH", f"/emails/{draft['id']}", {"status": "about_to_send"})
        for _ in range(30):
            if call("GET", f"/emails/{draft['id']}")["status"] == "sent":
                print(f"catch-up sent {draft['id']} to {len(targets)}")
                break
            time.sleep(10)
        else:
            raise SystemExit(f"보충 발송 상태 확인 실패: {draft['id']}")
    finally:
        # 발송 대상 표시는 남겨 두지 않는다. 다음 보충은 이벤트 기록으로 다시 계산한다.
        for sub in targets:
            meta = {k: v for k, v in (sub.get("metadata") or {}).items() if k != "catchup"}
            try:
                call("PATCH", f"/subscribers/{sub['id']}", {"metadata": meta})
            except SystemExit as exc:
                print(f"표시 정리 실패, 다음 구독자로 계속: {sub['id']} {exc}")


def main(lang, day, level="b"):
    L = langs.LANGS.get(lang, {})
    if not L.get("email", True):
        print(f"이 언어는 아직 메일을 보내지 않습니다 (email=False, {lang}). 종료합니다.")
        return
    url_base = f"{build_email.SITE}/{lang}/{day}/"
    wait_live(url_base, build_email.parse(lang, day)["topic"], url_base + "thumb.png")
    if level == "a":
        mail = build_email.build(lang, day, "a")
        if mail is None:
            print(f"기초 지문 없음, 중급 메일에 포함됨 ({lang} {day})")
            return  # exit 0: 중급(b) 발송 시 이미 a-구독자 포함
        send(mail, lang, "day", day, level="a")
        return
    # level == "b": 기초 지문이 없으면 a-구독자도 중급 메일에 포함한다(수준 필터 없음)
    mail = build_email.build(lang, day, "b")
    has_level_a = build_email.build(lang, day, "a") is not None
    effective_level = "b" if has_level_a else None
    send(mail, lang, "day", day, level=effective_level)


def main_weekly(lang, end):
    L = langs.LANGS.get(lang, {})
    if not L.get("email", True):
        print(f"이 언어는 아직 메일을 보내지 않습니다 (email=False, {lang}). 종료합니다.")
        return
    import weekly
    mail = weekly.build_email(lang, end)
    url = mail.pop("url")
    wait_live(url, weekly.span(end))
    send(mail, lang, "week", end)


if __name__ == "__main__":
    langs.get(sys.argv[1])
    # --level b 또는 --level a 파라미터 파싱 (그 외 값은 오류)
    level = "b"
    if "--level" in sys.argv:
        li = sys.argv.index("--level")
        if li + 1 < len(sys.argv):
            level = sys.argv[li + 1]
        if level not in ("a", "b"):
            raise SystemExit(f"--level 값이 올바르지 않습니다: {level!r}. 'a' 또는 'b' 만 허용합니다.")
    if "--weekly" in sys.argv:
        main_weekly(sys.argv[1], sys.argv[2])
    elif "--catchup" in sys.argv:
        catchup(sys.argv[1], sys.argv[2], level)
    else:
        main(sys.argv[1], sys.argv[2], level)
