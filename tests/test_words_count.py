"""주요 단어 10~12개 기준(2026-11-16 매일 지문부터). 비축분과 그 전 지문은 5~7개 그대로 통과해야 한다."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
import check_content  # noqa: E402


def doc(n, marked=None):
    """주요 단어 n개, 본문 형광펜 marked개(기본 n)인 6문장 지문."""
    marked = n if marked is None else marked
    words = [[f"word{i}", f"뜻{i}"] for i in range(n)]
    hl = [f"**word{i}**" for i in range(marked)]
    sents = [{"en": "Plain sentence " + " ".join(hl[k::6]) + "."} for k in range(6)]
    return {"words": words, "sentences": sents}


def run(n, day="2026-11-16", lang="en", where="content", marked=None, **extra):
    c = dict(doc(n, marked), **extra)
    return check_content.check_word_count(c, ROOT / where / lang / f"{day}.json")


class TestWordCount(unittest.TestCase):
    def test_before_effective_seven_ok(self):
        self.assertEqual(run(7, day="2026-11-15"), [])

    def test_after_effective_seven_error(self):
        for lang in ("en", "ja", "de"):
            errors = run(7, lang=lang)
            self.assertEqual(len(errors), 1, (lang, errors))
            self.assertIn("7개", errors[0])

    def test_after_effective_ten_to_twelve_ok(self):
        for n in (10, 11, 12):
            self.assertEqual(run(n), [], n)
        self.assertEqual(run(10, day="2027-01-03", lang="de"), [])

    def test_after_effective_nine_and_thirteen_error(self):
        self.assertTrue(run(9))
        self.assertTrue(run(13))

    def test_pool_six_ok(self):
        self.assertEqual(run(6, day="de-011", where="pool", lang="de"), [])
        self.assertEqual(run(6, day="2026-11-20", where="pool"), [])

    def test_swapped_pool_day_ok(self):
        self.assertEqual(run(6, from_pool="003-octopus.json"), [])

    def test_marked_count_must_match(self):
        errors = run(10, marked=9)
        self.assertEqual(len(errors), 1)
        self.assertIn("형광펜", errors[0])
        self.assertEqual(run(7, day="2026-11-15", marked=8), [])  # 그 전 지문은 보지 않는다

    def test_wired_into_check(self):
        """check() 가 실제로 이 검사를 부른다(함수만 있고 연결이 빠지는 실수 방지)."""
        tmp = Path(tempfile.mkdtemp())
        try:
            p = tmp / "content" / "en" / "2026-11-16.json"
            p.parent.mkdir(parents=True)
            p.write_text(json.dumps(dict(doc(7), topic="t")), encoding="utf-8")
            errors, _ = check_content.check(p)
            self.assertTrue(any("주요 단어가 7개" in e for e in errors), errors)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestRenderLimit(unittest.TestCase):
    def setUp(self):
        import render
        self.render = render
        self.tmp = Path(tempfile.mkdtemp())
        self.orig = render.ROOT
        render.ROOT = self.tmp
        (self.tmp / "content" / "en").mkdir(parents=True)

    def tearDown(self):
        self.render.ROOT = self.orig
        shutil.rmtree(self.tmp, ignore_errors=True)

    def load(self, n):
        c = {"date": "2026-11-16", "category": "science", "topic": "t",
             "sentences": [{"en": "s."}] * 6, "answers": ["a"] * 6,
             "words": [[f"w{i}", "뜻"] for i in range(n)],
             "points": [{"title": "p", "body": "b"}], "advanced": [{}] * 6}
        (self.tmp / "content" / "en" / "2026-11-16.json").write_text(json.dumps(c), encoding="utf-8")
        return self.render.load("en", "2026-11-16")

    def test_render_accepts_5_to_12(self):
        for n in (5, 6, 7, 10, 12):
            self.assertEqual(len(self.load(n)["words"]), n)

    def test_render_rejects_4_and_13(self):
        for n in (4, 13):
            with self.assertRaises(SystemExit):
                self.load(n)


class TestFallbackMarksPool(unittest.TestCase):
    """2026-11-16 이후 날에 5~7개 비축분으로 바꿔도 검사에 막히지 않고 발행된다."""

    def test_pool_swap_after_effective(self):
        import fallback as fb
        tmp = Path(tempfile.mkdtemp())
        orig = fb.ROOT, fb.CONTENT_DIR, fb.POOL_DIR
        try:
            fb.ROOT, fb.CONTENT_DIR, fb.POOL_DIR = tmp, tmp / "content", tmp / "pool"
            (tmp / "content" / "en").mkdir(parents=True)
            (tmp / "pool" / "en").mkdir(parents=True)
            src = sorted((ROOT / "pool" / "en").glob("*.json"))[0]  # 실제 비축분(5~7개)
            pool_words = len(json.loads(src.read_text(encoding="utf-8"))["words"])
            self.assertLessEqual(pool_words, 7)
            shutil.copy(src, tmp / "pool" / "en" / "001-a.json")
            with patch("subprocess.run", return_value=MagicMock(returncode=0)):
                result = fb.process_lang("en", "2026-11-20", dry_run=False)
            self.assertTrue(result.startswith("USED en 2026-11-20 001-a.json"), result)
            data = json.loads((tmp / "content" / "en" / "2026-11-20.json").read_text(encoding="utf-8"))
            self.assertEqual(data["from_pool"], "001-a.json")
            self.assertEqual(len(data["words"]), pool_words)
            self.assertEqual(check_content.check(tmp / "content" / "en" / "2026-11-20.json")[0], [])
        finally:
            fb.ROOT, fb.CONTENT_DIR, fb.POOL_DIR = orig
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
