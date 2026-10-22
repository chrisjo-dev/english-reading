"""단어 발음 버튼, example_ko, plain_word_tts 단위 테스트.

실행: python3 -m pytest -q tests/test_word_audio.py
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
import audio as audio_mod  # noqa: E402
import check_content as cc  # noqa: E402
import render  # noqa: E402


# ── 공통 픽스처 ────────────────────────────────────────────────────────────────

def make_doc(lang="en", words=None, advanced=None, source=None):
    words = words or [["delivery", "배송"], ["warehouse", "창고"],
                      ["weighs", "무게가 ~이다"], ["supporters", "지지자들"],
                      ["compared", "비교했다"]]
    advanced = advanced or [
        {"word": "convenience", "meaning": "편리함", "confuse": None,
         "example": "Drones offer great **convenience**."}
    ] * 6
    return {
        "date": "2026-10-22",
        "category": "future",
        "topic": "드론",
        "title_ko": "드론 배달",
        "headline": "Drone Delivery" if lang == "en" else "ドローン配達",
        "chips": ["5문장"],
        "sentences": [{"en": "Drones fly.", "b2": False}] * 5,
        "words": words,
        "points": [{"title": "포인트", "body": "설명"}],
        "answers": ["드론이 난다."] * 5,
        "advanced": advanced,
        "source": source,
    }


def write_doc(root, lang, day, c):
    p = root / "content" / lang
    p.mkdir(parents=True, exist_ok=True)
    f = p / f"{day}.json"
    f.write_text(json.dumps(c, ensure_ascii=False))
    return f


# ── plain_word_tts 테스트 ──────────────────────────────────────────────────────

class TestPlainWordTts(unittest.TestCase):

    def test_en_strips_bold(self):
        self.assertEqual(audio_mod.plain_word_tts("**delivery**", "en"), "delivery")

    def test_en_strips_parenthetical(self):
        self.assertEqual(audio_mod.plain_word_tts("deliveries (delivery의 복수)", "en"), "deliveries")

    def test_en_furigana_keeps_kanji(self):
        # 영어에 후리가나가 붙어도 한자를 남긴다
        self.assertEqual(audio_mod.plain_word_tts("{漢字|かんじ}", "en"), "漢字")

    def test_ja_furigana_uses_kana(self):
        self.assertEqual(audio_mod.plain_word_tts("{文化祭|ぶんかさい}", "ja"), "ぶんかさい")

    def test_ja_mixed_furigana(self):
        self.assertEqual(audio_mod.plain_word_tts("11{月|がつ}3{日|か}", "ja"), "11がつ3か")

    def test_ja_strip_parenthetical(self):
        self.assertEqual(audio_mod.plain_word_tts("メニュー (menu)", "ja"), "メニュー")

    def test_ja_plain_katakana(self):
        self.assertEqual(audio_mod.plain_word_tts("メニュー", "ja"), "メニュー")

    def test_render_plain_word_tts_en(self):
        # render 모듈 버전도 동일하게 동작해야 한다
        self.assertEqual(render.plain_word_tts("**delivery**", "en"), "delivery")
        self.assertEqual(render.plain_word_tts("deliveries (delivery의 복수)", "en"), "deliveries")

    def test_render_plain_word_tts_ja(self):
        self.assertEqual(render.plain_word_tts("{文化祭|ぶんかさい}", "ja"), "ぶんかさい")
        self.assertEqual(render.plain_word_tts("{話|はな}し{合|あ}う", "ja"), "はなしあう")


# ── 렌더링: 발음 버튼 ───────────────────────────────────────────────────────────

class TestRenderWordButtons(unittest.TestCase):

    def _render_doc(self, lang, day, c):
        """임시 디렉터리에 content 파일을 쓰고 render() 를 호출한다."""
        import importlib, os
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "content" / lang).mkdir(parents=True)
            (root / "content" / lang / f"{day}.json").write_text(
                json.dumps(c, ensure_ascii=False))
            # render 는 ROOT 를 절대경로로 계산하므로 monkeypatch
            orig = render.ROOT
            orig_tmpl = render.TEMPLATE
            render.ROOT = root
            render.TEMPLATE = orig_tmpl
            try:
                out, _, _ = render.render(lang, day)
                html = out.read_text(encoding="utf-8")
            finally:
                render.ROOT = orig
        return html

    def test_words_have_wbtn(self):
        c = make_doc()
        html = self._render_doc("en", "2026-10-22", c)
        self.assertIn('class="wbtn"', html)
        self.assertIn('data-kind="w"', html)
        self.assertIn('발음 듣기', html)

    def test_advanced_have_vbtn(self):
        c = make_doc()
        html = self._render_doc("en", "2026-10-22", c)
        self.assertIn('data-kind="v"', html)

    def test_example_ko_rendered(self):
        adv = [{"word": "convenience", "meaning": "편리함", "confuse": None,
                "example": "Drones offer great **convenience**.",
                "example_ko": "드론은 큰 편리함을 제공한다."}] * 6
        c = make_doc(advanced=adv, source={"title": "T", "url": "https://example.com"})
        html = self._render_doc("en", "2026-10-22", c)
        self.assertIn('class="ex-ko"', html)
        self.assertIn("드론은 큰 편리함을 제공한다.", html)

    def test_no_example_ko_no_div(self):
        c = make_doc(source={"title": "T", "url": "https://example.com"})
        html = self._render_doc("en", "2026-10-22", c)
        self.assertNotIn('class="ex-ko"', html)

    def test_word_audio_empty_when_no_files(self):
        """음성 파일이 없으면 WORD_AUDIO = [] 로 렌더된다."""
        c = make_doc(source={"title": "T", "url": "https://example.com"})
        html = self._render_doc("en", "2026-10-22", c)
        self.assertIn("var WORD_AUDIO = [];", html)
        self.assertIn("var ADV_AUDIO = [];", html)

    def test_japanese_words_have_kana_data_word(self):
        ja_words = [["{文化祭|ぶんかさい}", "학교 축제"],
                    ["{話|はなし}", "이야기"],
                    ["{賛成|さんせい}", "찬성"],
                    ["11{月|がつ}3{日|か}", "11월 3일"],
                    ["メニュー", "메뉴"]]
        c = make_doc(lang="ja", words=ja_words)
        html = self._render_doc("ja", "2026-10-22", c)
        self.assertIn('data-word="ぶんかさい"', html)
        self.assertIn('data-word="はなし"', html)
        self.assertIn('data-word="メニュー"', html)


# ── check_content: example_ko 검증 ────────────────────────────────────────────

class TestCheckExampleKo(unittest.TestCase):

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())

    def check(self, lang, day, c):
        p = write_doc(self.root, lang, day, c)
        return cc.check(p)[0]

    def eko_errors(self, errs):
        return [e for e in errs if "example_ko" in e]

    def test_valid_example_ko_passes(self):
        adv = [{"word": "convenience", "meaning": "편리함", "confuse": None,
                "example": "Drones offer great **convenience**.",
                "example_ko": "드론은 큰 편리함을 제공한다."}] * 6
        c = make_doc(advanced=adv, source={"title": "T", "url": "https://example.com"})
        self.assertEqual(self.eko_errors(self.check("en", "2026-10-22", c)), [])

    def test_empty_example_ko_is_error(self):
        adv = [{"word": "convenience", "meaning": "편리함", "confuse": None,
                "example": "Drones offer great **convenience**.",
                "example_ko": ""}] * 6
        c = make_doc(advanced=adv, source={"title": "T", "url": "https://example.com"})
        errs = self.eko_errors(self.check("en", "2026-10-22", c))
        self.assertTrue(errs)
        self.assertIn("비어 있어요", errs[0])

    def test_middle_dot_in_example_ko_is_error(self):
        adv = [{"word": "convenience", "meaning": "편리함", "confuse": None,
                "example": "Drones offer great **convenience**.",
                "example_ko": "드론은 편리함·효율성을 제공한다."}] * 6
        c = make_doc(advanced=adv, source={"title": "T", "url": "https://example.com"})
        errs = self.eko_errors(self.check("en", "2026-10-22", c))
        self.assertTrue(errs)
        self.assertIn("가운뎃점", errs[0])

    def test_markdown_in_example_ko_is_error(self):
        adv = [{"word": "convenience", "meaning": "편리함", "confuse": None,
                "example": "Drones offer great **convenience**.",
                "example_ko": "*드론은* 편리하다."}] * 6
        c = make_doc(advanced=adv, source={"title": "T", "url": "https://example.com"})
        errs = self.eko_errors(self.check("en", "2026-10-22", c))
        self.assertTrue(errs)

    def test_missing_example_ko_before_cutoff_is_ok(self):
        c = make_doc(source={"title": "T", "url": "https://example.com"})
        # EXAMPLE_KO_FROM = 2099-01-01 이므로 현재 날짜는 훨씬 전
        self.assertEqual(self.eko_errors(self.check("en", "2026-10-22", c)), [])

    def test_example_ko_required_after_cutoff(self):
        # EXAMPLE_KO_FROM 이후 날짜로 파일을 만들어 검사
        import datetime as dtm
        import check_content as cc2
        orig = cc2.EXAMPLE_KO_FROM
        cc2.EXAMPLE_KO_FROM = dtm.date(2026, 10, 22)  # 현재 날짜로 낮춤
        try:
            c = make_doc(source={"title": "T", "url": "https://example.com"})
            errs = self.eko_errors(self.check("en", "2026-10-22", c))
            self.assertTrue(errs, "EXAMPLE_KO_FROM 이후 지문에 example_ko 없으면 오류여야 함")
        finally:
            cc2.EXAMPLE_KO_FROM = orig


if __name__ == "__main__":
    unittest.main()
