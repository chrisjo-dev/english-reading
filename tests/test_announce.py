"""기존 구독자 안내 메일(tools/announce.py, 시안 design/kakao-login K19). 본문 내용과 중복 발송 막기를 본다."""
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import announce  # noqa: E402
import send_email  # noqa: E402


class BodyTest(unittest.TestCase):
    def test_login_mail(self):
        m = announce.login_2026_11()
        self.assertEqual(m["subject"], "외운 단어, 이제 계정에 저장돼요 | 독해한입")
        b = m["body"]
        self.assertIn("{{ unsubscribe_url }}", b)
        self.assertIn("https://dokhaehanip.com/join/?next=%2F&amp;from=mail", b)
        self.assertIn("https://dokhaehanip.com/privacy/#account", b)
        for t in ("뜻 고르기", "단어 쓰기", "빈칸 채우기", "매일 아침 지문 메일은 지금처럼 와요."):
            self.assertIn(t, b)
        self.assertNotIn("·", b)
        self.assertEqual(b.count("{{"), 1)  # 수신거부 변수 말고는 템플릿 문법이 없어야 한다


class SendTest(unittest.TestCase):
    def run_send(self, existing):
        calls = []

        def call(method, path, body=None):
            calls.append((method, path, body))
            if method == "GET":
                return {"status": "sent"}
            return {"id": "new" if method == "POST" else path.rsplit("/", 1)[1], "status": "draft"}

        with mock.patch.object(send_email, "recent_emails", lambda: iter(existing)), \
                mock.patch.object(send_email, "call", call), mock.patch.object(send_email.time, "sleep", lambda s: None):
            announce.send("login-2026-11")
        return calls

    def test_new_mail_goes_to_everyone_once(self):
        calls = self.run_send([{"id": "x", "status": "sent", "metadata": {"lang": "en", "day": "2026-11-18"}}])
        post = [c for c in calls if c[0] == "POST"]
        self.assertEqual(len(post), 1)
        self.assertEqual(post[0][2]["metadata"], {"announce": "login-2026-11"})
        self.assertNotIn("filters", post[0][2])  # 언어, 수준 필터 없이 구독자 전원
        self.assertIn(("PATCH", "/emails/new", {"status": "about_to_send"}), calls)

    def test_already_sent_is_skipped(self):
        calls = self.run_send([{"id": "a", "status": "sent", "metadata": {"announce": "login-2026-11"}}])
        self.assertEqual(calls, [])

    def test_errored_mail_is_not_buried(self):
        with self.assertRaises(SystemExit):
            self.run_send([{"id": "e", "status": "errored", "metadata": {"announce": "login-2026-11"}}])

    def test_leftover_draft_is_reused(self):
        calls = self.run_send([{"id": "d", "status": "draft", "metadata": {"announce": "login-2026-11"}}])
        self.assertFalse([c for c in calls if c[0] == "POST"])
        self.assertEqual(calls[0][:2], ("PATCH", "/emails/d"))
        self.assertIn(("PATCH", "/emails/d", {"status": "about_to_send"}), calls)


class CatchupOncePerDayTest(unittest.TestCase):
    """보충 메일은 하루 한 번(두 번째는 본문이 같아 Buttondown 이 email_duplicate 로 막는다, 2026-11-18)."""

    def run_catchup(self, emails):
        calls = []
        with mock.patch.object(send_email, "recent_emails", lambda pages=5: iter(emails)), \
                mock.patch.object(send_email, "call", lambda *a, **k: calls.append(a) or {}), \
                mock.patch.object(send_email, "subscribers", lambda: calls.append("subscribers") or []), \
                mock.patch.object(send_email, "reached", lambda i: set()), \
                mock.patch.object(send_email, "fill_missing_lang", lambda: None):
            send_email.catchup("en", "2026-11-18", "b")
        return calls

    MAIN = {"id": "m", "status": "sent", "publish_date": "2026-11-17T21:55:00Z",
            "metadata": {"lang": "en", "day": "2026-11-18", "level": "b"}}

    def test_second_catchup_is_skipped(self):
        done = {"id": "c", "status": "sent", "metadata": {"lang": "en", "level": "b", "catchup_of": "en:2026-11-18:b"}}
        self.assertEqual(self.run_catchup([self.MAIN, done]), [])

    def test_first_catchup_still_looks_for_targets(self):
        self.assertIn("subscribers", self.run_catchup([self.MAIN]))


if __name__ == "__main__":
    unittest.main()
