"""일본어 음성 크레딧 하단 이동(design/ja-credit J01)과 출처 렌더링."""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import publish  # noqa: E402

CREDIT = "음성: VOICEVOX:冥鳴ひまり"


class TestCreditFooter(unittest.TestCase):
    def _page(self):
        return ('<style>\n  .site-footer { color: #6b7684; }\n</style>\n'
                '<p class="hint"><span id="hinttext">안내</span> ' + CREDIT + '</p>\n'
                '<footer class="site-footer"><a href="/">홈</a></footer>\n')

    def test_moves_credit_below_footer_links_once(self):
        once = publish.credit_to_footer(self._page(), "ja")
        self.assertIn('<span id="hinttext">안내</span></p>', once)
        self.assertIn(f'<span class="credit">{CREDIT}</span></footer>', once)
        self.assertEqual(once.count(CREDIT), 1)
        self.assertIn(".site-footer .credit", once)
        self.assertEqual(publish.credit_to_footer(once, "ja"), once)

    def test_languages_without_credit_unchanged(self):
        page = self._page()
        self.assertEqual(publish.credit_to_footer(page, "en"), page)

    def test_generated_ja_pages_have_credit_only_in_footer(self):
        for f in sorted((ROOT / "ja").glob("20??-??-??/index.html")):
            t = f.read_text(encoding="utf-8")
            self.assertEqual(t.count(CREDIT), 1, f)
            self.assertIn(f'<span class="credit">{CREDIT}</span></footer>', t, f)
        self.assertNotIn(CREDIT, (ROOT / "en" / "2026-11-03" / "index.html").read_text(encoding="utf-8"))

    def test_template_has_no_credit_in_hint(self):
        self.assertNotIn("{{credit}}", (ROOT / "tools" / "template.html").read_text(encoding="utf-8"))


class TestOfficialSource(unittest.TestCase):
    def test_official_page_source_without_date_renders(self):
        page = (ROOT / "ja" / "2026-11-03" / "index.html").read_text(encoding="utf-8")
        self.assertIn('<p class="src">출처: <a href="https://www8.cao.go.jp/chosei/shukujitsu/gaiyou.html" target="_blank" rel="noopener">'
                      '国民の祝日について (内閣府)</a></p>', page)

    def test_routine_requires_three_source_days(self):
        r = (ROOT / "tools" / "ROUTINE.ja.md").read_text(encoding="utf-8")
        for day in ("화: 일본 문화", "수: 사회", "금: 과학과 자연"):
            line = next(x for x in r.splitlines() if day in x)
            self.assertIn("출처 필수", line)


if __name__ == "__main__":
    unittest.main()
