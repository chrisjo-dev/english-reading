import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import linewrite  # noqa: E402

OLD = (ROOT / "tools" / "template.html").read_text(encoding="utf-8").replace(
    "{{tools_extra}}{{sentences}}", "".join(f'    <div class="sent"><button class="no">{i}</button><div class="say"><div class="en">x</div></div></div>\n' for i in (1, 2)))


class Apply(unittest.TestCase):
    def test_old_block_is_replaced(self):
        p = linewrite.apply(OLD)
        for gone in ('id="mine"', "copymine", "copyMine", "'#mine'", "내 해석' 칸", ".mine {"):
            self.assertNotIn(gone, p)
        self.assertEqual(p.count("<!-- lw -->"), 2)
        for one in ('id="lw-sw"', 'id="lw-dock"', 'id="linewrite-js"', "/* linewrite-css */"):
            self.assertEqual(p.count(one), 1, one)
        self.assertIn("['#lw-ask'", p)

    def test_idempotent(self):
        once = linewrite.apply(OLD)
        self.assertEqual(linewrite.apply(once), once)

    def test_other_pages_untouched(self):
        self.assertEqual(linewrite.apply("<body>x</body>"), "<body>x</body>")

    def test_every_day_page(self):
        for lang in ("en", "ja", "de"):
            for f in sorted((ROOT / lang).glob("20??-??-??/index.html")):
                p = f.read_text(encoding="utf-8")
                self.assertGreater(p.count("<!-- lw -->"), 0, f)
                self.assertEqual(p.count("<!-- lw -->"), p.count('<div class="sent">'), f)
                self.assertEqual(p.count('id="linewrite-js"'), 1, f)
                self.assertNotIn("copyMine", p, f)


class Cloze(unittest.TestCase):
    def test_blank_itself_is_the_input(self):
        js = (ROOT / "assets" / "drill.js").read_text(encoding="utf-8")
        self.assertIn("dr-inb", js)
        self.assertNotIn('placeholder="빈칸에', js)
