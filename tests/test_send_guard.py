"""발송 직전 장치(send_email.release). Buttondown 자동 검사에 걸릴 발송(하루 상한 초과, 같은 본문 재발송)을 막는다."""
import datetime
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import send_email  # noqa: E402

NOW = datetime.datetime(2026, 11, 18, 4, 8, tzinfo=datetime.timezone.utc)


def sent(i, hours_ago, body="b"):
    at = (NOW - datetime.timedelta(hours=hours_ago)).isoformat().replace("+00:00", "Z")
    return {"id": f"e{i}", "status": "sent", "publish_date": at, "body": body}


class ReleaseTest(unittest.TestCase):
    def release(self, existing, body="new body"):
        calls = []
        with mock.patch.object(send_email, "recent_emails", lambda: iter(existing)), \
                mock.patch.object(send_email, "call", lambda m, p, b=None: calls.append((m, p, b))):
            send_email.release("d1", body, now=NOW)
        return calls

    def test_normal_day_sends(self):
        calls = self.release([sent(i, 1, f"body {i}") for i in range(6)])
        self.assertEqual(calls, [("PATCH", "/emails/d1", {"status": "about_to_send"})])

    def test_same_body_within_a_day_is_blocked(self):
        # 2026-11-18: 늦은 보충이 이미 보낸 보충과 같은 본문을 다시 보내려다 email_duplicate 로 거절당했다
        with self.assertRaises(SystemExit) as cm:
            self.release([sent(1, 5, "catchup en b")], body="catchup en b")
        self.assertIn("e1", str(cm.exception))

    def test_same_body_older_than_a_day_is_fine(self):
        self.assertEqual(len(self.release([sent(1, 25, "same")], body="same")), 1)

    def test_daily_limit(self):
        many = [sent(i, 0.5, f"body {i}") for i in range(send_email.DAILY_SEND_LIMIT)]
        with self.assertRaises(SystemExit):
            self.release(many)
        self.assertEqual(len(self.release(many[:-1])), 1)

    def test_drafts_and_itself_do_not_count(self):
        drafts = [{**sent(i, 0.1, "new body"), "status": "draft"} for i in range(30)]
        me = {**sent(99, 0.1, "new body"), "id": "d1"}
        self.assertEqual(len(self.release(drafts + [me])), 1)


if __name__ == "__main__":
    unittest.main()
