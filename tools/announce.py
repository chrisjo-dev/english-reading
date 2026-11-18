"""기존 메일 구독자 전원에게 한 번 보내는 안내 메일. 매일 지문 메일(send_email.py)과 따로 손으로만 보낸다.

사용: python3 tools/announce.py login-2026-11 html > /tmp/a.html                (본문만 만든다. 키가 필요 없다)
      BUTTONDOWN_API_KEY=... python3 tools/announce.py login-2026-11 draft       (Buttondown 에 초안만 만든다. 대시보드에서 미리 보기)
      BUTTONDOWN_API_KEY=... python3 tools/announce.py login-2026-11 send        (구독자 전원에게 보낸다)
- 받는 사람은 언어와 수준에 상관없이 구독자 전원이다(filters 를 비운다).
- 같은 안내(metadata.announce)를 이미 보냈으면 다시 보내지 않는다. 초안만 있으면 최신 내용으로 고쳐 쓴다.
- 워크플로: .github/workflows/announce.yml (키는 GitHub secret 에만 있다)
"""
import html
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_email import BG, FONT, INK, MUTED, SITE, SUB  # noqa: E402

BLUE, BLUE_SOFT, LINE, GREEN, CORAL = "#2a52d4", "#eff3fd", "#eef0f3", "#0f9d6b", "#f04452"
CARD = "background:#ffffff;border-radius:20px;padding:22px 20px;"
H2 = f"margin:0 0 14px;font-size:19px;font-weight:700;color:{INK};"


def _shell(preheader, cards, foot):
    """지문 메일과 같은 틀: 회색 바탕, 가운데 로고, 흰 카드, 아래 수신거부. preheader 는 받은편지함 미리보기 문구."""
    gap = '<tr><td style="height:12px;"></td></tr>'
    return f"""<!-- buttondown-editor-mode: plaintext -->
<div style="display:none;max-height:0;overflow:hidden;opacity:0;">{html.escape(preheader)}</div>
<div style="background:{BG};padding:16px 0;font-family:{FONT};word-break:keep-all;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;margin:0 auto;">
<tr><td style="padding:16px 0 12px;text-align:center;"><img src="{SITE}/assets/brand/badge-192.png" width="88" height="88" alt="독해한입" style="display:block;margin:0 auto;border:0;"></td></tr>
{gap.join(f'<tr><td style="{CARD}">{c}</td></tr>' for c in cards)}
<tr><td style="padding:16px 8px 0;font-size:12px;line-height:1.6;color:{MUTED};text-align:center;">{foot}</td></tr>
</table>
</div>"""


def login_2026_11():
    """로그인 가입 안내(시안 design/kakao-login K19, 2026-11-18)."""
    join = f"{SITE}/join/?next=%2F&amp;from=mail"

    def why(n, title, text, extra=""):
        top = "" if n == 1 else f"border-top:1px solid {LINE};"
        return (f'<tr><td valign="top" style="width:38px;padding:{0 if n == 1 else 14}px 0 14px;{top}">'
                f'<div style="width:26px;height:26px;border-radius:13px;background:{BLUE_SOFT};color:{BLUE};font-size:13px;font-weight:800;line-height:26px;text-align:center;">{n}</div></td>'
                f'<td style="padding:{0 if n == 1 else 14}px 0 14px;{top}">'
                f'<p style="margin:0 0 4px;font-size:16px;font-weight:700;color:{INK};">{title}</p>'
                f'<p style="margin:0;font-size:15px;line-height:1.65;color:{SUB};">{text}</p>{extra}</td></tr>')

    chips = '<p style="margin:8px 0 0;">' + "".join(
        f'<span style="display:inline-block;margin:0 4px 4px 0;padding:4px 9px;border-radius:8px;background:{BLUE_SOFT};color:{BLUE};font-size:13px;font-weight:600;">{t}</span>'
        for t in ("뜻 고르기", "단어 쓰기", "빈칸 채우기")) + "</p>"
    # 위 메뉴 마이페이지 버튼(K15)을 그림 대신 글자로 보여 준다
    pill = (f'<p style="margin:8px 0 0;"><span style="display:inline-block;padding:5px 12px 5px 5px;border-radius:999px;background:{BLUE_SOFT};font-size:14px;font-weight:700;color:{INK};">'
            f'<span style="display:inline-block;width:24px;height:24px;border-radius:12px;background:{BLUE};color:#ffffff;text-align:center;line-height:24px;font-size:13px;margin-right:6px;vertical-align:middle;">나</span>'
            f'마이페이지<span style="color:{CORAL};margin-left:6px;">🔥3</span></span></p>')

    def same(text):
        return (f'<tr><td valign="top" style="width:18px;padding:9px 0 0 4px;"><div style="width:6px;height:6px;border-radius:3px;background:{GREEN};"></div></td>'
                f'<td style="padding:0 0 8px;font-size:15px;line-height:1.6;color:{SUB};">{text}</td></tr>')

    cards = [
        f'<p style="margin:0 0 4px;font-size:13px;font-weight:700;color:{BLUE};">새 기능</p>'
        f'<h1 style="margin:2px 0 12px;font-size:24px;line-height:1.35;font-weight:800;color:{INK};">외운 단어, 이제 <span style="color:{BLUE};">어느 기기에서든</span> 이어서 공부해요</h1>'
        f'<p style="margin:0;font-size:16px;line-height:1.65;color:{SUB};">독해한입에 로그인이 생겼어요. 카카오나 Google 계정으로 바로 가입할 수 있고, 무료예요.</p>'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:18px;"><tr>'
        f'<td align="center" style="background:{BLUE};border-radius:14px;"><a href="{join}" style="display:block;padding:16px 12px;font-size:16px;font-weight:700;color:#ffffff;text-decoration:none;">가입하고 단어 기록 이어 가기</a></td></tr></table>'
        f'<p style="margin:10px 0 0;font-size:13px;color:{MUTED};text-align:center;">카카오와 Google 중 편한 쪽을 고르면 돼요.</p>',

        f'<h2 style="{H2}">가입하면 이렇게 달라져요</h2>'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">'
        + why(1, "단어 기록이 사라지지 않아요",
              "지금은 외운 단어와 복습 날짜가 쓰던 브라우저에만 남아요. 휴대폰과 PC가 따로 기억하고, 사이트 데이터를 지우면 사라져요. "
              "가입하면 계정에 저장돼서 어느 기기에서 열어도 이어져요.")
        + why(2, "단어 문제 풀기가 열려요", "카드로 외운 단어를 문제로 확인해요. 문제 풀기는 가입한 분께 열려요.", chips)
        + why(3, "며칠째 공부했는지 보여요", "연속 학습일이 사이트 위 메뉴와 마이페이지에 보여요.", pill)
        + "</table>",

        f'<h2 style="{H2}">그대로인 것</h2>'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">'
        + same("매일 아침 지문 메일은 지금처럼 와요.")
        + same("지문 읽기와 음성, 단어 카드 외우기와 복습은 가입하지 않아도 계속 무료예요.")
        + same(f'로그인 정보는 광고에 쓰지 않아요. 자세한 내용은 <a href="{SITE}/privacy/#account" style="color:{SUB};">개인정보처리방침</a>에 있어요.')
        + "</table>",
    ]
    foot = ("독해한입 지문 메일을 구독하신 분께 보내는 안내예요.<br>"
            f'더 받지 않으려면 <a href="{{{{ unsubscribe_url }}}}" style="color:{MUTED};">수신거부</a>를 눌러 주세요.')
    preheader = "카카오나 Google로 가입하면 단어 기록이 어느 기기에서든 이어져요. 무료예요."
    return {"subject": "외운 단어, 이제 계정에 저장돼요 | 독해한입", "body": _shell(preheader, cards, foot)}


ANNOUNCES = {"login-2026-11": login_2026_11}


def find(key):
    import send_email
    for e in send_email.recent_emails():
        if (e.get("metadata") or {}).get("announce") == key:
            return e
    return None


def draft(key):
    """같은 안내의 초안이 있으면 최신 내용으로 고치고, 없으면 만든다. 이미 보냈으면 None."""
    import send_email
    mail = ANNOUNCES[key]()
    e = find(key)
    if e and e["status"] != "draft":
        print(f"이미 처리한 안내 메일이 있어 건너뜀: {e['id']} ({e['status']})")
        return None
    body = {**mail, "template": "naked"}  # filters 를 주지 않으면 구독자 전원
    if e:
        return send_email.call("PATCH", f"/emails/{e['id']}", body)
    return send_email.call("POST", "/emails", {**body, "status": "draft", "metadata": {"announce": key}})


def send(key):
    import send_email
    d = draft(key)
    if d is None:
        return
    send_email.call("PATCH", f"/emails/{d['id']}", {"status": "about_to_send"})
    status = None
    for _ in range(30):
        status = send_email.call("GET", f"/emails/{d['id']}")["status"]
        if status == "sent":
            print(f"sent {d['id']}")
            return
        time.sleep(10)
    if status == "in_flight":
        print(f"::warning::발송 대기 중(in_flight): {d['id']}. Buttondown 큐에 있어 곧 나갈 가능성이 높습니다.")
        return
    raise SystemExit(f"발송 상태 확인 실패: {d['id']} ({status})")


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ANNOUNCES or sys.argv[2] not in ("html", "draft", "send"):
        raise SystemExit(f"사용: python3 tools/announce.py <{'|'.join(ANNOUNCES)}> <html|draft|send>")
    key, mode = sys.argv[1], sys.argv[2]
    if mode == "html":
        print(ANNOUNCES[key]()["body"])
    elif mode == "draft":
        d = draft(key)
        if d:
            print(json.dumps({"id": d["id"], "status": d["status"], "subject": d.get("subject")}, ensure_ascii=False))
    else:
        send(key)
