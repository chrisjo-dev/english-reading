"""site-improve 브랜치 변경 사항 단위 테스트.

Task 1: 언어별 localStorage 수준 저장
Task 2: thumb-sq.jpg 생성 및 목록 사용
Task 3: SEO/메타 - 아카이브 설명, 지문 설명, sitemap lastmod, 주간 복습 제목
Task 4: 404 페이지 독일어 링크
Task 5: 퀴즈 카운터 즉시 감소
"""
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import publish  # noqa: E402
import thumb    # noqa: E402
import weekly   # noqa: E402
import langs    # noqa: E402


# ── Task 4: 404 페이지 독일어 링크 ──────────────────────────────────────────

class Test404DeLinkTask4(unittest.TestCase):
    def setUp(self):
        self.page = (ROOT / "404.html").read_text(encoding="utf-8")

    def test_de_link_present(self):
        self.assertIn('<a href="/de/">독일어 지문 목록</a>', self.page)

    def test_en_link_still_present(self):
        self.assertIn('<a href="/en/">영어 지문 목록</a>', self.page)

    def test_ja_link_still_present(self):
        self.assertIn('<a href="/ja/">일본어 지문 목록</a>', self.page)


# ── Task 5: 퀴즈 카운터 즉시 감소 ──────────────────────────────────────────

class TestDrillCounterTask5(unittest.TestCase):
    def setUp(self):
        self.js = (ROOT / "assets" / "drill.js").read_text(encoding="utf-8")

    def test_counter_subtracts_answered_item(self):
        """prog()는 이미 답한 큐 첫 항목(it0.pick != null)을 '남은 문제'에서 뺀다."""
        self.assertIn("it0 && it0.pick != null ? 1 : 0", self.js)

    def test_counter_uses_queue_length_minus_answered(self):
        """남은 문제 = queue.length - (맨 앞 항목이 이미 답했으면 1)"""
        self.assertIn("S.queue.length - (it0 && it0.pick != null ? 1 : 0)", self.js)

    def test_no_bare_queue_length_in_lc(self):
        """'남은 문제 ' + S.queue.length 형태가 남아 있으면 안 된다."""
        self.assertNotIn("'남은 문제 ' + S.queue.length", self.js)


# ── Task 1: 언어별 localStorage 수준 저장 ───────────────────────────────────

class TestLevelStorageTask1(unittest.TestCase):
    def setUp(self):
        self.tmpl = (ROOT / "tools" / "template.html").read_text(encoding="utf-8")

    def test_head_script_uses_per_lang_key(self):
        """head script 에서 read_level:+_lc 형식의 키를 쓴다."""
        self.assertIn("read_level:'+_lc", self.tmpl)

    def test_head_script_migrates_old_en_key(self):
        """영어 이전 키(read_level) 마이그레이션이 head script 에 있다."""
        self.assertIn("localStorage.getItem('read_level')", self.tmpl)
        self.assertIn("localStorage.setItem('read_level:en'", self.tmpl)
        self.assertIn("localStorage.removeItem('read_level')", self.tmpl)

    def test_body_url_param_uses_per_lang_key(self):
        """body script URL 파라미터 처리도 read_level:+_gaLang 형식을 쓴다."""
        self.assertIn("localStorage.setItem('read_level:' + _gaLang, lp)", self.tmpl)

    def test_switch_level_uses_per_lang_key(self):
        """switchLevel 함수도 read_level:+_gaLang 형식을 쓴다."""
        self.assertIn("localStorage.setItem('read_level:' + _gaLang, to)", self.tmpl)

    def test_no_bare_set_read_level(self):
        """localStorage.setItem('read_level', ...) 형태(콜론 없는 기존 키)가 template.html 에 없어야 한다."""
        self.assertNotIn("localStorage.setItem('read_level',", self.tmpl)
        self.assertNotIn('localStorage.setItem("read_level",', self.tmpl)


# ── Task 2: thumb-sq.jpg 생성 및 목록 사용 ─────────────────────────────────

DAY = "2026-10-30"


class TestThumbSqGenerationTask2a(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        for sub in (f"en/{DAY}", "content/en"):
            (self.tmp / sub).mkdir(parents=True)
        shutil.copy(ROOT / "en" / DAY / "index.html", self.tmp / "en" / DAY / "index.html")
        shutil.copy(ROOT / "content" / "en" / f"{DAY}.json", self.tmp / "content" / "en" / f"{DAY}.json")
        self.patch = mock.patch.object(thumb, "ROOT", self.tmp)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        shutil.rmtree(self.tmp)

    def test_photo_day_generates_thumb_sq(self):
        """사진이 있는 날은 thumb-sq.jpg(112×112)도 생성한다."""
        pic = Image.new("RGB", (1200, 630), (40, 90, 160))
        thumb.build("en", DAY, "science", pic)
        sq = self.tmp / "en" / DAY / "thumb-sq.jpg"
        self.assertTrue(sq.exists(), "thumb-sq.jpg 가 생성되어야 합니다")
        im = Image.open(sq)
        self.assertEqual(im.size, (112, 112))
        self.assertEqual(im.format, "JPEG")

    def test_illustration_day_does_not_generate_thumb_sq(self):
        """일러스트 날(사진 없음)은 thumb-sq.jpg 를 만들지 않는다."""
        with mock.patch.dict(__import__('os').environ, {"OPENAI_API_KEY": ""}):
            thumb.build("en", DAY, "science")
        sq = self.tmp / "en" / DAY / "thumb-sq.jpg"
        self.assertFalse(sq.exists(), "일러스트 날에는 thumb-sq.jpg 가 없어야 합니다")


class TestRebuildListsThumbSqTask2a(unittest.TestCase):
    def setUp(self):
        import json
        import publish as pub
        self.pub = pub
        self.tmp = Path(tempfile.mkdtemp())
        # 최소 구조: en/YYYY-MM-DD/index.html + content JSON
        self.day = "2026-10-30"
        day_dir = self.tmp / "en" / self.day
        day_dir.mkdir(parents=True)
        shutil.copy(ROOT / "en" / self.day / "index.html", day_dir / "index.html")
        content_dir = self.tmp / "content" / "en"
        content_dir.mkdir(parents=True)
        shutil.copy(ROOT / "content" / "en" / f"{self.day}.json", content_dir / f"{self.day}.json")
        self.patch = mock.patch.object(pub, "ROOT", self.tmp)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        shutil.rmtree(self.tmp)

    def test_thumb_sq_preferred_over_photo(self):
        """thumb-sq.jpg 가 있으면 photo.jpg 대신 사용한다."""
        (self.tmp / "en" / self.day / "thumb-sq.jpg").write_bytes(b"x")
        (self.tmp / "en" / self.day / "photo.jpg").write_bytes(b"x")
        self.pub.rebuild_lists("en")
        hub = (self.tmp / "en" / "index.html").read_text(encoding="utf-8")
        self.assertIn("thumb-sq.jpg", hub)
        self.assertNotIn(f"{self.day}/photo.jpg", hub)

    def test_photo_fallback_when_no_thumb_sq(self):
        """thumb-sq.jpg 없고 photo.jpg 만 있으면 photo.jpg 를 쓴다."""
        (self.tmp / "en" / self.day / "photo.jpg").write_bytes(b"x")
        self.pub.rebuild_lists("en")
        hub = (self.tmp / "en" / "index.html").read_text(encoding="utf-8")
        self.assertIn("photo.jpg", hub)

    def test_thumb_png_fallback_when_no_photo(self):
        """사진이 전혀 없으면 thumb.png 를 쓴다."""
        self.pub.rebuild_lists("en")
        hub = (self.tmp / "en" / "index.html").read_text(encoding="utf-8")
        self.assertIn("thumb.png", hub)


# ── Task 3a: 아카이브/허브 메타 설명 ────────────────────────────────────────

class TestArchiveMetaDescTask3a(unittest.TestCase):
    def setUp(self):
        import publish as pub
        self.pub = pub
        self.tmp = Path(tempfile.mkdtemp())
        self.day = "2026-10-30"
        day_dir = self.tmp / "en" / self.day
        day_dir.mkdir(parents=True)
        shutil.copy(ROOT / "en" / self.day / "index.html", day_dir / "index.html")
        content_dir = self.tmp / "content" / "en"
        content_dir.mkdir(parents=True)
        shutil.copy(ROOT / "content" / "en" / f"{self.day}.json", content_dir / f"{self.day}.json")
        self.patch = mock.patch.object(pub, "ROOT", self.tmp)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        shutil.rmtree(self.tmp)

    def test_hub_has_meta_description(self):
        """언어 허브 페이지(/en/)에 meta description 이 있다."""
        self.pub.rebuild_lists("en")
        hub = (self.tmp / "en" / "index.html").read_text(encoding="utf-8")
        self.assertIn('<meta name="description"', hub)
        desc_m = re.search(r'<meta name="description" content="([^"]*)"', hub)
        self.assertIsNotNone(desc_m)
        self.assertGreater(len(desc_m.group(1)), 10)

    def test_archive_has_meta_description(self):
        """아카이브 페이지(/en/archive/)에도 meta description 이 있다."""
        self.pub.rebuild_lists("en")
        archive = (self.tmp / "en" / "archive" / "index.html").read_text(encoding="utf-8")
        self.assertIn('<meta name="description"', archive)


# ── Task 3b: 지문 페이지 메타 설명에 주제 포함 ──────────────────────────────

class TestPassageMetaDescTask3b(unittest.TestCase):
    OLD = "2026-10-29"

    def setUp(self):
        import publish as pub
        self.pub = pub
        self.tmp = Path(tempfile.mkdtemp())
        day_dir = self.tmp / "en" / self.OLD
        day_dir.mkdir(parents=True)
        shutil.copy(ROOT / "en" / self.OLD / "index.html", day_dir / "index.html")
        self.patch = mock.patch.object(pub, "ROOT", self.tmp)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        shutil.rmtree(self.tmp)

    def _topic_from_page(self):
        page = (self.tmp / "en" / self.OLD / "index.html").read_text(encoding="utf-8")
        m = re.search(r"<h1>.*?<em>(.*?)</em>", page, re.S)
        return m.group(1).strip() if m else None

    def test_description_includes_topic(self):
        """지문 페이지 meta description 에 주제가 포함된다."""
        topic = self._topic_from_page()
        self.pub.patch_page("en", self.OLD)
        page = (self.tmp / "en" / self.OLD / "index.html").read_text(encoding="utf-8")
        desc_m = re.search(r'<meta name="description" content="([^"]*)"', page)
        self.assertIsNotNone(desc_m)
        if topic:
            self.assertIn(topic, desc_m.group(1))

    def test_description_idempotent(self):
        """patch_page 를 두 번 실행해도 description 이 달라지지 않는다."""
        self.pub.patch_page("en", self.OLD)
        after_first = (self.tmp / "en" / self.OLD / "index.html").read_text(encoding="utf-8")
        self.pub.patch_page("en", self.OLD)
        after_second = (self.tmp / "en" / self.OLD / "index.html").read_text(encoding="utf-8")
        desc1 = re.search(r'<meta name="description" content="([^"]*)"', after_first)
        desc2 = re.search(r'<meta name="description" content="([^"]*)"', after_second)
        self.assertEqual(desc1.group(1) if desc1 else "", desc2.group(1) if desc2 else "")


# ── Task 3d: render.py lang 속성 ────────────────────────────────────────────

class TestRenderLangAttrTask3d(unittest.TestCase):
    def setUp(self):
        import render as rnd
        self.rnd = rnd
        if not (ROOT / "en" / "2026-10-30" / "index.html").exists():
            self.skipTest("2026-10-30 페이지 없음")
        self.tmp = Path(tempfile.mkdtemp())
        for sub in ("en/2026-10-30", "content/en"):
            (self.tmp / sub).mkdir(parents=True)
        shutil.copy(ROOT / "en" / "2026-10-30" / "index.html", self.tmp / "en" / "2026-10-30" / "index.html")
        shutil.copy(ROOT / "content" / "en" / "2026-10-30.json", self.tmp / "content" / "en" / "2026-10-30.json")
        self.orig = rnd.ROOT
        rnd.ROOT = self.tmp

    def tearDown(self):
        self.rnd.ROOT = self.orig
        shutil.rmtree(self.tmp)

    def test_en_div_has_lang_attribute(self):
        """render 결과 .en div 에 lang 속성이 붙는다."""
        out, _, _ = self.rnd.render("en", "2026-10-30")
        page = out.read_text(encoding="utf-8")
        self.assertIn('<div class="en" lang="en">', page)

    def test_word_span_has_lang_attribute(self):
        """단어 .w span 에 lang 속성이 붙는다."""
        out, _, _ = self.rnd.render("en", "2026-10-30")
        page = out.read_text(encoding="utf-8")
        self.assertRegex(page, r'<span class="w" lang="en">')


# ── Task 3e: sitemap lastmod 및 아카이브 포함 ───────────────────────────────

class TestSitemapLastmodTask3e(unittest.TestCase):
    def setUp(self):
        import publish as pub
        self.pub = pub
        self.tmp = Path(tempfile.mkdtemp())
        self.day = "2026-10-30"
        day_dir = self.tmp / "en" / self.day
        day_dir.mkdir(parents=True)
        shutil.copy(ROOT / "en" / self.day / "index.html", day_dir / "index.html")
        content_dir = self.tmp / "content" / "en"
        content_dir.mkdir(parents=True)
        shutil.copy(ROOT / "content" / "en" / f"{self.day}.json", content_dir / f"{self.day}.json")
        self.patch = mock.patch.object(pub, "ROOT", self.tmp)
        self.patch.start()
        self.pub.write_sitemap()
        self.sitemap = (self.tmp / "sitemap.xml").read_text(encoding="utf-8")

    def tearDown(self):
        self.patch.stop()
        shutil.rmtree(self.tmp)

    def test_day_url_has_lastmod(self):
        """날짜 페이지 URL 에 lastmod 태그가 있다."""
        self.assertIn(f"/{self.day}/<", self.sitemap)
        m = re.search(r'<url><loc>[^<]*/en/' + self.day + r'/</loc><lastmod>([^<]+)</lastmod></url>', self.sitemap)
        self.assertIsNotNone(m, "lastmod 태그가 없습니다")
        self.assertEqual(m.group(1), self.day)

    def test_archive_url_included(self):
        """아카이브 URL(/en/archive/)이 사이트맵에 포함된다."""
        self.assertIn("/en/archive/", self.sitemap)

    def test_lang_hub_has_lastmod(self):
        """언어 허브 URL 에도 lastmod 가 있다."""
        m = re.search(r'<url><loc>[^<]*/en/</loc><lastmod>([^<]+)</lastmod></url>', self.sitemap)
        self.assertIsNotNone(m, "언어 허브 lastmod 없음")


# ── Task 3c: 주간 복습 제목 고유화 및 canonical ─────────────────────────────

class TestWeeklyPageTitleTask3c(unittest.TestCase):
    END = "2026-10-26"  # 실제 내용이 있는 날짜

    def setUp(self):
        if not (ROOT / "content" / "en" / f"{self.END}.json").exists():
            self.skipTest(f"content/en/{self.END}.json 없음")
        self.tmp = Path(tempfile.mkdtemp())
        # weekly.py 가 ROOT/content 를 읽으므로 실제 ROOT 사용
        import weekly as wk
        self.wk = wk
        self.orig = wk.ROOT
        wk.ROOT = ROOT  # 실제 콘텐츠 사용

    def tearDown(self):
        self.wk.ROOT = self.orig
        shutil.rmtree(self.tmp)

    def test_title_includes_span(self):
        """주간 복습 제목에 날짜 범위(__SPAN__)가 포함된다."""
        out = self.wk.build_page("en", self.END)
        page = out.read_text(encoding="utf-8")
        m = re.search(r"<title>([^<]+)</title>", page)
        self.assertIsNotNone(m)
        # 날짜 형식 "X월 X일" 이 제목에 들어가야 한다
        self.assertRegex(m.group(1), r"\d+월 \d+일")

    def test_title_includes_lang_name(self):
        """주간 복습 제목에 언어 이름이 포함된다."""
        out = self.wk.build_page("en", self.END)
        page = out.read_text(encoding="utf-8")
        m = re.search(r"<title>([^<]+)</title>", page)
        self.assertIsNotNone(m)
        self.assertIn("영어", m.group(1))

    def test_canonical_present(self):
        """주간 복습 페이지에 canonical 링크가 있다."""
        out = self.wk.build_page("en", self.END)
        page = out.read_text(encoding="utf-8")
        self.assertRegex(page, r'<link rel="canonical" href="https://[^"]+/review/')


if __name__ == "__main__":
    unittest.main()


class TestOldPagesLevelKey(unittest.TestCase):
    """지난 페이지도 수준을 언어별 키로 저장한다(공용 read_level 에 쓰지 않는다)."""

    def test_all_pages_use_per_language_key(self):
        for f in sorted(Path(__file__).resolve().parent.parent.glob("*/20??-??-??/index.html")):
            s = f.read_text(encoding="utf-8")
            self.assertNotIn("setItem('read_level',", s, str(f))
            self.assertIn("var _lc=location", s, str(f))
