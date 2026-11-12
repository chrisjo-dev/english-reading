"""언어별 지난 지문으로 가는 길(이슈 #19, #20): 위 메뉴 언어 시트, 목록 언어 탭, 날짜 검색."""
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

# 위 메뉴 시안 A 이전의 생성 페이지(예전 모양을 새 모양으로 바꾸는 테스트에 쓴다)
OLD_PAGE = ROOT / "tests" / "fixtures" / "old_gnb_en_2026-10-29.html"


class TestFindability(unittest.TestCase):
    def test_menu_languages_skip_hidden_languages(self):
        """위 메뉴 언어 시트와 PC 언어 탭: 숨긴 언어는 빼고, 지금 보고 있는 언어는 숨겨도 보인다."""
        self.assertEqual(publish.public_langs(), ["en", "ja", "de"])  # 독일어 공개(2026-10-30)
        with mock.patch.dict(publish.langs.LANGS["de"], {"noindex": True}):
            self.assertNotIn('href="/de/archive/"', publish.gnb.header_html("en"))
            self.assertIn('href="/de/archive/"', publish.gnb.header_html("de"))

    def test_old_page_language_row_moves_to_menu_sheet(self):
        """예전 '다른 언어' 링크, 날짜 위 알약 줄, 소개 끝 '메일로 받기'를 지우고 위 메뉴 시트로 모은다(이슈 #20)."""
        tmp = Path(tempfile.mkdtemp())
        try:
            day = "2026-10-29"
            (tmp / "en" / day).mkdir(parents=True)
            page = OLD_PAGE.read_text(encoding="utf-8")  # 시안 A 이전 생성물 그대로
            self.assertIn('class="lang-row"', page)
            page = page.replace('<a href="#subscribe">메일로 받기</a></p>', '<a href="#subscribe">메일로 받기</a><a href="../../">다른 언어</a></p>', 1)
            (tmp / "en" / day / "index.html").write_text(page, encoding="utf-8")
            with mock.patch.object(publish, "ROOT", tmp):
                publish.patch_page("en", day)
                once = (tmp / "en" / day / "index.html").read_text(encoding="utf-8")
                publish.patch_page("en", day)
                again = (tmp / "en" / day / "index.html").read_text(encoding="utf-8")
            self.assertNotIn('<a href="../../">다른 언어</a>', once)
            self.assertNotIn("lang-go", once)
            self.assertNotIn("lang-row", once)
            self.assertNotRegex(once, r'<p class="intro">[^<]*<a href="#subscribe">')
            self.assertIn('<a class="gs-past" href="/ja/archive/"', once)
            self.assertIn('<a class="gs-past" href="/de/archive/"', once)
            self.assertEqual(once, again)
        finally:
            shutil.rmtree(tmp)

    def test_lists_have_language_tabs_and_language_in_title(self):
        page = (ROOT / "ja" / "archive" / "index.html").read_text(encoding="utf-8")
        self.assertIn("<h1>일본어 지난 지문</h1>", page)
        self.assertIn('<a href="/en/archive/">영어</a>', page)
        self.assertIn('<a href="/ja/archive/" class="on" aria-current="page">일본어</a>', page)
        self.assertIn('<a href="/de/archive/">독일어</a>', page)
        self.assertIn('<meta property="og:title" content="일본어 지난 지문 | 독해한입">', page)
        self.assertIn('<a href="/de/archive/" class="on"', (ROOT / "de" / "archive" / "index.html").read_text(encoding="utf-8"))

    def test_past_page_title_has_no_today_and_german_is_indexed(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            day = "2026-10-28"
            (tmp / "de" / day).mkdir(parents=True)
            page = (ROOT / "de" / day / "index.html").read_text(encoding="utf-8")
            page = page.replace("<title>독일어 읽기,", "<title>오늘의 독일어 읽기,").replace('<link rel="stylesheet"', '<meta name="robots" content="noindex">\n<link rel="stylesheet"', 1)
            (tmp / "de" / day / "index.html").write_text(page, encoding="utf-8")
            with mock.patch.object(publish, "ROOT", tmp):
                publish.patch_page("de", day)
            out = (tmp / "de" / day / "index.html").read_text(encoding="utf-8")
            self.assertRegex(out, r"<title>[^<]+ 독일어 독해 B1~B2, 2026년 10월 28일 \| 독해한입</title>")
            self.assertNotIn("오늘의", out[:out.index("</title>")])
            self.assertNotIn('name="robots" content="noindex"', out)
        finally:
            shutil.rmtree(tmp)

    def test_top_menu_names_the_language(self):
        """위 메뉴 언어 칩은 지금 언어 이름, PC '지난 지문'은 그 언어 목록으로 간다. 목록 페이지에서는 켜져 있다."""
        page = (ROOT / "ja" / "2026-10-20" / "index.html").read_text(encoding="utf-8")
        self.assertIn('<span class="gnb-pill">일본어<svg', page)
        self.assertIn('<a class="gnb-past" href="/ja/archive/">지난 지문</a>', page)
        arch = (ROOT / "de" / "archive" / "index.html").read_text(encoding="utf-8")
        self.assertIn('<a class="gnb-past on" href="/de/archive/" aria-current="page">지난 지문</a>', arch)
        self.assertIn('<span class="gnb-pill">독일어<svg', arch)
        self.assertNotIn("/* gnb-narrow */", arch)
        self.assertIn("{{gnb}}<main>", (ROOT / "tools" / "template.html").read_text(encoding="utf-8"))

    def test_search_text_includes_dates(self):
        q = publish.entry("ja", "2026-10-20")["q"]
        for w in ("10월", "20일", "10/20", "2026-10-20"):
            self.assertIn(w, q)


if __name__ == "__main__":
    unittest.main()
