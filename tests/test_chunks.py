"""끊어 읽기(chunks) 검사 단위 테스트: check_content 의 chunks 규칙과 render 의 끊어 읽기 줄.

실행: python -m pytest -q tests/test_chunks.py
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
import check_content as cc  # noqa: E402
import render  # noqa: E402

EN = "Imagine ordering a phone **charger** today."
GOOD = [["Imagine", "상상해 보세요"], ["ordering a phone **charger**", "휴대폰 충전기를 주문하는 것을"], ["today.", "오늘"]]


def doc(sentence, chunks=None):
    s = {"en": sentence, "b2": False}
    if chunks is not None:
        s["chunks"] = chunks
    return {"topic": "t", "title_ko": "제목", "headline": "Head", "sentences": [s], "words": [], "source": None}


class CheckChunksTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())

    def check(self, lang, day, c, kind="content"):
        d = self.root / kind / lang
        d.mkdir(parents=True, exist_ok=True)
        p = d / f"{day}.json"
        p.write_text(json.dumps(c, ensure_ascii=False))
        return cc.check(p)[0]

    def chunk_errors(self, errs):
        return [e for e in errs if "chunks" in e]

    def test_valid_chunks_pass(self):
        self.assertEqual(self.chunk_errors(self.check("en", "2026-10-23", doc(EN, GOOD))), [])

    def test_join_mismatch_is_error(self):
        bad = [["Imagine", "상상해 보세요"], ["ordering a phone charger", "충전기를 주문하는 것을"], ["today.", "오늘"]]  # ** 빠짐
        errs = self.chunk_errors(self.check("en", "2026-10-20", doc(EN, bad)))
        self.assertEqual(len(errs), 1)
        self.assertIn("문장과 달라요", errs[0])

    def test_empty_meaning_is_error(self):
        bad = [["Imagine", ""], ["ordering a phone **charger** today.", "충전기를 오늘 주문하는 것을"]]
        self.assertTrue(self.chunk_errors(self.check("en", "2026-10-20", doc(EN, bad))))

    def test_split_bold_marker_is_error(self):
        bad = [["Imagine ordering a phone **charger", "휴대폰 충전기를 주문하는 것을"], ["** today.", "오늘"]]
        self.assertTrue(self.chunk_errors(self.check("en", "2026-10-20", doc(EN, bad))))

    def test_missing_chunks_on_new_date_is_error(self):
        errs = self.chunk_errors(self.check("en", "2026-10-23", doc(EN)))
        self.assertEqual(len(errs), 1)
        self.assertIn("chunks 가 없어요", errs[0])

    def test_missing_chunks_before_cutoff_is_ok(self):
        self.assertEqual(self.chunk_errors(self.check("en", "2026-10-22", doc(EN))), [])

    def test_missing_chunks_in_english_pool_is_error(self):
        self.assertTrue(self.chunk_errors(self.check("en", "015-test", doc(EN), kind="pool")))

    def test_japanese_does_not_need_chunks(self):
        self.assertEqual(self.chunk_errors(self.check("ja", "2026-10-23", doc("今日は{雨|あめ}です。"))), [])
        self.assertEqual(self.chunk_errors(self.check("ja", "015-test", doc("今日は{雨|あめ}です。"), kind="pool")), [])


class RenderChunksTest(unittest.TestCase):
    def test_valid_rows_keep_bold_and_escape(self):
        rows = render.chunk_rows("en", "d", [{"en": EN, "chunks": GOOD[:2] + [["today.", "오늘 <곧>"]]}])
        self.assertEqual(len(rows), 1)
        self.assertIn("<b>charger</b>", rows[0])
        self.assertIn("오늘 &lt;곧&gt;", rows[0])
        self.assertEqual(rows[0].count('class="s"'), 2)  # 마지막 덩어리 뒤에는 / 가 없다

    def test_any_mismatch_drops_whole_page(self):
        sents = [{"en": EN, "chunks": GOOD}, {"en": "Second one.", "chunks": [["Second", "두 번째"], ["one", "것"]]}]
        self.assertIsNone(render.chunk_rows("en", "d", sents))

    def test_missing_or_japanese_has_no_rows(self):
        self.assertIsNone(render.chunk_rows("en", "d", [{"en": EN, "chunks": GOOD}, {"en": "No chunks."}]))
        self.assertIsNone(render.chunk_rows("ja", "d", [{"en": EN, "chunks": GOOD}]))


if __name__ == "__main__":
    unittest.main()
