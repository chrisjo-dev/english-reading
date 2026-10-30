"""언어별 지난 지문으로 가는 길(이슈 #19): 지문 페이지의 다른 언어 링크, 목록 언어 탭, 날짜 검색."""
import re
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
        self.assertEqual(publish.other_lang_links("en"), '<a class="lang-go" href="/ja/archive/">일본어 지난 지문 보기 →</a>')
        self.assertEqual(publish.other_lang_links("ja"), '<a class="lang-go" href="/en/archive/">영어 지난 지문 보기 →</a>')
        self.assertNotIn("/de/", publish.other_lang_links("en"))  # 독일어는 비공개 시험 중
        self.assertIn("/ja/archive/", publish.other_lang_links("de"))

    def test_old_page_links_move_to_row_above_date(self):
        """예전 '다른 언어'(첫 화면) 링크와 2차 때 소개 문단 끝에 둔 링크를 지우고, 날짜 위 한 줄로 모은다."""
        tmp = Path(tempfile.mkdtemp())
        try:
            day = "2026-10-29"
            (tmp / "en" / day).mkdir(parents=True)
            page = (ROOT / "en" / day / "index.html").read_text(encoding="utf-8")
            page = re.sub(r'<p class="lang-row">.*?</p>\n    ', "", page)  # 줄을 빼고 예전 모양으로
            page = page.replace('<a href="#subscribe">메일로 받기</a></p>', '<a href="#subscribe">메일로 받기</a><a href="../../">다른 언어</a></p>', 1)
            (tmp / "en" / day / "index.html").write_text(page, encoding="utf-8")
            with mock.patch.object(publish, "ROOT", tmp):
                publish.patch_page("en", day)
                once = (tmp / "en" / day / "index.html").read_text(encoding="utf-8")
                publish.patch_page("en", day)
                again = (tmp / "en" / day / "index.html").read_text(encoding="utf-8")
            self.assertNotIn('<a href="../../">다른 언어</a>', once)
            self.assertIn('<p class="lang-row"><a class="lang-go" href="/ja/archive/">일본어 지난 지문 보기 →</a></p>\n    <div class="date">', once)
            self.assertEqual(once.count('class="lang-go"'), 1)
            self.assertEqual(once.count(".lang-row {"), 1)
            self.assertEqual(once, again)
        finally:
            shutil.rmtree(tmp)

    def test_lists_have_language_tabs_and_language_in_title(self):
        page = (ROOT / "ja" / "archive" / "index.html").read_text(encoding="utf-8")
        self.assertIn("<h1>일본어 지난 지문</h1>", page)
        self.assertIn('<a href="/en/archive/">영어</a>', page)
        self.assertIn('<a href="/ja/archive/" class="on" aria-current="page">일본어</a>', page)
        self.assertNotIn('/de/archive/', page)
        self.assertIn('<meta property="og:title" content="일본어 지난 지문 | 매일 일본어 읽기">', page)
        self.assertIn('<a href="/de/archive/" class="on"', (ROOT / "de" / "archive" / "index.html").read_text(encoding="utf-8"))

    def test_search_text_includes_dates(self):
        q = publish.entry("ja", "2026-10-20")["q"]
        for w in ("10월", "20일", "10/20", "2026-10-20"):
            self.assertIn(w, q)


if __name__ == "__main__":
    unittest.main()
