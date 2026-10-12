"""배포된 날짜 페이지를 확인한 뒤 Buttondown 으로 구독자에게 메일을 보낸다.

사용: BUTTONDOWN_API_KEY=... python3 tools/send_email.py 2026-10-12
- 페이지와 썸네일이 200 으로 열리고 페이지에 주제어가 보일 때만 보낸다(최대 10분 대기).
- 같은 날짜로 이미 만든 메일(metadata.day)이 있으면 보내지 않는다. 다시 실행해도 중복 발송되지 않는다.
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


def wait_live(day, topic):
    url = f"{build_email.SITE}/{day}/"
    for _ in range(40):
        try:
            with urllib.request.urlopen(url + f"?v={time.time():.0f}", timeout=15) as r:
                page = r.read().decode("utf-8")
            with urllib.request.urlopen(url + "thumb.png", timeout=15) as r:
                thumb_ok = r.status == 200
            if topic in page and thumb_ok:
                return
        except urllib.error.URLError:
            pass
        time.sleep(15)
    raise SystemExit(f"페이지가 열리지 않아 메일을 보내지 않음: {url}")


def main(day):
    mail = build_email.build(day)
    topic = build_email.parse(day)["topic"]
    wait_live(day, topic)
    for e in call("GET", "/emails?ordering=-creation_date")["results"][:50]:
        if (e.get("metadata") or {}).get("day") == day:
            print(f"이미 만든 메일이 있어 건너뜀: {e['id']} ({e['status']})")
            return
    draft = call("POST", "/emails", {**mail, "status": "draft", "template": "naked", "metadata": {"day": day}})
    call("PATCH", f"/emails/{draft['id']}", {"status": "about_to_send"})
    for _ in range(30):
        status = call("GET", f"/emails/{draft['id']}")["status"]
        if status == "sent":
            print(f"sent {draft['id']}")
            return
        time.sleep(10)
    raise SystemExit(f"발송 상태 확인 실패: {draft['id']} ({status})")


if __name__ == "__main__":
    main(sys.argv[1])
