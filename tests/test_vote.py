"""주제 반응 카드(이슈 #13): 페이지 삽입과 메일 링크."""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import build_email  # noqa: E402
import vote  # noqa: E402

PAGE = (ROOT / "en" / "2026-10-29" / "index.html")


class TestVoteApply(unittest.TestCase):
    def setUp(self):
        if not PAGE.exists():
            self.skipTest("렌더 HTML 없음")
        self.page = PAGE.read_text(encoding="utf-8")

    def test_page_has_one_card_badge_and_script(self):
        p = self.page
        self.assertEqual(p.count('id="vote"'), 1)
        self.assertEqual(p.count('<script id="vote-js">'), 1)
        self.assertEqual(p.count("/* vote-css */"), 1)
        self.assertIn('<div class="date">10월 29일 목요일 <span class="cat cat-future">미래</span></div>', p)
        self.assertIn('<span class="today">목 미래</span>', p)
        self.assertIn('data-cat="future" data-wd="3"', p)

    def test_apply_is_idempotent_and_replaces_old_version(self):
        self.assertEqual(vote.apply(self.page, "en", "2026-10-29"), self.page)
        old = self.page.replace(f'id="vote" data-v="{vote.VERSION}"', 'id="vote" data-v="0"')
        again = vote.apply(old, "en", "2026-10-29")
        self.assertEqual(again.count('id="vote"'), 1)
        self.assertEqual(again.count('class="cat cat-'), 2)
        self.assertEqual(again.count("/* vote-css */"), 1)
        self.assertEqual(again.count('<script id="vote-js">'), 1)

    def test_week_follows_language(self):
        self.assertIn('<span class="today">목 일과 학교</span>', vote.week_html("ja", "2026-10-29"))
        self.assertIn("월 일상생활", vote.week_html("de", "2026-10-29"))


class TestVoteEmail(unittest.TestCase):
    def test_email_date_has_no_badge_and_links_vote(self):
        if not PAGE.exists():
            self.skipTest("렌더 HTML 없음")
        b = build_email.build("en", "2026-10-29", "b")["body"]
        self.assertIn(">10월 29일 목요일</p>", b)
        self.assertIn("오늘은 미래 분야였어요", b)
        self.assertIn('href="https://read.wspace.ai.kr/en/2026-10-29/?vote=up&amp;from=email#vote"', b)
        a = build_email.build("en", "2026-10-29", "a")["body"]
        self.assertTrue(re.search(r'href="https://read\.wspace\.ai\.kr/en/2026-10-29/\?level=a&amp;vote=down&amp;from=email#vote"', a))


if __name__ == "__main__":
    unittest.main()
