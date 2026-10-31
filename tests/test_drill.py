"""단어 암기 반복(이슈 #16): 카드 자료와 페이지 삽입."""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import drill  # noqa: E402

PAGE = ROOT / "en" / "2026-10-29" / "index.html"


def data_of(page):
    m = re.search(r'<script type="application/json" id="drill-data">(.*?)</script>', page, re.S)
    return json.loads(m.group(1))


class TestCards(unittest.TestCase):
    def test_en_words_with_example_audio_and_alts(self):
        cs = drill.cards("en", "2026-10-29")
        self.assertEqual([c["w"] for c in cs][:3], ["humanoid", "range from A to B", "wires"])
        insp = cs[3]
        self.assertEqual(insp["m"], "검사, 점검")
        self.assertIn("<b>inspection</b>", insp["ex"])
        self.assertTrue(insp["ek"].startswith("그 로봇들은"))
        self.assertIn("<b>inspection</b>", insp["sh"])
        self.assertEqual(insp["au"], "/en/2026-10-29/audio/w4.mp3")
        self.assertEqual(len(insp["alts"]), len(cs) - 1)
        self.assertNotIn(insp["m"], insp["alts"])

    def test_ja_word_has_reading_and_ruby_example(self):
        cs = drill.cards("ja", "2026-10-29")
        c = next(x for x in cs if x["w"] == "集中する")
        self.assertEqual(c["r"], "しゅうちゅうする")
        self.assertIn("<ruby>集中<rt>しゅうちゅう</rt></ruby>", c["ex"])
        self.assertNotIn("{", c["ex"])

    def test_de_word_found_without_bold(self):
        c = next(x for x in drill.cards("de", "2026-10-29") if x["w"] == "Betrieb")
        self.assertIn("Betrieb", c["ex"])

    def test_every_word_has_an_example(self):
        for f in sorted((ROOT / "content").glob("*/*.json")):
            for c in drill.cards(f.parent.name, f.stem):
                self.assertIn("ex", c, f"{f.parent.name}/{f.stem} {c['w']}")

    def test_example_highlights_the_word_itself_and_cloze_blanks_it(self):
        c = next(x for x in drill.cards("de", "2026-10-30") if x["w"] == "Blatt")
        self.assertEqual(re.findall(r"<b>(.*?)</b>", c["ex"]), ["Blatt"])  # 전에는 Farbstoffe 를 강조했다
        self.assertEqual(c["ca"], "Blatt")
        self.assertEqual(c["cz"].count('<span class="dr-blank"></span>'), 1)
        self.assertNotIn("Blatt", c["cz"].replace("Blätter", ""))

    def test_ja_inflected_verb_cloze_drops_trailing_connective(self):
        cs = {x["w"]: x for x in drill.cards("ja", "2026-10-30")}
        self.assertEqual(cs["含む"]["ca"], "含まれています")
        self.assertEqual(cs["逃げる"]["ca"], "逃げてしまう")
        self.assertEqual(cs["滑る"]["ca"], "滑らない")

    def test_cloze_answer_must_be_a_form_of_the_word(self):
        self.assertTrue(drill._fits("teaming", "team up"))
        self.assertTrue(drill._fits("Farbstoffe", "Farbstoff"))
        self.assertFalse(drill._fits("Bäckerei", "Bäcker"))
        self.assertFalse(drill._fits("紅葉", "葉"))

    def test_every_cloze_has_one_blank_and_an_answer(self):
        for f in sorted((ROOT / "content").glob("*/*.json")):
            for c in drill.cards(f.parent.name, f.stem):
                if "cz" in c:
                    self.assertEqual(c["cz"].count("dr-blank"), 1, f"{f.stem} {c['w']}")
                    self.assertTrue(c["ca"].strip())
                    self.assertNotIn("*", c["cz"])

    def test_no_cloze_when_answer_still_shows_in_sentence(self):
        c = next(x for x in drill.cards("ja", "2026-10-30") if x["w"] == "地面")  # 문장에 地面 이 두 번 나온다
        self.assertNotIn("cz", c)
        self.assertIn("ex", c)

    def test_write_hint_hides_answer_in_parentheses(self):
        """독일어 2026-10-31: 뜻 '물가, 호숫가 (das Ufer)' 가 단어 쓰기 힌트에 답을 보여 줬다."""
        cs = {x["w"]: x for x in drill.cards("de", "2026-10-31")}
        self.assertEqual(cs["Ufer"]["m"], "물가, 호숫가 (das Ufer)")  # 카드 뒷면, 뜻 고르기는 그대로
        self.assertEqual(cs["Ufer"]["mh"], "물가, 호숫가")
        self.assertEqual(cs["Hang"]["mh"], "비탈, 경사면")
        for c in cs.values():
            self.assertNotIn(c["w"].lower(), c.get("mh", c["m"]).lower())
        self.assertEqual(drill._hint("협력하다, 손잡다 (teaming up: 손잡는 중)", "team up"), "협력하다, 손잡다")
        self.assertEqual(drill._hint("마음 (비유)", "heart"), "마음 (비유)")  # 답이 없는 괄호는 둔다

    def test_de_word_found_through_umlaut_form(self):
        c = next(x for x in drill.cards("de", "2026-10-31") if x["w"] == "Hang")  # 문장에는 Hängen
        self.assertIn("<b>Hängen</b>", c["ex"])

    def test_missing_content_gives_no_cards(self):
        self.assertEqual(drill.cards("en", "2020-01-01"), [])


class TestApply(unittest.TestCase):
    def setUp(self):
        if not PAGE.exists():
            self.skipTest("렌더 HTML 없음")
        self.page = PAGE.read_text(encoding="utf-8")

    def test_page_has_one_of_each_part_in_order(self):
        p = self.page
        for s in ('id="dr-due"', 'id="drill"', 'id="drill-data"', '<script id="drill-js"', "/* drill-css */"):
            self.assertEqual(p.count(s), 1, s)
        self.assertLess(p.index('</header>'), p.index('id="dr-due"'))
        self.assertLess(p.index('id="dr-due"'), p.index('<div class="top">'))
        self.assertLess(p.index('id="drill"'), p.index('id="vote"'))
        self.assertIn('<div class="step">STEP 5</div>\n    <h2>오늘 단어 외우기</h2>', p)
        self.assertIn('aria-pressed="true"><b>카드로 외우기</b>', p)
        self.assertIn("7개 외우기 시작", p)
        self.assertEqual(len(data_of(p)), 7)
        self.assertNotIn("\u00b7", p[p.index("/* drill-css */"):])

    def test_apply_is_idempotent_and_replaces_old_version(self):
        self.assertEqual(drill.apply(self.page, "en", "2026-10-29"), self.page)
        old = self.page.replace(f'<script id="drill-js" data-v="{drill.VERSION}"', '<script id="drill-js" data-v="0"')
        again = drill.apply(old, "en", "2026-10-29")
        self.assertEqual(again, self.page)

    def test_page_without_words_gets_banner_only(self):
        bare = self.page.replace(f'<script id="drill-js" data-v="{drill.VERSION}"', '<script id="drill-js" data-v="0"')
        for a, b in (("<!-- drill-due -->", "<!-- /drill-due -->"), ("<!-- drill-card -->", "<!-- /drill-card -->")):
            bare = re.sub(re.escape(a) + r".*?" + re.escape(b) + r"\n\n?", "", bare, flags=re.S)
        out = drill.apply(bare, "en", "2020-01-01")
        self.assertNotIn('id="drill"', out)
        self.assertIn('id="dr-due"', out)
        self.assertEqual(data_of(out), [])

    def test_script_asset_exists(self):
        js = (ROOT / "assets" / "drill.js").read_text(encoding="utf-8")
        self.assertIn("c.mh || c.m", js)  # 단어 쓰기 힌트는 답을 가린 뜻
        self.assertIn("replace(/^(der|die|das) /, '')", js)  # 관사를 붙여 써도 정답
        for name in ("word_drill_start", "word_drill_done", "word_review_start", "drill:v1"):
            self.assertIn(name, js)
        self.assertNotIn("\u00b7", js)
        self.assertNotIn('style="', js)  # CSP style-src 대비: 마크업 style 속성 없이 클래스와 CSSOM만


class TestGuard(unittest.TestCase):
    def test_non_passage_pages_are_left_alone(self):
        arch = ROOT / "en" / "archive" / "index.html"
        if arch.exists():
            page = arch.read_text(encoding="utf-8")
            self.assertEqual(drill.apply(page, "en", "archive"), page)
        bare = "<html><head><style>\n  .gnb { }\n</style></head><body><header></header>\n<main></main></body></html>"
        self.assertEqual(drill.apply(bare, "en", "review"), bare)
        self.assertEqual(drill.apply(bare, "en", "2026-10-2"), bare)
        no_anchor = "<html><body><main></main></body></html>"
        self.assertEqual(drill.apply(no_anchor, "en", "2026-10-29"), no_anchor)
        self.assertNotEqual(drill.apply(bare, "en", "2026-10-29"), bare)


if __name__ == "__main__":
    unittest.main()