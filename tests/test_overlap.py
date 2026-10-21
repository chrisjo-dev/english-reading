"""tools/check_content.overlap 단위 테스트: 주제는 같아도 되고, 최근 14일 안에 같은 이야기를 반복하면 오류.

실행: python -m pytest -q tests/test_overlap.py
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
import check_content as cc  # noqa: E402

REPAIR_A = ["Every month a small hall turns into a repair cafe where volunteers fix broken lamps and toasters for free.",
            "Retired engineers help people reduce waste instead of throwing things away."]
REPAIR_B = ["On Saturday people carried broken lamps and noisy fans into a repair cafe.",
            "Volunteers fixed them for free, hoping to reduce waste in the city."]
REPAIR_NEW = ["Ten years after the first event, the city has opened a permanent workshop with paid staff.",
              "Officials now plan a law that forces companies to sell spare parts for seven years."]
OTHER = ["Scientists found that octopus brains grew by folding their genetic code in new ways.",
         "The study suggests that loops in long molecules decide which genes turn on."]


def doc(topic, sents, words, url=None):
    return {"topic": topic, "sentences": [{"en": s} for s in sents], "words": [[w, "뜻"] for w in words],
            "source": {"title": "t", "url": url} if url else None}


class OverlapTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp()) / "content" / "en"
        self.dir.mkdir(parents=True)
        self.write("2026-10-17", doc("수리 카페", REPAIR_A, ["repair", "volunteers", "reduce"], "https://a.example/1"))

    def write(self, day, c):
        p = self.dir / f"{day}.json"
        p.write_text(json.dumps(c, ensure_ascii=False))
        return p

    def check(self, day, c):
        return cc.overlap(self.write(day, c), c)

    def test_same_article_is_error(self):
        errs = self.check("2026-10-21", doc("다른 주제", OTHER, ["octopus"], "https://a.example/1"))
        self.assertTrue(errs and "같은 기사" in errs[0], errs)

    def test_shared_keywords_is_error(self):
        errs = self.check("2026-10-21", doc("수리 카페", REPAIR_B, ["volunteers", "reduce", "lamps"]))
        self.assertTrue(errs and "형광펜" in errs[0], errs)

    def test_repeated_explanation_is_error(self):
        errs = self.check("2026-10-21", doc("고장 난 물건", REPAIR_B, ["carried"]))
        self.assertTrue(errs and "겹쳐요" in errs[0], errs)

    def test_same_topic_new_development_is_ok(self):
        self.assertEqual(self.check("2026-10-21", doc("수리 카페", REPAIR_NEW, ["permanent", "spare"])), [])

    def test_different_story_is_ok(self):
        self.assertEqual(self.check("2026-10-21", doc("문어의 뇌", OTHER, ["octopus", "loops"])), [])

    def test_older_than_window_is_ok(self):
        errs = self.check("2026-11-05", doc("수리 카페", REPAIR_B, ["volunteers", "reduce"]))
        self.assertEqual(errs, [])

    def test_pool_files_are_not_compared(self):
        pool = Path(tempfile.mkdtemp()) / "pool" / "en"
        pool.mkdir(parents=True)
        p = pool / "2026-10-21.json"
        c = doc("수리 카페", REPAIR_B, ["volunteers", "reduce"])
        p.write_text(json.dumps(c, ensure_ascii=False))
        self.assertEqual(cc.overlap(p, c), [])


if __name__ == "__main__":
    unittest.main()
