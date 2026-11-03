"""의견 보내기(이슈 #21): 하단 링크 위 '기능 건의', '버그 제보' 메일 버튼과 뉴스레터 하단 한 줄."""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import build_email  # noqa: E402
import feedback  # noqa: E402
import publish  # noqa: E402

OLD_PAGE = ROOT / "tests" / "fixtures" / "old_gnb_en_2026-10-29.html"


def query(href):
    href = href.replace("&amp;", "&")
    parts = urlsplit(href)
    return parts.path, {k: v[0] for k, v in parse_qs(parts.query).items()}


class TestFeedback(unittest.TestCase):
    def test_mailto_subject_and_body_round_trip(self):
        to, q = query(feedback.mailto(feedback.BUG_SUBJECT, feedback.bug_body("https://read.wspace.ai.kr/en/2026-11-03/")))
        self.assertEqual(to, "wonsang.dev@gmail.com")
        self.assertEqual(q["subject"], "[독해한입] 버그 제보")
        self.assertIn("페이지: https://read.wspace.ai.kr/en/2026-11-03/\r\n기기: ", q["body"])
        _, q = query(feedback.mailto(feedback.IDEA_SUBJECT, feedback.idea_body("ja")))
        self.assertEqual(q["subject"], "[독해한입] 기능 건의")
        self.assertTrue(q["body"].endswith("보던 언어: 일본어"))
        self.assertNotIn("보던 언어", feedback.idea_body())

    def test_old_page_gets_block_once_above_footer(self):
        """예전 생성 페이지에 patch_page 를 두 번 돌려도 블록, CSS, 스크립트가 하나씩만 하단 링크 바로 위에 있다."""
        tmp = Path(tempfile.mkdtemp())
        try:
            day = "2026-10-29"
            (tmp / "en" / day).mkdir(parents=True)
            (tmp / "en" / day / "index.html").write_text(OLD_PAGE.read_text(encoding="utf-8"), encoding="utf-8")
            with mock.patch.object(publish, "ROOT", tmp):
                publish.patch_page("en", day)
                once = (tmp / "en" / day / "index.html").read_text(encoding="utf-8")
                publish.patch_page("en", day)
                again = (tmp / "en" / day / "index.html").read_text(encoding="utf-8")
        finally:
            shutil.rmtree(tmp)
        self.assertEqual(once, again)
        for mark in ("<!-- fb -->", "/* fb */", '<script id="fb-js">', ">기능 건의</a>", ">버그 제보</a>"):
            self.assertEqual(once.count(mark), 1, mark)
        self.assertLess(once.index('id="subscribe"'), once.index("<!-- fb -->"))
        self.assertIn('<!-- /fb -->\n<footer class="site-footer">', once)
        self.assertIn("%ED%8E%98%EC%9D%B4%EC%A7%80%3A%20https%3A%2F%2Fread.wspace.ai.kr%2Fen%2F2026-10-29%2F", once)

    def test_generated_pages_have_block(self):
        for rel in ("en/2026-11-03/index.html", "ja/archive/index.html", "de/index.html", "en/review/2026-11-01/index.html"):
            page = (ROOT / rel).read_text(encoding="utf-8")
            self.assertEqual(page.count('<section class="fb"'), 1, rel)
            self.assertIn("독해한입에 바라는 점이 있나요?", page)

    def test_page_without_footer_is_untouched(self):
        page = "<html><head><style>a{}</style></head><body><main></main></body></html>"
        self.assertEqual(feedback.apply(page, "en"), page)

    def test_email_footer_line(self):
        body = build_email.build("en", "2026-11-03")["body"]
        self.assertEqual(body.count("독해한입에 바라는 점이 있으면"), 1)
        self.assertIn(">기능 건의</a>, 이상한 곳을 보셨다면 <a", body)
        self.assertIn("subject=%5B%EB%8F%85%ED%95%B4%ED%95%9C%EC%9E%85%5D%20%EB%B2%84%EA%B7%B8%20%EC%A0%9C%EB%B3%B4", body)
        self.assertLess(body.index("지난 지문 모아 보기"), body.index("독해한입에 바라는 점이 있으면"))

    def test_landing_footer_has_buttons(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("기능 건의", page)
        self.assertIn("버그 제보", page)


if __name__ == "__main__":
    unittest.main()
