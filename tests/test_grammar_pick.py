"""문법 후보 순서: 기록 없는 항목, 오래된 항목, 목록 순서. 후보가 없어도 멈추지 않는다."""
import datetime as dt
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import grammar_pick  # noqa: E402

MONDAY = dt.date(2026, 11, 9)


def item(n, fit=("news",)):
    return {"id": f"b-{n}", "name": n, "example": n, "fit": list(fit), "pattern": None}


class TestCandidates(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "tools/grammar").mkdir(parents=True)
        (self.root / "content/en").mkdir(parents=True)
        items = [item(n) for n in "abcdefg"] + [item("life", ("life",))]
        (self.root / "tools/grammar/en.json").write_text(json.dumps({"a": [], "b": items}), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def used(self, day, ids):
        (self.root / f"content/en/{day}.json").write_text(json.dumps({"grammar": {"b": ids, "a": []}}), encoding="utf-8")

    def ids(self, day=MONDAY, skip=0, level="b"):
        return [i["id"] for i in grammar_pick.candidates("en", level, day, skip, self.root)]

    def test_starts_in_list_order(self):
        self.assertEqual(self.ids(), ["b-a", "b-b", "b-c"])

    def test_unused_first_then_oldest(self):
        self.used("2026-11-02", ["b-a"])
        self.used("2026-11-04", ["b-b"])
        self.assertEqual(self.ids(), ["b-c", "b-d", "b-e"])
        self.assertEqual(self.ids(skip=1), ["b-f", "b-g", "b-a"])
        self.assertEqual(self.ids(skip=2), ["b-b"])

    def test_rotation_after_all_used(self):
        for n, x in enumerate("gfedcba"):
            self.used(f"2026-11-0{n + 1}", [f"b-{x}"])
        self.assertEqual(self.ids(), ["b-g", "b-f", "b-e"])

    def test_future_and_same_day_ignored(self):
        self.used("2026-11-09", ["b-a"])
        self.used("2026-11-10", ["b-b"])
        self.assertEqual(self.ids(), ["b-a", "b-b", "b-c"])

    def test_filters_by_weekday_fit(self):
        self.assertEqual(self.ids(dt.date(2026, 11, 14)), ["b-life"])

    def test_no_candidates(self):
        self.assertEqual(self.ids(level="a"), [])
        self.assertEqual(self.ids(skip=9), [])


class TestCli(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, "tools/grammar_pick.py", *args], cwd=ROOT, capture_output=True, text=True)

    def test_prints_three_candidates(self):
        r = self.run_cli("en", "b", "--day", "2026-11-09")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.splitlines()[0], "fit=news")
        self.assertEqual(len(r.stdout.splitlines()), 4)

    def test_no_candidates_exits_zero(self):
        for args in (("en", "b", "--day", "2026-11-09", "--skip", "99"), ("xx", "b", "--day", "2026-11-09")):
            r = self.run_cli(*args)
            self.assertEqual(r.returncode, 0)
            self.assertIn("후보 없음", r.stdout)


class TestLists(unittest.TestCase):
    def test_upper_range_items_are_last(self):
        self.assertEqual(grammar_pick.load("en")["b"][-1]["id"], "b-third-conditional")
        self.assertEqual(grammar_pick.load("de")["b"][-1]["id"], "b-konjunktiv-i")

    def test_every_level_has_every_fit(self):
        for lang in ("en", "ja", "de"):
            for level, items in grammar_pick.load(lang).items():
                for fit in ("news", "explain", "life"):
                    self.assertGreaterEqual(sum(fit in i["fit"] for i in items), 3, (lang, level, fit))


if __name__ == "__main__":
    unittest.main()
