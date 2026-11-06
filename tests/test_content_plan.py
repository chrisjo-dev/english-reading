"""공통 주간 구조 경고(이슈 #25): 요일 유형, 출처, 문법, 영어 길이, 소재 반복."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import check_content  # noqa: E402

LONG = " ".join(["word"] * 15) + "."


def base(**kw):
    c = {"fit": "news", "source": {"title": "t", "url": "u"}, "grammar": {"b": [], "a": []}, "keywords": ["소재"],
         "topic": "주제어", "title_ko": "제목", "sentences": [{"en": LONG}]}
    c.update(kw)
    return c


class Plan(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def warns(self, lang, day, c, folder="content"):
        d = self.root / folder / lang
        d.mkdir(parents=True, exist_ok=True)
        return check_content.check_plan(c, d / f"{day}.json")

    def seed(self, lang, day, **kw):
        d = self.root / "content" / lang
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{day}.json").write_text(json.dumps(kw, ensure_ascii=False), encoding="utf-8")

    def test_clean_day_has_no_warning(self):
        self.assertEqual(self.warns("en", "2026-11-09", base()), [])

    def test_fit_must_match_weekday(self):
        self.assertTrue(any("fit" in w for w in self.warns("en", "2026-11-10", base())))
        self.assertTrue(any("fit" in w for w in self.warns("en", "2026-11-09", base(fit=None))))
        self.assertEqual(self.warns("en", "2026-11-14", base(fit="life", source=None)), [])

    def test_source_needed_on_news_and_explain_for_every_language(self):
        for lang in ("en", "ja", "de"):
            self.assertTrue(any("출처" in w for w in self.warns(lang, "2026-11-09", base(source=None))))
            self.assertTrue(any("출처" in w for w in self.warns(lang, "2026-11-10", base(fit="explain", source=None))))

    def test_unknown_grammar_id(self):
        w = self.warns("en", "2026-11-09", base(grammar={"b": ["b-nothing"], "a": []}))
        self.assertTrue(any("b-nothing" in x for x in w))

    def test_grammar_pattern_checked_per_sentence(self):
        c = base(grammar={"b": ["b-will"], "a": []})
        self.assertTrue(any("찾지 못했어요" in x for x in self.warns("en", "2026-11-09", c)))
        c["sentences"] = [{"en": LONG}, {"en": LONG.replace("word.", "**will** word.")}]
        self.assertFalse(any("찾지 못했어요" in x for x in self.warns("en", "2026-11-09", c)))

    def test_ja_pattern_ignores_furigana(self):
        c = base(grammar={"b": ["b-yotei"], "a": []}, sentences=[{"en": "{来年|らいねん}{開|ひら}く{予定|よてい}です。"}])
        self.assertFalse(any("찾지 못했어요" in x for x in self.warns("ja", "2026-11-09", c)))

    def test_english_length(self):
        short = base(sentences=[{"en": "Too short here."}])
        self.assertTrue(any("단어예요" in w for w in self.warns("en", "2026-11-09", short)))
        long27 = " ".join(["word"] * 27) + "."
        self.assertTrue(any("단어예요" in w for w in self.warns("en", "2026-11-09", base(sentences=[{"en": long27}]))))
        self.assertFalse(any("단어예요" in w for w in self.warns("en", "2026-11-09", base(sentences=[{"en": long27, "b2": True}]))))
        long31 = " ".join(["word"] * 31) + "."
        self.assertTrue(any("단어예요" in w for w in self.warns("en", "2026-11-09", base(sentences=[{"en": long31, "b2": True}]))))
        self.assertFalse(any("단어예요" in w for w in self.warns("de", "2026-11-09", base(sentences=[{"en": long31}]))))

    def test_not_applied_before_plan_from(self):
        self.assertEqual(self.warns("en", "2026-11-07", {"sentences": [{"en": "Short."}]}), [])

    def test_pool_is_skipped(self):
        self.assertEqual(self.warns("en", "2026-11-10", {"sentences": []}, folder="pool"), [])

    def test_topic_repeat_within_90_days(self):
        self.seed("ja", "2026-10-15", topic="첫 아르바이트", title_ko="카페에서 시작한 첫 아르바이트")
        w = self.warns("ja", "2026-11-09", base(topic="서점 아르바이트", title_ko="서점 아르바이트 첫날"))
        self.assertTrue(any("2026-10-15" in x and "아르바이트" in x for x in w))

    def test_keywords_are_compared_and_old_days_are_not(self):
        self.seed("ja", "2026-10-15", topic="다른 주제", title_ko="다른 제목", keywords=["아르바이트"])
        self.seed("ja", "2026-06-01", topic="옛 주제", title_ko="옛 제목", keywords=["서점"])
        w = self.warns("ja", "2026-11-09", base(keywords=["아르바이트", "서점"]))
        self.assertTrue(any("2026-10-15" in x for x in w))
        self.assertFalse(any("2026-06-01" in x for x in w))

    def test_josa_is_ignored(self):
        self.seed("ja", "2026-10-15", topic="도서관", title_ko="동네 도서관")
        w = self.warns("ja", "2026-11-09", base(title_ko="도서관의 하루"))
        self.assertTrue(any("소재 반복" in x for x in w))

    def test_generic_words_do_not_warn(self):
        self.seed("ja", "2026-10-15", topic="일본 이야기", title_ko="오늘 일본의 가을 이야기")
        self.seed("de", "2026-10-15", topic="독일 소식", title_ko="독일의 새로운 이야기")
        self.assertFalse(any("소재 반복" in x for x in self.warns("ja", "2026-11-09", base(title_ko="일본의 가을 소식"))))
        self.assertFalse(any("소재 반복" in x for x in self.warns("de", "2026-11-09", base(title_ko="독일 이야기"))))


class RealCases(unittest.TestCase):
    def repeat(self, lang, day):
        return subprocess.run([sys.executable, "tools/check_content.py", "--repeat", lang, day], cwd=ROOT, capture_output=True, text=True)

    def test_part_time_job_repeat(self):
        r = self.repeat("ja", "2026-11-05")
        self.assertEqual(r.returncode, 0)
        self.assertIn("2026-10-15", r.stdout)
        self.assertIn("아르바이트", r.stdout)

    def test_robotaxi_repeat(self):
        r = self.repeat("en", "2026-11-05")
        self.assertEqual(r.returncode, 0)
        self.assertIn("2026-10-15", r.stdout)
        self.assertIn("로보택시", r.stdout)

    def test_topics_list(self):
        r = subprocess.run([sys.executable, "tools/check_content.py", "--topics", "ja", "2026-11-05"], cwd=ROOT, capture_output=True, text=True)
        self.assertIn("첫 아르바이트", r.stdout)
        self.assertNotIn("서점 아르바이트", r.stdout)


class Routines(unittest.TestCase):
    def test_routines_read_common_rules_and_new_fields(self):
        for name in ("ROUTINE.md", "ROUTINE.ja.md", "ROUTINE.de.md"):
            r = (ROOT / "tools" / name).read_text(encoding="utf-8")
            for word in ("tools/ROUTINE.common.md", "grammar_pick.py", "--topics", "`fit`", "`grammar`", "`keywords`"):
                self.assertIn(word, r, name)

    def test_personal_weak_points_removed(self):
        r = (ROOT / "tools" / "ROUTINE.md").read_text(encoding="utf-8")
        self.assertNotIn("약점", r)


if __name__ == "__main__":
    unittest.main()
