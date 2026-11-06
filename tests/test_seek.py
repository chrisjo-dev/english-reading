import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import seek  # noqa: E402


def old_page():
    """seek 가 들어가기 전 모양의 페이지. 템플릿이 바뀌어 고리가 끊기면 여기서 드러난다."""
    return (ROOT / "tools" / "template.html").read_text(encoding="utf-8")


class Apply(unittest.TestCase):
    def test_all_hooks_exist_in_template(self):
        page = old_page()
        for old, _ in seek.HOOKS:
            self.assertEqual(page.count(old), 1, old)
        self.assertEqual(page.count(seek._OLD_MARKUP), 1)
        self.assertEqual(len(seek._OLD_CSS.findall(page)), 1)
        self.assertEqual(len(seek._OLD_JS.findall(page)), 1)

    def test_apply_replaces_old_bar(self):
        page = seek.apply(old_page())
        self.assertNotIn('<div class="prog">', page)
        self.assertNotIn(".pbar .prog", page)
        self.assertNotIn("pbarProg.style.width = '0%'", page)
        self.assertNotIn("Math.max(3, pct)", page)
        self.assertEqual(page.count('role="slider"'), 1)
        self.assertEqual(page.count("// seek-js\n"), 1)
        self.assertEqual(page.count("/* seek-css */"), 1)
        for _, new in seek.HOOKS:
            self.assertEqual(page.count(new), 1, new)

    def test_apply_is_idempotent(self):
        once = seek.apply(old_page())
        self.assertEqual(seek.apply(once), once)

    def test_new_version_replaces_block(self):
        once = seek.apply(old_page())
        old_body = once.replace(seek.JS, seek.JS.replace("var _seekI = 0", "var _seekI = 1")).replace(seek.CSS, seek.CSS.replace("18px", "19px"))
        self.assertNotEqual(old_body, once)
        self.assertEqual(seek.apply(old_body), once)

    def test_page_without_player_is_untouched(self):
        self.assertEqual(seek.apply("<html><body>x</body></html>"), "<html><body>x</body></html>")

    def test_touch_area_and_drag_rules(self):
        self.assertIn("touch-action: none", seek.CSS)
        self.assertIn("top: -13px; bottom: -13px", seek.CSS)  # 18px 트랙 칸과 합쳐 44px
        self.assertIn(".drag .seek-track i, .pbar .seek.drag .seek-knob { transition: none; }", seek.CSS)


class Pages(unittest.TestCase):
    def test_every_day_page_has_seek_once(self):
        for lang in ("en", "ja", "de"):
            for f in sorted((ROOT / lang).glob("20??-??-??/index.html")):
                page = f.read_text(encoding="utf-8")
                self.assertEqual(page.count('id="pbar-seek"'), 1, f)
                self.assertEqual(page.count("// seek-js\n"), 1, f)


if __name__ == "__main__":
    unittest.main()
