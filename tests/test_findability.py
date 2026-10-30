"""언어별 지난 지문으로 가는 길(이슈 #19): 지문 페이지의 다른 언어 링크, 목록 언어 탭, 날짜 검색."""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import publish  # noqa: E402


class TestFindability(unittest.TestCase):
    def test_other_language_links_skip_hidden_languages(self):
        self.assertEqual(publish.other_lang_links("en"), '<a href="/ja/">일본어 지문 보기 →</a>')
        self.assertEqual(publish.other_lang_links("ja"), '<a href="/en/">영어 지문 보기 →</a>')
        self.assertNotIn("/de/", publish.other_lang_links("en"))  # 독일어는 비공개 시험 중
        self.assertIn("/ja/", publish.other_lang_links("de"))

    def test_old_page_link_to_home_is_replaced(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            day = "2026-10-29"
            (tmp / "en" / day).mkdir(parents=True)
            page = (ROOT / "en" / day / "index.html").read_text(encoding="utf-8")
            page = page.replace('<a href="/ja/">일본어 지문 보기 →</a>', '<a href="../../">다른 언어</a>')
            (tmp / "en" / day / "index.html").write_text(page, encoding="utf-8")
            with mock.patch.object(publish, "ROOT", tmp):
                publish.patch_page("en", day)
                once = (tmp / "en" / day / "index.html").read_text(encoding="utf-8")
                publish.patch_page("en", day)
                again = (tmp / "en" / day / "index.html").read_text(encoding="utf-8")
            self.assertNotIn('<a href="../../">다른 언어</a>', once)
            self.assertIn('<a href="/ja/">일본어 지문 보기 →</a>', once)
            self.assertEqual(once, again)
        finally:
            shutil.rmtree(tmp)

    def test_lists_have_language_tabs_and_language_in_title(self):
        page = (ROOT / "ja" / "archive" / "index.html").read_text(encoding="utf-8")
        self.assertIn("<h1>일본어 지난 지문</h1>", page)
        self.assertIn('<a href="/en/archive/">영어</a>', page)
        self.assertIn('<a href="/ja/archive/" class="on" aria-current="page">일본어</a>', page)
        self.assertNotIn('/de/archive/', page)
        self.assertIn('<a href="/de/archive/" class="on"', (ROOT / "de" / "archive" / "index.html").read_text(encoding="utf-8"))

    def test_search_text_includes_dates(self):
        q = publish.entry("ja", "2026-10-20")["q"]
        for w in ("10월", "20일", "10/20", "2026-10-20"):
            self.assertIn(w, q)


if __name__ == "__main__":
    unittest.main()
