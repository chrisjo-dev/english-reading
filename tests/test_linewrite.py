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


class Notes(unittest.TestCase):
    MINE = (ROOT / "assets" / "mine.js").read_text(encoding="utf-8")

    def test_prompts_match_langs(self):
        import langs
        for code in ("en", "ja", "de"):
            L = langs.LANGS[code]
            self.assertIn(f"'{L['copy_head'].split('입니다.')[0]}입니다.', '{L['copy_weak']}'", self.MINE, code)

    def test_mine_before_linewrite(self):
        p = linewrite.apply(OLD)
        self.assertEqual(p.count('id="mine-js"'), 1)
        self.assertLess(p.index('id="mine-js"'), p.index('id="linewrite-js"'))

    def test_notes_page_and_card(self):
        notes = (ROOT / "me/notes/index.html").read_text(encoding="utf-8")
        for need in ('id="mn"', "/assets/mine.js", "/assets/notes.js", 'content="noindex"', ".lw-sheet {", ".mn-card {"):
            self.assertIn(need, notes)
        me = (ROOT / "me/index.html").read_text(encoding="utf-8")
        self.assertEqual(me.count("data-mine-card"), 1)
        self.assertIn("/assets/mine.js", me)
        self.assertNotIn("mine.js", (ROOT / "join/index.html").read_text(encoding="utf-8"))

    def test_weekly_card(self):
        for lang in ("en", "ja", "de"):
            for f in sorted((ROOT / lang / "review").glob("*/index.html")):
                p = f.read_text(encoding="utf-8")
                self.assertEqual(p.count("data-mine-card"), 1, f)
                self.assertEqual(linewrite.weekly(p, lang, f.parent.name), p, f)
        self.assertIn('data-from="2026-11-16" data-to="2026-11-22"', (ROOT / "en/review/2026-11-22/index.html").read_text(encoding="utf-8"))
