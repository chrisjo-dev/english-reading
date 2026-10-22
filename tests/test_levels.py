"""levels.a 스키마 검증, build_email 회귀, send_email 로직 단위 테스트.

실행: python3 -m pytest -q tests/test_levels.py
"""
import datetime
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
import check_content as cc  # noqa: E402
import build_email  # noqa: E402
import send_email  # noqa: E402
import langs  # noqa: E402


# ── 공통 픽스처 ────────────────────────────────────────────────────────────────

MAIN_SENTENCE = "The drone can now bring **packages** to your door."
MAIN_CHUNKS = [["The drone can now", "드론은 이제 할 수 있다"], ["bring **packages**", "소포를 가져다주다"], ["to your door.", "당신의 문 앞까지"]]

A_SENTENCE = "Drones bring packages to your door."
A_CHUNKS = [["Drones bring packages", "드론이 소포를 가져다준다"], ["to your door.", "당신의 문 앞까지"]]


def make_content(n_sentences=1, with_levels=True, a_sentence=A_SENTENCE, a_chunks=None,
                 n_a_sentences=None, n_a_answers=None, bad_en=None):
    """테스트용 콘텐츠 딕셔너리를 만든다."""
    sentences = [{"en": MAIN_SENTENCE, "b2": False, "chunks": MAIN_CHUNKS}] * n_sentences
    answers = ["모범 해석."] * n_sentences
    c = {
        "date": "2026-11-01",
        "category": "science",
        "topic": "드론",
        "title_ko": "드론 배달",
        "headline": "Drone Delivery",
        "chips": ["5문장"],
        "sentences": sentences,
        "words": [["packages", "소포"]] * 5,
        "points": [{"title": "포인트", "body": "포인트 설명"}],
        "answers": answers,
        "advanced": [{"word": "efficient", "meaning": "효율적인", "confuse": None, "example": "Drones are **efficient**."}] * 6,
        "source": {"title": "Test (TestSite, 2026-10-01)", "url": "https://example.com"},
    }
    if with_levels:
        n_a = n_a_sentences if n_a_sentences is not None else n_sentences
        n_ans = n_a_answers if n_a_answers is not None else n_a
        a_sents = [{"en": bad_en or a_sentence, "chunks": a_chunks or A_CHUNKS}] * n_a
        c["levels"] = {"a": {"sentences": a_sents, "answers": ["기초 해석."] * n_ans}}
    return c


def write_content(root, lang, day, c):
    p = root / "content" / lang
    p.mkdir(parents=True, exist_ok=True)
    f = p / f"{day}.json"
    f.write_text(json.dumps(c, ensure_ascii=False))
    return f


# ── check_content: levels.a 스키마 검증 ───────────────────────────────────────

class TestCheckLevelsA(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())

    def check(self, day, c):
        p = write_content(self.root, "en", day, c)
        return cc.check(p)[0]

    def level_errors(self, errs):
        return [e for e in errs if "levels.a" in e or "levels" in e.lower()]

    def test_valid_levels_a_pass(self):
        errs = self.check("2026-11-01", make_content())
        self.assertEqual(self.level_errors(errs), [], errs)

    def test_no_levels_before_cutoff_is_ok(self):
        """LEVELS_FROM(2099-01-01) 이전이면 levels 없어도 오류 없음."""
        errs = self.check("2026-11-01", make_content(with_levels=False))
        self.assertEqual(self.level_errors(errs), [])

    def test_sentence_count_mismatch_is_error(self):
        c = make_content(n_sentences=2, n_a_sentences=1)
        errs = self.check("2026-11-01", c)
        self.assertTrue(any("개수" in e for e in errs), errs)

    def test_answers_count_mismatch_is_error(self):
        c = make_content(n_sentences=1, n_a_answers=2)
        errs = self.check("2026-11-01", c)
        self.assertTrue(any("answers" in e for e in errs), errs)

    def test_middledot_in_levels_a_en_is_error(self):
        c = make_content(bad_en="Drones · deliver packages.")
        errs = self.check("2026-11-01", c)
        self.assertTrue(any("가운뎃점" in e for e in errs), errs)

    def test_markdown_leftover_in_levels_a_en_is_error(self):
        c = make_content(bad_en="_italic_ word")
        errs = self.check("2026-11-01", c)
        self.assertTrue(any("마크다운" in e for e in errs), errs)

    def test_chunks_required_in_levels_a(self):
        """levels.a.sentences[].chunks 는 항상 필수다."""
        c = make_content()
        c["levels"]["a"]["sentences"][0].pop("chunks", None)
        errs = self.check("2026-11-01", c)
        self.assertTrue(any("chunks" in e for e in errs), errs)

    def test_chunks_join_mismatch_in_levels_a(self):
        bad_chunks = [["Drones bring", "드론이 가져다준다"], ["packages to door.", "소포를 문까지"]]
        c = make_content(a_chunks=bad_chunks)
        errs = self.check("2026-11-01", c)
        self.assertTrue(any("chunks" in e for e in errs), errs)

    def test_japanese_levels_ignored(self):
        """일본어 파일은 levels.a 검사 대상이 아니다."""
        c = make_content()
        p = self.root / "content" / "ja"
        p.mkdir(parents=True, exist_ok=True)
        f = p / "2026-11-01.json"
        # 일본어 형식에 맞춰 간단한 픽스처
        ja_c = {"date": "2026-11-01", "category": "science", "topic": "ドローン", "title_ko": "드론", "headline": "Drone",
                "chips": ["5文"], "sentences": [{"en": "ドローンです。"}],
                "words": [["ドローン", "드론"]] * 5, "points": [{"title": "p", "body": "b"}],
                "answers": ["해석"], "advanced": [{"word": "w", "meaning": "m", "confuse": None, "example": "ex"}] * 6,
                "source": None, "example": True}
        f.write_text(json.dumps(ja_c, ensure_ascii=False))
        errs = cc.check(f)[0]
        self.assertFalse(any("levels" in e.lower() for e in errs))

    def test_overlap_ignores_levels_a_sentences(self):
        """겹침 검사는 levels.a.sentences 를 무시하고 원문 sentences 만 본다."""
        day1 = "2026-11-01"
        day2 = "2026-11-10"
        # 두 지문의 원문은 서로 다르고, levels.a 내용이 같아도 겹침 오류가 없어야 한다
        c1 = make_content()
        c1["sentences"] = [{"en": "The cat sat on the mat today.", "b2": False}]
        c1["answers"] = ["고양이가 매트 위에 앉아 있다."]
        c1["source"] = {"title": "Article A (SiteA, 2026-11-01)", "url": "https://example.com/a"}
        write_content(self.root, "en", day1, c1)
        c2 = make_content()
        c2["sentences"] = [{"en": "Scientists found a new planet yesterday.", "b2": False}]
        c2["answers"] = ["과학자들이 새 행성을 발견했다."]
        c2["source"] = {"title": "Article B (SiteB, 2026-11-10)", "url": "https://example.com/b"}
        p2 = write_content(self.root, "en", day2, c2)
        errs = cc.overlap(p2, c2)
        self.assertEqual(errs, [])


# ── build_email: 수준별 빌드 + 회귀 테스트 ───────────────────────────────────

class TestBuildEmail(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        # 테스트용 content 디렉터리
        (self.root / "content" / "en").mkdir(parents=True)
        # 실제 렌더된 HTML 파일도 필요 (parse() 가 읽음)
        (self.root / "en" / "2026-10-22").mkdir(parents=True)

    def _patch_root(self):
        """build_email.parse 가 읽는 HTML 경로를 실제 파일로 대체."""
        real_html = REPO / "en" / "2026-10-22" / "index.html"
        if not real_html.exists():
            self.skipTest("실제 렌더된 HTML 없음, 회귀 테스트 건너뜀")
        return real_html

    def test_build_b_returns_dict_with_subject_and_body(self):
        """build(lang, day, 'b') 는 subject, body 키가 있는 딕셔너리를 반환한다."""
        real_html = self._patch_root()
        result = build_email.build("en", "2026-10-22", "b")
        self.assertIn("subject", result)
        self.assertIn("body", result)
        self.assertIn("?level=b", result["body"])

    def test_build_b_regression_byte_identical(self):
        """build(lang, day, 'b') 의 출력이 level 없이 호출한 기존 출력과 동일해야 한다."""
        self._patch_root()
        result_b = build_email.build("en", "2026-10-22", "b")
        # build_email.build 의 기존 시그니처(level='b' 기본값)와 동일
        result_default = build_email.build("en", "2026-10-22")
        self.assertEqual(result_b, result_default)

    def test_build_a_returns_none_when_no_levels(self):
        """levels.a 없는 content 에서 build(level='a') 는 None 을 반환한다."""
        c = make_content(with_levels=False)
        (REPO / "content" / "en" / "test-levels-no-a.json").write_text(
            json.dumps(c, ensure_ascii=False), encoding="utf-8")
        try:
            # parse() 가 읽을 HTML 파일도 없으므로 parse 를 mock 한다
            with patch.object(build_email, "parse", return_value={
                "date": "2026-11-01", "topic": "드론", "headline": "Drone",
                "chips": [], "sentences": ["Sentence one."], "words": [("pkg", "소포")], "source": None,
            }):
                result = build_email.build("en", "test-levels-no-a", "a")
            self.assertIsNone(result)
        finally:
            (REPO / "content" / "en" / "test-levels-no-a.json").unlink(missing_ok=True)

    def test_build_a_uses_levels_a_sentences(self):
        """build(level='a') 는 levels.a.sentences 의 en 을 이메일 본문에 사용한다."""
        c = make_content(n_sentences=1)
        day = "test-levels-with-a"
        content_path = REPO / "content" / "en" / f"{day}.json"
        content_path.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
        try:
            with patch.object(build_email, "parse", return_value={
                "date": "2026-11-01", "topic": "드론", "headline": "Drone",
                "chips": [], "sentences": [build_email._marks_email(MAIN_SENTENCE)],
                "words": [("packages", "소포")], "source": None,
            }):
                result = build_email.build("en", day, "a")
            self.assertIsNotNone(result)
            # level a 문장이 본문에 있어야 한다
            self.assertIn("Drones bring packages", result["body"])
            self.assertIn("?level=a", result["body"])
        finally:
            content_path.unlink(missing_ok=True)


# ── send_email: same_issue, audience, wants, catchup 로직 ───────────────────

class TestSameIssue(unittest.TestCase):
    def test_same_lang_day_level_b(self):
        meta = {"lang": "en", "day": "2026-11-01", "level": "b"}
        self.assertTrue(send_email.same_issue(meta, "en", "day", "2026-11-01", "b"))

    def test_same_lang_day_level_a(self):
        meta = {"lang": "en", "day": "2026-11-01", "level": "a"}
        self.assertTrue(send_email.same_issue(meta, "en", "day", "2026-11-01", "a"))

    def test_different_level_does_not_match(self):
        meta = {"lang": "en", "day": "2026-11-01", "level": "b"}
        self.assertFalse(send_email.same_issue(meta, "en", "day", "2026-11-01", "a"))

    def test_missing_level_treated_as_b(self):
        """level 키 없는 기존 메일은 중급(b)으로 취급한다."""
        meta = {"lang": "en", "day": "2026-11-01"}
        self.assertTrue(send_email.same_issue(meta, "en", "day", "2026-11-01", "b"))
        self.assertFalse(send_email.same_issue(meta, "en", "day", "2026-11-01", "a"))


class TestAudience(unittest.TestCase):
    def test_level_b_adds_not_equals_filter(self):
        result = send_email.audience("en", "b")
        level_filters = [f for f in result["filters"] if f.get("field") == "subscriber.metadata.level"]
        self.assertEqual(len(level_filters), 1)
        self.assertEqual(level_filters[0]["operator"], "not_equals")
        self.assertEqual(level_filters[0]["value"], "a")

    def test_level_a_adds_equals_filter(self):
        result = send_email.audience("en", "a")
        level_filters = [f for f in result["filters"] if f.get("field") == "subscriber.metadata.level"]
        self.assertEqual(len(level_filters), 1)
        self.assertEqual(level_filters[0]["operator"], "equals")
        self.assertEqual(level_filters[0]["value"], "a")

    def test_default_level_is_b(self):
        result_default = send_email.audience("en")
        result_b = send_email.audience("en", "b")
        self.assertEqual(result_default, result_b)


class TestWants(unittest.TestCase):
    def _sub(self, lang=None, level=None, sub_type="regular"):
        meta = {}
        if lang:
            meta["lang"] = lang
        if level:
            meta["level"] = level
        return {"type": sub_type, "metadata": meta}

    def test_en_no_level_wants_b(self):
        """level 키 없는 구독자는 중급(b) 메일을 받아야 한다."""
        sub = self._sub()
        self.assertTrue(send_email.wants(sub, "en", "b"))
        self.assertFalse(send_email.wants(sub, "en", "a"))

    def test_en_level_a_wants_a_not_b(self):
        sub = self._sub(level="a")
        self.assertTrue(send_email.wants(sub, "en", "a"))
        self.assertFalse(send_email.wants(sub, "en", "b"))

    def test_en_level_b_wants_b_not_a(self):
        sub = self._sub(level="b")
        self.assertTrue(send_email.wants(sub, "en", "b"))
        self.assertFalse(send_email.wants(sub, "en", "a"))

    def test_ja_subscriber_does_not_want_en(self):
        sub = self._sub(lang="ja")
        self.assertFalse(send_email.wants(sub, "en", "b"))

    def test_non_regular_never_wants(self):
        sub = self._sub(sub_type="unactivated")
        self.assertFalse(send_email.wants(sub, "en", "b"))


class TestRecentlySent(unittest.TestCase):
    def test_within_30_min(self):
        now = datetime.datetime(2026, 11, 1, 10, 0, tzinfo=datetime.timezone.utc)
        sent = "2026-11-01T09:45:00Z"
        self.assertTrue(send_email.recently_sent(sent, now))

    def test_over_30_min(self):
        now = datetime.datetime(2026, 11, 1, 10, 0, tzinfo=datetime.timezone.utc)
        sent = "2026-11-01T09:00:00Z"
        self.assertFalse(send_email.recently_sent(sent, now))


if __name__ == "__main__":
    unittest.main()
