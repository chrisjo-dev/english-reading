"""독일어(de) Phase 1 단위 테스트.

토크나이저, 겹침 감지, 언어 플래그, noindex 렌더링, 사이트맵 제외,
이메일 거부, audience() 제외, chunks 렌더링, en/ja 회귀 없음을 검사한다.

실행: python -m pytest -q tests/test_de.py
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

import check_content as cc   # noqa: E402
import langs                  # noqa: E402
import publish                # noqa: E402
import render as rnd          # noqa: E402
import send_email             # noqa: E402

# ── 공통 독일어 지문 픽스처 ────────────────────────────────────────────────────

BAECKEREI_A = [
    "In Deutschland gibt es viele Bäckereien.",
    "Die meisten Bäckereien öffnen früh am Morgen.",
]
BAECKEREI_B = [
    "Deutsche kaufen jeden Morgen frisches Brot und Brötchen beim Bäcker.",
    "Die Bäckereien sind sehr beliebt und öffnen früh um sieben Uhr morgens.",
]
BAECKEREI_NEW = [
    "In Berlin eröffnet ein Café, das Brot nach alten Rezepten backt.",
    "Die Gäste kommen aus vielen Ländern, um die neuen Sorten zu probieren.",
]
WETTER = [
    "Im Sommer ist es oft warm und sonnig in Deutschland.",
    "Der Winter bringt Schnee und Kälte in viele Regionen des Landes.",
]


def de_doc(sents, words=None, url=None):
    """테스트용 독일어 콘텐츠 딕셔너리."""
    return {
        "topic": "테스트",
        "title_ko": "테스트 제목",
        "headline": "Test",
        "chips": ["5문장", "A2 위주", "B1 1문장", "약 3분"],
        "sentences": [{"en": s, "b2": False, "chunks": [["Wort.", "단어"]]} for s in sents],
        "words": [[w, "뜻"] for w in (words or ["Bäckerei", "Brot", "Morgen", "Laden", "backen", "Mehl"])],
        "points": [{"title": "테스트", "body": "설명"}],
        "answers": ["해석." for _ in sents],
        "advanced": [
            {"word": "frisch", "meaning": "신선한", "confuse": None,
             "example": "Das Brot ist **frisch** gebacken.", "example_ko": "빵이 갓 구워졌습니다."}
        ] * 6,
        "source": {"title": "t", "url": url} if url else None,
        "example": True,
    }


# ── 1. 언어 플래그 ─────────────────────────────────────────────────────────────

class DeLangFlagsTest(unittest.TestCase):
    """langs.LANGS["de"] 의 플래그를 검사한다."""

    def setUp(self):
        self.L = langs.LANGS["de"]

    def test_de_exists(self):
        self.assertIn("de", langs.LANGS)

    def test_email_is_true(self):
        self.assertTrue(self.L.get("email", True), "email 플래그가 True여야 합니다 (Phase 2: 메일 발송 활성화)")

    def test_noindex_is_true(self):
        self.assertTrue(self.L.get("noindex", False), "noindex 플래그가 True여야 합니다")

    def test_chunks_is_true(self):
        self.assertTrue(self.L.get("chunks", False), "chunks 플래그가 True여야 합니다")

    def test_levels_is_true(self):
        self.assertTrue(self.L.get("levels", False), "levels 플래그가 True여야 합니다")

    def test_level_a_label(self):
        self.assertIn("level_a_label", self.L, "de 는 level_a_label 키가 있어야 합니다")
        self.assertEqual(self.L["level_a_label"], "기초 A2~B1")

    def test_tts_is_qwen(self):
        self.assertEqual(self.L.get("tts"), "qwen", "tts 필드가 'qwen'이어야 합니다")

    def test_tts_lang_is_de_DE(self):
        self.assertEqual(self.L.get("tts_lang"), "de-DE", "tts_lang 이 'de-DE'여야 합니다")

    def test_en_email_is_true(self):
        self.assertTrue(langs.LANGS["en"].get("email", True), "en email 플래그가 True여야 합니다 (회귀)")

    def test_ja_email_is_true(self):
        self.assertTrue(langs.LANGS["ja"].get("email", True), "ja email 플래그가 True여야 합니다 (회귀)")


# ── 2. 독일어 토크나이저 ───────────────────────────────────────────────────────

class DeTokenizerTest(unittest.TestCase):
    """_de_content_words 가 Umlaut/ß 를 포함한 내용어를 올바르게 추출하는지 검사한다."""

    def words(self, sents):
        return cc._de_content_words({"sentences": [{"en": s} for s in sents]})

    def test_umlaut_extracted(self):
        w = self.words(["Die Bäckerei öffnet früh am Morgen."])
        self.assertIn("bäckerei", w)
        self.assertIn("öffnet", w)
        self.assertIn("morgen", w)

    def test_eszett_extracted(self):
        w = self.words(["Er heißt Klaus und ißt gern Weißbrot."])
        # heißt(5자), weißbrot(9자) 추출 기대
        self.assertTrue(any("ß" in word for word in w), f"ß 포함 단어가 없어요: {w}")

    def test_stopwords_excluded(self):
        w = self.words(["Das ist eine sehr gute Idee."])
        # 독일어 불용어(das, ist, eine, sehr)는 제외되어야 한다
        self.assertNotIn("das", w)
        self.assertNotIn("eine", w)
        self.assertNotIn("sehr", w)

    def test_short_words_excluded(self):
        w = self.words(["Sie ist gut."])
        # 3자 이하 단어는 제외
        self.assertNotIn("ist", w)
        self.assertNotIn("sie", w)

    def test_bold_markers_stripped(self):
        w = self.words(["Die **Bäckerei** ist beliebt."])
        self.assertIn("bäckerei", w)
        self.assertNotIn("**bäckerei**", w)


# ── 3. 독일어 겹침 감지 ────────────────────────────────────────────────────────

class DeOverlapTest(unittest.TestCase):
    """overlap() 이 독일어에서도 올바르게 동작하는지 검사한다."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp()) / "content" / "de"
        self.dir.mkdir(parents=True)
        self._write("2026-10-17", de_doc(BAECKEREI_A, ["Bäckerei", "Brot", "Morgen", "öffnen", "backen", "Mehl"]))

    def _write(self, day, c):
        p = self.dir / f"{day}.json"
        p.write_text(json.dumps(c, ensure_ascii=False))
        return p

    def check(self, day, c):
        return cc.overlap(self._write(day, c), c)

    def test_similar_story_is_error(self):
        errs = self.check("2026-10-21", de_doc(
            BAECKEREI_B,
            ["Bäckerei", "Brot", "Morgen", "backen", "Mehl", "Laden"]
        ))
        self.assertTrue(errs and "겹쳐요" in errs[0], f"겹침 오류가 없어요: {errs}")

    def test_new_development_is_ok(self):
        errs = self.check("2026-10-21", de_doc(
            BAECKEREI_NEW,
            ["Rezept", "Café", "Gäste", "Sorten", "probieren", "Berlin"]
        ))
        self.assertEqual(errs, [], f"새 내용인데 오류가 나요: {errs}")

    def test_different_topic_is_ok(self):
        errs = self.check("2026-10-21", de_doc(
            WETTER,
            ["Sommer", "Winter", "Schnee", "Wetter", "Region", "Kälte"]
        ))
        self.assertEqual(errs, [], f"다른 주제인데 오류가 나요: {errs}")

    def test_older_than_window_is_ok(self):
        errs = self.check("2026-11-05", de_doc(
            BAECKEREI_B,
            ["Bäckerei", "Brot", "Morgen", "backen", "Mehl", "Laden"]
        ))
        self.assertEqual(errs, [], "14일 넘은 지문은 겹침 검사에서 제외돼야 합니다")

    def test_pool_not_compared(self):
        pool = Path(tempfile.mkdtemp()) / "pool" / "de"
        pool.mkdir(parents=True)
        c = de_doc(BAECKEREI_B, ["Bäckerei", "Brot", "Morgen", "backen", "Mehl", "Laden"])
        p = pool / "de-test.json"
        p.write_text(json.dumps(c, ensure_ascii=False))
        self.assertEqual(cc.overlap(p, c), [], "pool 파일은 겹침 검사 대상이 아닙니다")


# ── 4. check_content 플래그 분기 ─────────────────────────────────────────────

class DeCheckFlagsTest(unittest.TestCase):
    """check_content.check() 가 de 언어의 chunks/levels 플래그를 올바르게 처리하는지 검사한다."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())

    def _write(self, lang, day, c, kind="content"):
        d = self.root / kind / lang
        d.mkdir(parents=True, exist_ok=True)
        p = d / f"{day}.json"
        p.write_text(json.dumps(c, ensure_ascii=False))
        return p

    def _check(self, lang, day, c, kind="content"):
        return cc.check(self._write(lang, day, c, kind))

    def test_de_requires_chunks(self):
        """de 지문은 chunks 가 없으면 오류."""
        c = de_doc(["Die Bäckerei öffnet früh."])
        # 모든 문장에서 chunks 제거
        for s in c["sentences"]:
            del s["chunks"]
        errs, _ = self._check("de", "2026-10-28", c)
        chunk_errs = [e for e in errs if "chunks" in e]
        self.assertTrue(chunk_errs, "de 지문에 chunks 없으면 오류가 나야 합니다")

    def test_de_does_not_require_levels_before_cutoff(self):
        """DE_LEVELS_FROM(2026-10-29) 이전이면 de 지문에 levels 없어도 오류 없음."""
        c = de_doc(["Die Bäckerei öffnet früh am Morgen."])
        errs, _ = self._check("de", "2026-10-28", c)
        level_errs = [e for e in errs if "levels" in e]
        self.assertEqual(level_errs, [], f"커트오프 이전 de 는 levels 불필요: {level_errs}")

    def test_de_requires_levels_after_cutoff(self):
        """2026-10-29 이후 de 지문은 levels.a 필수."""
        c = de_doc(["Die Bäckerei öffnet früh am Morgen."])
        errs, _ = self._check("de", "2026-10-29", c)
        level_errs = [e for e in errs if "levels" in e.lower()]
        self.assertTrue(level_errs, f"커트오프 이후 de 는 levels 필수여야 합니다: {errs}")

    def test_ja_still_no_chunks_required(self):
        """ja 회귀: chunks 없어도 오류 없음."""
        ja_c = {
            "topic": "t", "title_ko": "제목", "headline": "見出し",
            "chips": ["5文", "N3"],
            "sentences": [{"en": "今日は雨です。", "b2": False}],
            "words": [["雨", "비"]], "points": [], "answers": ["오늘은 비예요."],
            "advanced": [{"word": "雨", "meaning": "비", "confuse": None, "example": "**雨**が降っています。", "example_ko": "비가 오고 있습니다."}] * 6,
            "source": None, "example": True,
        }
        errs, _ = self._check("ja", "2026-10-28", ja_c)
        chunk_errs = [e for e in errs if "chunks" in e]
        self.assertEqual(chunk_errs, [], f"ja 는 chunks 불필요: {chunk_errs}")


# ── 5. noindex 메타 태그 렌더링 ───────────────────────────────────────────────

DE_FULL_CONTENT = {
    "date": "2026-10-28",
    "category": "culture",
    "topic": "동네 빵집",
    "title_ko": "매일 아침 문을 여는 동네 빵집",
    "headline": "Die Bäckerei um die Ecke",
    "chips": ["5문장", "A2 위주", "B1 1문장", "약 3분"],
    "sentences": [
        {"en": "In Deutschland gibt es viele **Bäckereien**.", "b2": False,
         "chunks": [["In Deutschland", "독일에는"], ["gibt es", "있습니다"], ["viele **Bäckereien**.", "빵집이 많이"]]},
        {"en": "Die Bäckerei öffnet früh am Morgen.", "b2": False,
         "chunks": [["Die Bäckerei", "빵집은"], ["öffnet", "엽니다"], ["früh am Morgen.", "이른 아침에"]]},
        {"en": "Viele Menschen kaufen frisches **Brot**.", "b2": False,
         "chunks": [["Viele Menschen", "많은 사람들이"], ["kaufen", "삽니다"], ["frisches **Brot**.", "신선한 빵을"]]},
        {"en": "Der Duft von Brot ist sehr angenehm.", "b2": False,
         "chunks": [["Der Duft", "향기는"], ["von Brot", "빵의"], ["ist sehr angenehm.", "매우 좋습니다"]]},
        {"en": "Die Verkäuferin empfiehlt den Roggenkuchen.", "b2": True,
         "chunks": [["Die Verkäuferin", "판매원이"], ["empfiehlt", "추천합니다"], ["den Roggenkuchen.", "호밀 케이크를"]]},
    ],
    "words": [["Bäckerei", "빵집"], ["Brot", "빵"], ["Brötchen", "롤빵"], ["Frühstück", "아침 식사"], ["Duft", "향기"], ["Roggen", "호밀"]],
    "points": [{"title": "zum Frühstück", "body": "`zum`은 `zu + dem` 이에요."}],
    "answers": ["독일에는 빵집이 많습니다.", "빵집은 이른 아침에 엽니다.", "많은 사람들이 신선한 빵을 삽니다.", "빵의 향기는 매우 좋습니다.", "판매원이 호밀 케이크를 추천합니다."],
    "advanced": [
        {"word": "frisch", "meaning": "신선한", "confuse": None,
         "example": "Das Brot ist **frisch**.", "example_ko": "빵이 신선합니다."}
    ] * 6,
    "source": None,
    "example": True,
    "levels": {
        "a": {
            "sentences": [
                {"en": "In Deutschland gibt es Baeckereien.", "chunks": [["In Deutschland gibt es Baeckereien.", "독일에는 빵집이 있습니다"]]},
                {"en": "Die Baeckerei oeffnet frueh.", "chunks": [["Die Baeckerei oeffnet frueh.", "빵집은 일찍 엽니다"]]},
                {"en": "Viele Menschen kaufen Brot.", "chunks": [["Viele Menschen kaufen Brot.", "많은 사람들이 빵을 삽니다"]]},
                {"en": "Das Brot riecht gut.", "chunks": [["Das Brot riecht gut.", "빵 냄새가 좋습니다"]]},
                {"en": "Sie empfiehlt Roggenkuchen.", "chunks": [["Sie empfiehlt Roggenkuchen.", "그녀가 호밀 케이크를 추천합니다"]]},
            ],
            "answers": [
                "독일에는 빵집이 있습니다.",
                "빵집은 일찍 엽니다.",
                "많은 사람들이 빵을 삽니다.",
                "빵 냄새가 좋습니다.",
                "그녀가 호밀 케이크를 추천합니다.",
            ],
        }
    },
}


class DeNoindexRenderTest(unittest.TestCase):
    """render() 가 de 언어에 noindex 메타 태그를 삽입하는지 검사한다."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        content_dir = self.tmp / "content" / "de"
        content_dir.mkdir(parents=True)
        (content_dir / "2026-10-28.json").write_text(
            json.dumps(DE_FULL_CONTENT, ensure_ascii=False), encoding="utf-8"
        )

    def _render(self):
        orig_root = rnd.ROOT
        try:
            rnd.ROOT = self.tmp
            rnd.render("de", "2026-10-28")
        finally:
            rnd.ROOT = orig_root
        return (self.tmp / "de" / "2026-10-28" / "index.html").read_text(encoding="utf-8")

    def test_noindex_meta_present(self):
        html = self._render()
        self.assertIn('<meta name="robots" content="noindex">', html,
                      "de 렌더링에 noindex 메타 태그가 있어야 합니다")

    def test_noindex_before_stylesheet(self):
        html = self._render()
        ni_pos = html.find('<meta name="robots" content="noindex">')
        css_pos = html.find('<link rel="stylesheet"')
        self.assertGreater(css_pos, ni_pos, "noindex 가 stylesheet link 앞에 있어야 합니다")

    def test_en_has_no_noindex(self):
        """en 회귀: noindex 없음. render() 검증을 통과할 수 있도록 콘텐츠를 완전하게 준비한다."""
        en_dir = self.tmp / "content" / "en"
        en_dir.mkdir(parents=True, exist_ok=True)
        # DE_FULL_CONTENT 를 그대로 복사한다 (5문장 충족, render 검증 통과)
        import copy
        en_c = copy.deepcopy(DE_FULL_CONTENT)
        (en_dir / "2026-10-28.json").write_text(json.dumps(en_c, ensure_ascii=False), encoding="utf-8")
        orig_root = rnd.ROOT
        try:
            rnd.ROOT = self.tmp
            rnd.render("en", "2026-10-28")
        finally:
            rnd.ROOT = orig_root
        en_html = (self.tmp / "en" / "2026-10-28" / "index.html").read_text(encoding="utf-8")
        self.assertNotIn('content="noindex"', en_html, "en 렌더링에는 noindex 가 없어야 합니다")


# ── 6. 사이트맵 / latest.json 제외 ────────────────────────────────────────────

class DeNoindexPublishTest(unittest.TestCase):
    """write_sitemap() 과 rebuild_root() 가 de 를 제외하는지 검사한다."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        # en 콘텐츠 준비
        en_dir = self.tmp / "content" / "en"
        en_dir.mkdir(parents=True, exist_ok=True)
        (en_dir / "2026-10-28.json").write_text(json.dumps({
            "topic": "test", "title_ko": "제목", "headline": "Head",
            "chips": ["5문장"], "sentences": [{"en": "Test.", "b2": False}],
            "words": [["test", "테스트"]], "points": [], "answers": ["테스트."],
            "advanced": [{"word": "test", "meaning": "테스트", "confuse": None, "example": "**test**.", "example_ko": "테스트."}] * 6,
            "source": None, "example": True,
        }, ensure_ascii=False), encoding="utf-8")
        # de 콘텐츠 준비
        de_dir = self.tmp / "content" / "de"
        de_dir.mkdir(parents=True, exist_ok=True)
        (de_dir / "2026-10-28.json").write_text(
            json.dumps(DE_FULL_CONTENT, ensure_ascii=False), encoding="utf-8"
        )
        # days_of() 는 {lang}/{day}/index.html 존재를 확인한다
        en_day = self.tmp / "en" / "2026-10-28"
        en_day.mkdir(parents=True, exist_ok=True)
        (en_day / "index.html").write_text(
            '<html><head><title>테스트</title></head><body>'
            '<h1><em>테스트</em></h1></body></html>', encoding="utf-8"
        )
        de_day = self.tmp / "de" / "2026-10-28"
        de_day.mkdir(parents=True, exist_ok=True)
        (de_day / "index.html").write_text(
            '<html><head><title>테스트</title></head><body>'
            '<h1><em>빵집</em></h1></body></html>', encoding="utf-8"
        )

    def _write_sitemap(self):
        orig = publish.ROOT
        try:
            publish.ROOT = self.tmp
            publish.write_sitemap()
        finally:
            publish.ROOT = orig
        return (self.tmp / "sitemap.xml").read_text(encoding="utf-8")

    def _rebuild_root(self):
        orig = publish.ROOT
        try:
            publish.ROOT = self.tmp
            publish.rebuild_root()
        finally:
            publish.ROOT = orig
        return json.loads((self.tmp / "latest.json").read_text(encoding="utf-8"))

    def test_sitemap_excludes_de(self):
        sitemap = self._write_sitemap()
        self.assertNotIn("/de/", sitemap, "사이트맵에 de URL 이 없어야 합니다")

    def test_sitemap_includes_en(self):
        sitemap = self._write_sitemap()
        self.assertIn("/en/", sitemap, "사이트맵에 en URL 이 있어야 합니다 (회귀)")

    def test_latest_json_excludes_de(self):
        data = self._rebuild_root()
        self.assertNotIn("de", data.get("langs", {}), "latest.json langs 에 de 가 없어야 합니다")

    def test_latest_json_includes_en(self):
        data = self._rebuild_root()
        self.assertIn("en", data.get("langs", {}), "latest.json langs 에 en 이 있어야 합니다 (회귀)")


# ── 7. 이메일 거부 ─────────────────────────────────────────────────────────────

class DeEmailSendTest(unittest.TestCase):
    """send_email.main() 과 main_weekly() 가 de(email=True)에서 wait_live 까지 진행하는지 검사한다."""

    def test_main_proceeds_for_de(self):
        """Phase 2: email=True 이므로 de 도 wait_live 까지 진행한다."""
        reached = []
        def mock_wait(*a, **k):
            reached.append(True)
            raise SystemExit("mock")  # 실제 HTTP 호출 방지
        with patch.object(send_email, "wait_live", mock_wait):
            try:
                send_email.main("de", "2026-10-28")
            except SystemExit:
                pass
        self.assertTrue(reached, "de 는 email=True 이므로 wait_live 까지 도달해야 합니다")

    def test_main_weekly_proceeds_for_de(self):
        """Phase 2: weekly 도 de 에서 진행한다."""
        reached = []
        def mock_wait(*a, **k):
            reached.append(True)
            raise SystemExit("mock")
        with patch.object(send_email, "wait_live", mock_wait):
            try:
                send_email.main_weekly("de", "2026-10-28")
            except SystemExit:
                pass
        self.assertTrue(reached, "de weekly 도 email=True 이므로 wait_live 까지 도달해야 합니다")

    def test_main_does_not_return_early_for_en(self):
        """en 회귀: wait_live 로 진행한다(실제 호출 전까지만 확인)."""
        reached = []
        def mock_wait(*a, **k):
            reached.append(True)
            raise SystemExit("mock")  # 실제 HTTP 호출 방지
        with patch.object(send_email, "wait_live", mock_wait):
            try:
                send_email.main("en", "2026-10-28")
            except SystemExit:
                pass
        self.assertTrue(reached, "en 은 wait_live 까지 도달해야 합니다 (회귀)")


# ── 8. audience() 에서 de 제외 ────────────────────────────────────────────────

class DeAudienceExclusionTest(unittest.TestCase):
    """audience("en") 이 not_equals de 필터를 포함하는지 검사한다."""

    def test_en_audience_excludes_de(self):
        aud = send_email.audience("en")
        filters = aud.get("filters", [])
        ne_langs = {f["value"] for f in filters if f.get("operator") == "not_equals"}
        self.assertIn("de", ne_langs, f"en audience 에서 de 를 제외해야 합니다. 현재 필터: {ne_langs}")

    def test_en_audience_excludes_ja(self):
        """ja 도 여전히 제외되어야 한다 (회귀)."""
        aud = send_email.audience("en")
        filters = aud.get("filters", [])
        ne_langs = {f["value"] for f in filters if f.get("operator") == "not_equals"}
        self.assertIn("ja", ne_langs, f"en audience 에서 ja 도 제외해야 합니다 (회귀). 현재: {ne_langs}")

    def test_de_audience_uses_equals(self):
        aud = send_email.audience("de")
        filters = aud.get("filters", [])
        eq_langs = {f["value"] for f in filters if f.get("operator") == "equals"}
        self.assertIn("de", eq_langs, "de audience 는 equals de 필터를 써야 합니다")


# ── 9. de chunk_rows 렌더링 ───────────────────────────────────────────────────

class DeChunkRenderTest(unittest.TestCase):
    """chunk_rows() 가 de 언어의 chunks 를 올바르게 렌더링하는지 검사한다."""

    DE_SENTS = [
        {"en": "In Deutschland gibt es viele **Bäckereien**.", "b2": False,
         "chunks": [["In Deutschland", "독일에는"], ["gibt es", "있습니다"], ["viele **Bäckereien**.", "빵집이 많이"]]},
        {"en": "Die Bäckerei öffnet früh am Morgen.", "b2": False,
         "chunks": [["Die Bäckerei", "빵집은"], ["öffnet", "엽니다"], ["früh am Morgen.", "이른 아침에"]]},
    ]

    def test_de_chunk_rows_not_none(self):
        rows = rnd.chunk_rows("de", "2026-10-28", self.DE_SENTS)
        self.assertIsNotNone(rows, "de chunks 가 있으면 chunk_rows 가 None 이 아니어야 합니다")

    def test_de_chunk_rows_count(self):
        rows = rnd.chunk_rows("de", "2026-10-28", self.DE_SENTS)
        self.assertEqual(len(rows), 2, "문장 수만큼 chunk row 가 있어야 합니다")

    def test_de_bold_rendered(self):
        rows = rnd.chunk_rows("de", "2026-10-28", self.DE_SENTS)
        self.assertIn("<b>Bäckereien</b>", rows[0], "** 표시가 <b> 태그로 렌더링되어야 합니다")

    def test_de_missing_chunks_returns_none(self):
        sents_no_chunks = [{"en": "Die Bäckerei öffnet früh.", "b2": False}]
        rows = rnd.chunk_rows("de", "2026-10-28", sents_no_chunks)
        self.assertIsNone(rows, "chunks 없으면 None 이어야 합니다")

    def test_ja_chunk_rows_still_none(self):
        """ja 회귀: chunk_rows 는 여전히 None."""
        rows = rnd.chunk_rows("ja", "2026-10-28", [{"en": "今日は雨です。", "chunks": [["今日", "오늘"]]}])
        self.assertIsNone(rows, "ja 는 chunk_rows 가 None 이어야 합니다 (회귀)")

    def test_de_chips_a_label_rendered(self):
        """de chips_a 레이블이 level_a_label 값을 사용하는지 확인한다."""
        import copy, pathlib as _pl
        tmp = _pl.Path(tempfile.mkdtemp())
        content_dir = tmp / "content" / "de"
        content_dir.mkdir(parents=True)
        (content_dir / "2026-10-28.json").write_text(
            json.dumps(DE_FULL_CONTENT, ensure_ascii=False), encoding="utf-8"
        )
        orig_root = rnd.ROOT
        try:
            rnd.ROOT = tmp
            rnd.render("de", "2026-10-28")
        finally:
            rnd.ROOT = orig_root
        html = (tmp / "de" / "2026-10-28" / "index.html").read_text(encoding="utf-8")
        self.assertIn("기초 A2~B1", html,
                      "de 렌더링 chips_a 에 level_a_label 값이 있어야 합니다")


# ── 10. rebuild_lists() noindex 메타 주입 ─────────────────────────────────────

class DeRebuildListsNoindexTest(unittest.TestCase):
    """rebuild_lists() 가 de 목록/아카이브 페이지에 noindex 메타를 삽입하는지 검사한다."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        # days_of() 가 확인하는 index.html 준비
        day_dir = self.tmp / "de" / "2026-10-28"
        day_dir.mkdir(parents=True)
        (day_dir / "index.html").write_text(
            '<html><head><title>빵집</title></head><body>'
            '<h1><em>동네 빵집</em></h1></body></html>', encoding="utf-8"
        )
        # entry() 가 읽는 content JSON 준비
        content_dir = self.tmp / "content" / "de"
        content_dir.mkdir(parents=True)
        (content_dir / "2026-10-28.json").write_text(
            json.dumps(DE_FULL_CONTENT, ensure_ascii=False), encoding="utf-8"
        )
        # thumb.png stub (publish.entry 에서 직접 읽지는 않으나 경로 참조용)
        (day_dir / "thumb.png").write_bytes(b"")

    def _rebuild_lists(self):
        orig = publish.ROOT
        try:
            publish.ROOT = self.tmp
            publish.rebuild_lists("de")
        finally:
            publish.ROOT = orig

    def test_list_page_has_noindex(self):
        self._rebuild_lists()
        page = (self.tmp / "de" / "index.html").read_text(encoding="utf-8")
        self.assertIn('<meta name="robots" content="noindex">', page,
                      "de 목록 페이지에 noindex 메타가 있어야 합니다")

    def test_archive_page_has_noindex(self):
        self._rebuild_lists()
        archive = (self.tmp / "de" / "archive" / "index.html").read_text(encoding="utf-8")
        self.assertIn('<meta name="robots" content="noindex">', archive,
                      "de 아카이브 페이지에 noindex 메타가 있어야 합니다")

    def test_noindex_before_stylesheet(self):
        self._rebuild_lists()
        page = (self.tmp / "de" / "index.html").read_text(encoding="utf-8")
        ni_pos = page.find('<meta name="robots" content="noindex">')
        css_pos = page.find('<link rel="stylesheet"')
        self.assertGreater(css_pos, ni_pos, "noindex 가 stylesheet 앞에 있어야 합니다")

    def test_en_list_has_no_noindex(self):
        """en 회귀: 목록 페이지에 noindex 없음."""
        en_day = self.tmp / "en" / "2026-10-28"
        en_day.mkdir(parents=True)
        (en_day / "index.html").write_text(
            '<html><head></head><body><h1><em>test</em></h1></body></html>', encoding="utf-8"
        )
        (en_day / "thumb.png").write_bytes(b"")
        en_content = self.tmp / "content" / "en"
        en_content.mkdir(parents=True)
        (en_content / "2026-10-28.json").write_text(
            json.dumps(DE_FULL_CONTENT, ensure_ascii=False), encoding="utf-8"
        )
        orig = publish.ROOT
        try:
            publish.ROOT = self.tmp
            publish.rebuild_lists("en")
        finally:
            publish.ROOT = orig
        en_page = (self.tmp / "en" / "index.html").read_text(encoding="utf-8")
        self.assertNotIn('content="noindex"', en_page, "en 목록 페이지에 noindex 가 없어야 합니다 (회귀)")


# ── 11. de 지문 품질 검사 (문장 길이 경고, advanced 개수 오류) ──────────────────

class DeQualityCheckTest(unittest.TestCase):
    """check_content.check_de_quality() 를 검사한다."""

    def _write_and_check(self, data, stem="2026-11-01", parent="content"):
        """임시 파일을 써서 check() 를 실행하고 (errors, warnings) 를 반환한다."""
        with tempfile.TemporaryDirectory() as tmp:
            lang_dir = Path(tmp) / parent / "de"
            lang_dir.mkdir(parents=True)
            p = lang_dir / f"{stem}.json"
            p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            return cc.check(p)

    def _base_content(self, avg_wc=17, adv_count=6):
        """검사에 통과하는 기본 de 지문을 만든다."""
        # avg_wc 단어 수의 문장을 6개 생성
        word = "Wort"
        sents = []
        for _ in range(6):
            en = " ".join([word] * avg_wc) + "."
            sents.append({
                "en": en,
                "b2": False,
                "chunks": [[en, "단어들"]],
            })
        advanced = [
            {"word": f"Wort{i}", "meaning": f"뜻{i}", "confuse": None,
             "example": f"**Wort{i}** hier.", "example_ko": f"예문{i}"}
            for i in range(adv_count)
        ]
        return {
            "date": "2026-11-01",
            "topic": "테스트",
            "title_ko": "테스트 제목",
            "headline": "Test",
            "chips": ["6문장", "B1 위주", "B2 1문장", "약 4분"],
            "sentences": sents,
            "words": [["Wort", "단어"]],
            "points": [{"title": "P", "body": "B"}],
            "answers": ["답." for _ in range(6)],
            "advanced": advanced,
            "source": None,
            "example": True,
            "levels": {
                "a": {
                    "sentences": [
                        {"en": "Kurzer Satz hier.", "chunks": [["Kurzer Satz hier.", "짧은 문장"]]}
                        for _ in range(6)
                    ],
                    "answers": ["짧은 문장." for _ in range(6)],
                }
            },
        }

    def test_no_warning_when_avg_gte_14(self):
        data = self._base_content(avg_wc=16)
        errors, warnings = self._write_and_check(data)
        self.assertFalse(any("평균 단어" in w for w in warnings),
                         "평균 16단어면 경고 없어야 합니다")

    def test_warning_when_avg_lt_14(self):
        data = self._base_content(avg_wc=10)
        errors, warnings = self._write_and_check(data)
        self.assertTrue(any("평균 단어" in w for w in warnings),
                        "평균 10단어면 경고가 있어야 합니다")

    def test_avg_exactly_14_no_warning(self):
        data = self._base_content(avg_wc=14)
        errors, warnings = self._write_and_check(data)
        self.assertFalse(any("평균 단어" in w for w in warnings),
                         "평균 14단어(경계값)는 경고 없어야 합니다")

    def test_no_error_when_advanced_gte_5_recent(self):
        """2026-10-29 이후 지문에서 advanced >= 5이면 오류 없다."""
        data = self._base_content(adv_count=6)
        errors, _ = self._write_and_check(data, stem="2026-10-30")
        self.assertFalse(any("advanced" in e for e in errors),
                         "advanced 6개면 오류 없어야 합니다")

    def test_error_when_advanced_lt_5_recent(self):
        """2026-10-29 이후 지문에서 advanced < 5이면 오류."""
        data = self._base_content(adv_count=3)
        errors, _ = self._write_and_check(data, stem="2026-10-30")
        self.assertTrue(any("advanced" in e for e in errors),
                        "advanced 3개이면 오류가 있어야 합니다")

    def test_no_error_for_old_content_low_advanced(self):
        """2026-10-28 이전 지문은 advanced 개수 검사 미적용."""
        data = self._base_content(adv_count=3)
        errors, _ = self._write_and_check(data, stem="2026-10-27")
        self.assertFalse(any("advanced" in e for e in errors),
                         "2026-10-27 이전 지문은 advanced 개수 오류 없어야 합니다")

    def test_error_when_advanced_lt_5_pool(self):
        """pool 비축분에서 advanced < 5이면 오류."""
        data = self._base_content(adv_count=2)
        errors, _ = self._write_and_check(data, stem="de-001", parent="pool")
        self.assertTrue(any("advanced" in e for e in errors),
                        "pool 비축분 advanced 2개이면 오류가 있어야 합니다")

    def test_no_error_when_advanced_gte_5_pool(self):
        """pool 비축분에서 advanced >= 5이면 오류 없다."""
        data = self._base_content(adv_count=6)
        errors, _ = self._write_and_check(data, stem="de-001", parent="pool")
        self.assertFalse(any("advanced" in e for e in errors),
                         "pool 비축분 advanced 6개면 오류 없어야 합니다")


# ── 12. catchup() 이메일 가드 ─────────────────────────────────────────────────

class DeCatchupEmailGuardTest(unittest.TestCase):
    """send_email.catchup() 이 de(email=True)에서 API 호출까지 진행하는지 검사한다."""

    def test_catchup_proceeds_for_de(self):
        """Phase 2: email=True 이므로 de 도 catchup() 이 API 호출까지 진행한다."""
        called = []
        def mock_recent(**k):
            called.append("api")
            raise SystemExit("mock")
        with patch.object(send_email, "recent_emails", mock_recent):
            try:
                send_email.catchup("de", "2026-10-28")
            except SystemExit:
                pass
        self.assertTrue(called, "de 는 email=True 이므로 catchup() 이 API 호출까지 도달해야 합니다")

    def test_catchup_does_not_return_early_for_en(self):
        """en 회귀: catchup() 이 API 호출까지 진행한다."""
        called = []
        def mock_recent(**k):
            called.append("api")
            raise SystemExit("mock")
        with patch.object(send_email, "recent_emails", mock_recent):
            try:
                send_email.catchup("en", "2026-10-28")
            except SystemExit:
                pass
        self.assertTrue(called, "en 은 catchup() 이 API 호출까지 도달해야 합니다 (회귀)")


if __name__ == "__main__":
    unittest.main()
