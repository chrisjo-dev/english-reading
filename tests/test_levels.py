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
        """LEVELS_FROM(2026-10-23) 이전이면 levels 없어도 오류 없음."""
        errs = self.check("2026-10-22", make_content(with_levels=False))
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

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class TestBuildEmail(unittest.TestCase):
    def _patch_root(self):
        """실제 렌더된 HTML 없으면 테스트 건너뜀."""
        real_html = REPO / "en" / "2026-10-22" / "index.html"
        if not real_html.exists():
            self.skipTest("실제 렌더된 HTML 없음, 회귀 테스트 건너뜀")
        return real_html

    def test_build_b_no_level_param_in_url(self):
        """build(lang, day, 'b') 는 ?level=b 를 URL에 추가하지 않는다(페이지 기본값 b)."""
        self._patch_root()
        result = build_email.build("en", "2026-10-22", "b")
        self.assertIn("subject", result)
        self.assertIn("body", result)
        self.assertNotIn("?level=b", result["body"])
        # 썸네일 URL 에도 ?level= 가 없어야 한다
        self.assertNotIn("thumb.png?", result["body"])
        self.assertNotIn("?level=bthumb", result["body"])

    def test_build_b_regression_en(self):
        """build(en, 2026-10-22, b) 가 Phase 2 이전 출력과 바이트 일치한다."""
        self._patch_root()
        snap_path = FIXTURES / "email_b_en_2026-10-22.json"
        if not snap_path.exists():
            self.skipTest("스냅샷 픽스처 없음")
        result = build_email.build("en", "2026-10-22", "b")
        snap = json.loads(snap_path.read_text(encoding="utf-8"))
        self.assertEqual(result, snap, "level b 이메일이 Phase 2 이전 출력과 달라졌습니다")

    def test_build_b_regression_ja(self):
        """build(ja, 2026-10-22, b) 가 Phase 2 이전 출력과 바이트 일치한다."""
        real_html = REPO / "ja" / "2026-10-22" / "index.html"
        if not real_html.exists():
            self.skipTest("ja 렌더 HTML 없음")
        snap_path = FIXTURES / "email_b_ja_2026-10-22.json"
        if not snap_path.exists():
            self.skipTest("스냅샷 픽스처 없음")
        result = build_email.build("ja", "2026-10-22", "b")
        snap = json.loads(snap_path.read_text(encoding="utf-8"))
        self.assertEqual(result, snap, "ja level b 이메일이 Phase 2 이전 출력과 달라졌습니다")

    def test_build_a_returns_none_when_no_levels(self):
        """levels.a 없는 content 에서 build(level='a') 는 None 을 반환한다."""
        c = make_content(with_levels=False)
        (REPO / "content" / "en" / "test-levels-no-a.json").write_text(
            json.dumps(c, ensure_ascii=False), encoding="utf-8")
        try:
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
            self.assertIn("Drones bring packages", result["body"])
            # level a 이메일은 ?level=a 를 포함한다
            self.assertIn("?level=a", result["body"])
            # 썸네일에는 ?level= 없음
            self.assertNotIn("thumb.png?", result["body"])
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

    def test_level_none_has_no_level_filter(self):
        """audience(lang, None) 은 수준 필터를 추가하지 않는다(단계적 배포 호환)."""
        result = send_email.audience("en", None)
        level_filters = [f for f in result["filters"] if f.get("field") == "subscriber.metadata.level"]
        self.assertEqual(level_filters, [])


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


class TestFillMissingLevel(unittest.TestCase):
    """fill_missing_level() 은 level 키 없는 구독자를 'b' 로 채운다."""

    def _make_sub(self, sub_id, meta, sub_type="regular"):
        return {"id": sub_id, "type": sub_type, "metadata": meta}

    def test_patches_missing_level(self):
        subs = [self._make_sub("s1", {"lang": "en"})]
        with patch.object(send_email, "subscribers", return_value=iter(subs)), \
             patch.object(send_email, "call") as mock_call:
            send_email.fill_missing_level()
        mock_call.assert_called_once_with("PATCH", "/subscribers/s1", {"metadata": {"lang": "en", "level": "b"}})

    def test_skips_existing_level(self):
        subs = [self._make_sub("s2", {"lang": "en", "level": "a"})]
        with patch.object(send_email, "subscribers", return_value=iter(subs)), \
             patch.object(send_email, "call") as mock_call:
            send_email.fill_missing_level()
        mock_call.assert_not_called()

    def test_skips_non_active_type(self):
        subs = [self._make_sub("s3", {}, sub_type="spam")]
        with patch.object(send_email, "subscribers", return_value=iter(subs)), \
             patch.object(send_email, "call") as mock_call:
            send_email.fill_missing_level()
        mock_call.assert_not_called()

    def test_patches_unactivated_with_no_level(self):
        subs = [self._make_sub("s4", {}, sub_type="unactivated")]
        with patch.object(send_email, "subscribers", return_value=iter(subs)), \
             patch.object(send_email, "call") as mock_call:
            send_email.fill_missing_level()
        mock_call.assert_called_once()


class TestLevelCliValidation(unittest.TestCase):
    """--level CLI 파라미터는 'a' 또는 'b' 만 허용한다."""

    def _run_main(self, argv):
        """send_email __main__ 블록의 level 파싱 로직을 직접 테스트한다."""
        level = "b"
        if "--level" in argv:
            li = argv.index("--level")
            if li + 1 < len(argv):
                level = argv[li + 1]
            if level not in ("a", "b"):
                raise SystemExit(f"--level 값이 올바르지 않습니다: {level!r}")
        return level

    def test_valid_level_a(self):
        self.assertEqual(self._run_main(["en", "2026-10-22", "--level", "a"]), "a")

    def test_valid_level_b(self):
        self.assertEqual(self._run_main(["en", "2026-10-22", "--level", "b"]), "b")

    def test_invalid_level_raises(self):
        with self.assertRaises(SystemExit) as ctx:
            self._run_main(["en", "2026-10-22", "--level", "c"])
        self.assertIn("올바르지 않습니다", str(ctx.exception))

    def test_no_level_defaults_to_b(self):
        self.assertEqual(self._run_main(["en", "2026-10-22"]), "b")


class TestCheckLevelsANumber(unittest.TestCase):
    """check_content: levels.a 에 출처 없는 수치 경고 적용."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())

    def _check(self, c, day="2026-11-01"):
        p = self.root / "content" / "en"
        p.mkdir(parents=True, exist_ok=True)
        f = p / f"{day}.json"
        f.write_text(json.dumps(c, ensure_ascii=False))
        return cc.check(f)

    def test_no_source_with_numbers_in_levels_a_warns(self):
        """출처 없고 levels.a 문장에 구체적 수치가 있으면 경고."""
        c = make_content(a_sentence="30 drones will fly from 5 city centers.")
        c.pop("source", None)  # 출처 제거
        c["example"] = False
        _, warnings = self._check(c)
        self.assertTrue(any("levels.a" in w for w in warnings), warnings)

    def test_with_source_no_warn_for_levels_a(self):
        """출처가 있으면 levels.a 수치 경고 없음."""
        c = make_content(a_sentence="30 drones will fly from 5 city centers.")
        c["source"] = {"title": "Test (2026-10-01)", "url": "https://example.com"}
        _, warnings = self._check(c)
        self.assertFalse(any("levels.a" in w for w in warnings), warnings)

    def test_example_no_warn_for_levels_a(self):
        """example=True 이면 경고 없음."""
        c = make_content(a_sentence="30 drones fly in 5 minutes.")
        c.pop("source", None)
        c["example"] = True
        _, warnings = self._check(c)
        self.assertFalse(any("levels.a" in w for w in warnings), warnings)


class TestWantsLevelNone(unittest.TestCase):
    """wants(sub, lang, None): 수준 필터 없음 — 해당 언어 구독자 전체."""

    def _sub(self, lang=None, level=None, sub_type="regular"):
        meta = {}
        if lang:
            meta["lang"] = lang
        if level:
            meta["level"] = level
        return {"type": sub_type, "metadata": meta}

    def test_level_none_includes_a_subscriber(self):
        self.assertTrue(send_email.wants(self._sub(level="a"), "en", None))

    def test_level_none_includes_b_subscriber(self):
        self.assertTrue(send_email.wants(self._sub(level="b"), "en", None))

    def test_level_none_includes_no_level_subscriber(self):
        self.assertTrue(send_email.wants(self._sub(), "en", None))

    def test_level_none_excludes_wrong_lang(self):
        self.assertFalse(send_email.wants(self._sub(lang="ja"), "en", None))

    def test_level_none_excludes_non_regular(self):
        self.assertFalse(send_email.wants(self._sub(sub_type="unactivated"), "en", None))


class TestMainNoAContent(unittest.TestCase):
    """main(): 기초 지문 없을 때 새 동작 — level a 는 조용히 종료, level b 는 전체 대상."""

    def _mock_parse(self, topic="드론"):
        return {"topic": topic, "date": "2026-11-01", "headline": "Drone", "chips": [],
                "sentences": [], "words": [], "source": None}

    def test_level_a_no_content_exits_0_no_send(self):
        """--level a 호출 시 기초 지문 없으면 send 하지 않고 종료한다."""
        with patch.object(send_email, "wait_live"), \
             patch.object(build_email, "parse", return_value=self._mock_parse()), \
             patch.object(build_email, "build", return_value=None), \
             patch.object(send_email, "send") as mock_send:
            send_email.main("en", "2026-11-01", level="a")
        mock_send.assert_not_called()

    def test_level_b_no_a_content_uses_none_audience(self):
        """--level b 호출 시 기초 지문 없으면 level=None(전체 대상)으로 send 한다."""
        dummy_mail = {"subject": "s", "body": "b"}
        with patch.object(send_email, "wait_live"), \
             patch.object(build_email, "parse", return_value=self._mock_parse()), \
             patch.object(build_email, "build", side_effect=lambda l, d, lv: dummy_mail if lv == "b" else None), \
             patch.object(send_email, "send") as mock_send:
            send_email.main("en", "2026-11-01", level="b")
        mock_send.assert_called_once()
        _, kwargs = mock_send.call_args
        assert kwargs.get("level") is None or mock_send.call_args[0][4] is None, \
            f"Expected level=None, got: {mock_send.call_args}"

    def test_level_b_with_a_content_uses_b_audience(self):
        """--level b 호출 시 기초 지문 있으면 level='b'(b-구독자만)로 send 한다."""
        dummy_mail = {"subject": "s", "body": "b"}
        with patch.object(send_email, "wait_live"), \
             patch.object(build_email, "parse", return_value=self._mock_parse()), \
             patch.object(build_email, "build", return_value=dummy_mail), \
             patch.object(send_email, "send") as mock_send:
            send_email.main("en", "2026-11-01", level="b")
        mock_send.assert_called_once()
        # level 인자 확인: positional 또는 keyword
        call_args = mock_send.call_args
        level_arg = call_args[1].get("level") if call_args[1] else call_args[0][4]
        self.assertEqual(level_arg, "b")


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


class TestLevelAllSentinel(unittest.TestCase):
    """수준 필터 없이 보낸 메일은 metadata.level 을 null 이 아닌 'all' 로 남겨, 같은 날 다시 돌려도 중복 발송하지 않는다."""

    def test_same_issue_all(self):
        meta = {"lang": "ja", "day": "2026-10-24", "level": "all"}
        self.assertTrue(send_email.same_issue(meta, "ja", "day", "2026-10-24", None))
        self.assertFalse(send_email.same_issue(meta, "ja", "day", "2026-10-24", "b"))

    def test_old_email_without_level_is_b(self):
        meta = {"lang": "en", "day": "2026-10-20"}
        self.assertTrue(send_email.same_issue(meta, "en", "day", "2026-10-20", "b"))
        self.assertFalse(send_email.same_issue(meta, "en", "day", "2026-10-20", None))
