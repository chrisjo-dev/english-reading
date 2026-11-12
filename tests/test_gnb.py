"""위 메뉴(GNB) 시안 A(이슈 #20, design/gnb-mobile G01~G03).

- 예전 모양 지문 페이지(떠 있는 바, 날짜 위 다른 언어 줄, '기초로 보기' 링크)를 새 모양으로 바꾸고, 두 번 돌려도 같다
- 모든 생성 페이지(지문, 언어 첫 화면, 지난 지문, 주간 복습)가 같은 위 메뉴를 쓴다
- 시트 aria(role=dialog, aria-modal, aria-expanded), 이번 주 단어 복습 줄은 복습 페이지가 있을 때만
- 랜딩(landing/src/app/gnb.css)과 같은 CSS
"""
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import gnb  # noqa: E402
import publish  # noqa: E402

OLD_PAGE = ROOT / "tests" / "fixtures" / "old_gnb_en_2026-10-29.html"


class TestOldPageToNewGnb(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.day = "2026-10-29"
        (self.tmp / "en" / self.day).mkdir(parents=True)
        self.old = OLD_PAGE.read_text(encoding="utf-8")
        (self.tmp / "en" / self.day / "index.html").write_text(self.old, encoding="utf-8")
        with mock.patch.object(publish, "ROOT", self.tmp):
            publish.patch_page("en", self.day)
            self.once = (self.tmp / "en" / self.day / "index.html").read_text(encoding="utf-8")
            publish.patch_page("en", self.day)
            self.again = (self.tmp / "en" / self.day / "index.html").read_text(encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_fixture_is_old_shape(self):
        for old in ('<nav aria-label="사이트 메뉴">', 'class="lang-row"', "기초로 보기", "/* gnb-narrow */", "toLevelA.hidden = isA;"):
            self.assertIn(old, self.old)

    def test_idempotent(self):
        self.assertEqual(self.once, self.again)

    def test_old_menu_gone(self):
        p = self.once
        for gone in ('<nav aria-label="사이트 메뉴">', "lang-row", "lang-go", "기초로 보기", "level-link {", "/* gnb-narrow */",
                     ".gnb nav", ".gnb .brand", "toLevelA.hidden", "top: 12px; z-index: 20"):
            self.assertNotIn(gone, p, gone)

    def test_new_menu_outside_main_and_once(self):
        p = self.once
        self.assertEqual(p.count('<header class="gnb">'), 1)
        self.assertEqual(p.count("/* gnb-a */"), 1)
        self.assertEqual(p.count('<script id="gnb-js">'), 1)
        self.assertLess(p.index('<header class="gnb">'), p.index("<main>"))
        self.assertLess(p.index('id="gnb-sheet"'), p.index("<main>"))
        # 복습 띠는 본문 맨 위에 그대로
        self.assertLess(p.index("<main>"), p.index('id="dr-due"'))
        self.assertIn('<a class="gnb-tap gnb-mail" href="#subscribe">', p)

    def test_level_segment_at_card_bottom(self):
        p = self.once
        top = p[p.index('<div class="top">'):p.index('<section class="card" id="passage">')]
        self.assertTrue(top.rstrip().endswith("</nav></div>\n  </div>".rstrip()), top[-200:])
        self.assertIn('<span class="lb">읽기 수준</span>', top)
        self.assertIn('<a href="?level=a" id="to-level-a">기초</a><a href="?level=b" id="to-level-b">중급</a>', top)
        self.assertLess(top.index('class="intro"'), top.index('class="lvl"'))
        # 저장 키와 전환 동작은 그대로
        self.assertIn("localStorage.setItem('read_level:' + _gaLang, to);", p)
        self.assertIn("toLevelA.setAttribute('aria-current', String(isA));", p)
        self.assertIn("html.level-a #to-level-a", p)

    def test_intro_has_no_mail_link(self):
        intro = re.search(r'<p class="intro">.*?</p>', self.once).group(0)
        self.assertNotIn("<a", intro)


class TestMenuMarkup(unittest.TestCase):
    def test_sheet_aria_and_languages(self):
        h = gnb.header_html("de")
        self.assertIn('aria-haspopup="dialog" aria-expanded="false" aria-controls="gnb-sheet"', h)
        self.assertIn('role="dialog" aria-modal="true" aria-labelledby="gnb-sheet-h" tabindex="-1" hidden', h)
        self.assertEqual(h.count('class="gs-row'), 3)
        # 줄 전체가 링크: 배지가 .gs-tx 링크 안에 있다(지난 지문은 따로)
        self.assertIn('<div class="gs-row on"><a class="gs-tx" href="/de/" data-today="de" aria-current="true">'
                      '<span class="gs-badge" aria-hidden="true">DE</span><span class="gs-tt">', h)
        self.assertNotIn('"gs-row"><span class="gs-badge"', h)
        self.assertEqual(h.count('<a class="gs-past"'), 3)
        self.assertIn('<a href="/de/" data-today="de" class="on" aria-current="page">독일어</a>', h)
        self.assertIn('<span class="gnb-pill">독일어<svg', h)

    def test_sheet_title_is_not_a_heading(self):
        # 시트는 본문 h1 보다 앞에 있어 제목을 heading 으로 두면 페이지 헤딩 순서가 h2, h1 이 된다
        h = gnb.header_html("en")
        self.assertNotRegex(h, r"<h[1-6]")
        self.assertIn('<p class="gs-title" id="gnb-sheet-h">어떤 언어를 읽을까요?</p>', h)

    def test_sheet_focus_goes_to_sheet_itself(self):
        # 시트를 열면 링크가 아니라 시트 자체(tabindex=-1, 테두리 없음)에 포커스. iOS Safari 파란 상자 방지
        h = gnb.header_html("en")
        self.assertIn('aria-labelledby="gnb-sheet-h" tabindex="-1" hidden>', h)
        self.assertIn(".gnb-sheet:focus { outline: none; }", gnb.CSS)
        self.assertIn("sheet.focus();", gnb.SCRIPT)
        self.assertNotIn(".gs-tx').focus", gnb.SCRIPT)
        self.assertNotIn("cur.focus()", gnb.SCRIPT)
        # 시트에 포커스가 있을 때 Tab 은 첫 항목, Shift+Tab 은 마지막 항목
        self.assertIn("if(document.activeElement===sheet){e.preventDefault();(e.shiftKey?z:a).focus();}", gnb.SCRIPT)
        # 닫으면 칩으로 돌아간다
        self.assertIn("chip.focus();", gnb.SCRIPT)

    def test_sheet_theme_color_tint_and_restore(self):
        s = gnb.SCRIPT
        # 흰 바탕 위 rgba(16,24,40,.40) 합성색
        self.assertEqual("#%02x%02x%02x" % tuple(round(255 * .6 + c * .4) for c in (16, 24, 40)), "#9fa3a9")
        self.assertIn("tm.setAttribute('content','#9fa3a9');", s)
        self.assertIn("if(tprev===null)tm.remove();else tm.setAttribute('content',tprev);", s)
        self.assertIn("tint(true);sheet.focus();", s)
        self.assertEqual(s.count("tint(false);"), 2)  # 닫기, pageshow
        nav = (ROOT / "landing" / "src" / "components" / "Nav.tsx").read_text(encoding="utf-8")
        for x in ('const SHEET_THEME = "#9fa3a9";', "untint();", "sheet.current?.focus();", "tabIndex={-1}",
                  "(e.shiftKey ? z : a).focus();"):
            self.assertIn(x, nav)

    def test_sheet_single_left_baseline_and_bottom_padding(self):
        c = gnb.CSS
        # 제목, 안내, 구분선, 배지(줄 링크 padding-left 12px) 모두 시트 padding 16 + 12 = 28px
        self.assertIn("padding: 8px 16px calc(12px + env(safe-area-inset-bottom));", c)
        self.assertIn(".gnb-sheet .gs-title { font-size: 20px; font-weight: 800; letter-spacing: -0.03em; padding: 0 12px;", c)
        self.assertIn(".gnb-sheet .gs-hint { font-size: 14px; color: #6b7684; margin: 4px 12px 12px;", c)
        self.assertIn(".gnb-sheet hr { border: 0; height: 1px; background: #e5e8eb; margin: 8px 12px; }", c)
        self.assertIn(".gs-tx { flex: 1; min-width: 0; display: flex; align-items: center; gap: 12px; padding: 10px 0 10px 12px;", c)
        self.assertIn(".gs-review { display: flex; align-items: center; gap: 12px; min-height: 60px; padding: 8px 8px 8px 12px;", c)

    def test_review_row_only_when_review_exists(self):
        with tempfile.TemporaryDirectory() as t, mock.patch.object(gnb, "ROOT", Path(t)):
            self.assertIn('id="gnb-review" data-lang="de" href="/de/archive/" hidden', gnb.header_html("de"))
            (Path(t) / "de" / "review" / "2026-11-01").mkdir(parents=True)
            (Path(t) / "de" / "review" / "2026-11-01" / "index.html").write_text("x")
            self.assertIn('id="gnb-review" data-lang="de" href="/de/review/2026-11-01/">', gnb.header_html("de"))

    def test_all_generated_pages_share_menu(self):
        pages = [ROOT / "de" / "2026-11-03" / "index.html", ROOT / "ja" / "index.html", ROOT / "ja" / "archive" / "index.html",
                 ROOT / "en" / "review" / "2026-11-01" / "index.html"]
        for f in pages:
            p = f.read_text(encoding="utf-8")
            self.assertEqual(p.count('<header class="gnb">'), 1, f)
            self.assertIn(gnb.css_block(), p, f)
            self.assertIn(gnb.SCRIPT, p, f)
            self.assertNotIn('<nav aria-label="사이트 메뉴">', p, f)

    def test_latest_json_has_review(self):
        import json
        d = json.loads((ROOT / "latest.json").read_text(encoding="utf-8"))
        for code, x in d["langs"].items():
            if (ROOT / code / "review").exists():
                self.assertTrue(x["review"]["desc"].endswith("개를 다시 봐요"))

    def test_landing_uses_same_css(self):
        css = (ROOT / "landing" / "src" / "app" / "gnb.css").read_text(encoding="utf-8")
        self.assertTrue(css.endswith(gnb.CSS))
        self.assertIn('import "./gnb.css";', (ROOT / "landing" / "src" / "app" / "layout.tsx").read_text(encoding="utf-8"))
        self.assertIn('class="gnb-sheet"', (ROOT / "index.html").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
