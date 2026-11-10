"""보충 발송(catchup)이 본 메일이 빠진 오늘 지문은 본 메일로 보내는지 검사한다(2026-11-10 ja 누락)."""
import datetime
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import send_email  # noqa: E402


def today_kst():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date().isoformat()


class CatchupSendsMissingMainTest(unittest.TestCase):
    def test_today_without_main_sends_main(self):
        calls = []
        with patch.object(send_email, "recent_emails", lambda **k: []), \
                patch.object(send_email, "main", lambda *a, **k: calls.append(a)):
            send_email.catchup("ja", today_kst(), "a")
        self.assertEqual(calls, [("ja", today_kst(), "a")])

    def test_past_day_without_main_still_refuses(self):
        calls = []
        with patch.object(send_email, "recent_emails", lambda **k: []), \
                patch.object(send_email, "main", lambda *a, **k: calls.append(a)):
            with self.assertRaises(SystemExit):
                send_email.catchup("ja", "2026-10-01", "a")
        self.assertEqual(calls, [])

    def test_main_already_sent_does_not_resend_main(self):
        day = today_kst()
        sent = {"id": "e1", "status": "sent", "publish_date": "2000-01-01T00:00:00Z",
                "metadata": {"lang": "ja", "day": day, "level": "a"}}
        calls = []
        with patch.object(send_email, "recent_emails", lambda **k: [sent]), \
                patch.object(send_email, "main", lambda *a, **k: calls.append(a)), \
                patch.object(send_email, "fill_missing_lang", lambda: (_ for _ in ()).throw(SystemExit("stop"))):
            with self.assertRaises(SystemExit):
                send_email.catchup("ja", day, "a")
        self.assertEqual(calls, [], "본 메일이 있으면 보충 경로로 가야 합니다")


if __name__ == "__main__":
    unittest.main()
