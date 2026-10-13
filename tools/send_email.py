"""배포된 날짜 페이지를 확인한 뒤 Buttondown 으로 구독자에게 메일을 보낸다.

사용: BUTTONDOWN_API_KEY=... python3 tools/send_email.py en 2026-10-12
      BUTTONDOWN_API_KEY=... python3 tools/send_email.py ja 2026-10-18 --weekly   (주간 단어 복습)
- 페이지와 썸네일이 200 으로 열리고 페이지에 주제어가 보일 때만 보낸다(최대 10분 대기).
- 같은 언어와 날짜로 이미 만든 메일(metadata.lang, metadata.day)이 있으면 보내지 않는다. 다시 실행해도 중복 발송되지 않는다.
- 받는 사람은 구독자 metadata.lang 으로 거른다. 영어는 "ja 등 다른 언어가 아닌" 구독자 전부.
- Buttondown 필터는 lang 값이 없는 구독자를 not_equals 에서도 빼므로, 보내기 전에 lang 이 없는 구독자를 기본 언어(en)로 채운다.
"""
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


def audience(lang):
    """구독자 언어 필터. 기본 언어(영어)는 다른 언어로 표시된 구독자만 빼고 모두에게 보낸다."""
    if lang == langs.DEFAULT:
        rules = [{"field": "subscriber.metadata.lang", "operator": "not_equals", "value": other} for other in langs.LANGS if other != lang]
    else:
        rules = [{"field": "subscriber.metadata.lang", "operator": "equals", "value": lang}]
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


def recent_emails(pages=5):
    path = "/emails?ordering=-creation_date"
    for _ in range(pages):
        data = call("GET", path)
        yield from data["results"]
        nxt = data.get("next")
        if not nxt:
            return
        path = nxt.split("/v1", 1)[1]


def same_issue(meta, lang, key, value):
    """예전(언어 구분 전) 메일은 metadata.lang 이 없고 모두 영어였다."""
    return meta.get(key) == value and meta.get("lang", langs.DEFAULT) == lang


def send(mail, lang, key, value):
    """같은 언어, 같은 key 값의 메일이 이미 있으면 보내지 않는다. 다시 실행해도 중복 발송되지 않는다."""
    draft = None
    for e in recent_emails():
        if not same_issue(e.get("metadata") or {}, lang, key, value):
            continue
        if e["status"] == "draft":
            # 지난 실행이 초안만 만들고 실패한 경우: 그 초안을 최신 내용으로 고쳐 다시 보낸다.
            draft = call("PATCH", f"/emails/{e['id']}", {**mail, "template": "naked", "filters": audience(lang)})
            break
        if e["status"] in ("errored", "throttled"):
            # 일부 구독자에게 나갔을 수 있으므로 자동으로 다시 보내지 않고 실패로 드러낸다.
            raise SystemExit(f"Buttondown 발송 오류 상태라 확인 필요: {e['id']} ({e['status']})")
        print(f"이미 처리한 메일이 있어 건너뜀: {e['id']} ({e['status']})")
        return
    fill_missing_lang()
    if draft is None:
        draft = call("POST", "/emails", {**mail, "status": "draft", "template": "naked",
                                          "filters": audience(lang), "metadata": {"lang": lang, key: value}})
    call("PATCH", f"/emails/{draft['id']}", {"status": "about_to_send"})
    for _ in range(30):
        status = call("GET", f"/emails/{draft['id']}")["status"]
        if status == "sent":
            print(f"sent {draft['id']}")
            return
        time.sleep(10)
    raise SystemExit(f"발송 상태 확인 실패: {draft['id']} ({status})")


def main(lang, day):
    mail = build_email.build(lang, day)
    url = f"{build_email.SITE}/{lang}/{day}/"
    wait_live(url, build_email.parse(lang, day)["topic"], url + "thumb.png")
    send(mail, lang, "day", day)


def main_weekly(lang, end):
    import weekly
    mail = weekly.build_email(lang, end)
    url = mail.pop("url")
    wait_live(url, weekly.span(end))
    send(mail, lang, "week", end)


if __name__ == "__main__":
    langs.get(sys.argv[1])
    if "--weekly" in sys.argv:
        main_weekly(sys.argv[1], sys.argv[2])
    else:
        main(sys.argv[1], sys.argv[2])
