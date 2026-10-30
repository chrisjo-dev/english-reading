"""썸네일: 기사 사진(OpenAI) 합성과 일러스트 대체. 시안: design/article-thumb T11~T13."""
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import thumb  # noqa: E402

DAY = "2026-10-30"


class TestThumb(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        for sub in (f"en/{DAY}", "content/en"):
            (self.tmp / sub).mkdir(parents=True)
        shutil.copy(ROOT / "en" / DAY / "index.html", self.tmp / "en" / DAY / "index.html")
        shutil.copy(ROOT / "content" / "en" / f"{DAY}.json", self.tmp / "content" / "en" / f"{DAY}.json")
        self.patch = mock.patch.object(thumb, "ROOT", self.tmp)
        self.patch.start()
        self.out = self.tmp / "en" / DAY / "thumb.png"

    def tearDown(self):
        self.patch.stop()
        shutil.rmtree(self.tmp)

    def test_without_key_falls_back_to_illustration(self):
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
            thumb.build("en", DAY, "science")
        self.assertFalse(thumb.is_photo(self.out))
        self.assertEqual(Image.open(self.out).size, (1200, 630))

    def test_api_failure_falls_back_to_illustration(self):
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}), \
             mock.patch.object(thumb.urllib.request, "urlopen", side_effect=OSError("down")):
            self.assertIsNone(thumb.photo("en", DAY))
            thumb.build("en", DAY, "science")
        self.assertFalse(thumb.is_photo(self.out))

    def test_photo_is_composed_marked_and_light(self):
        pic = Image.new("RGB", (1536, 1024), (40, 90, 160))
        ImageDraw.Draw(pic).ellipse((900, 300, 1300, 700), fill=(250, 180, 60))
        thumb.build("en", DAY, "science", pic)
        im = Image.open(self.out)
        self.assertEqual(im.size, (1200, 630))
        self.assertTrue(thumb.is_photo(self.out))
        self.assertLess(self.out.stat().st_size, 600_000)
        ph = Image.open(self.out.with_name("photo.jpg"))  # 페이지 배너용 글 없는 사진
        self.assertEqual((ph.format, ph.size), ("JPEG", (1200, 630)))
        # 왼쪽은 어둡게 눌리고 오른쪽 끝은 사진 그대로
        rgb = im.convert("RGB")
        self.assertLess(sum(rgb.getpixel((20, 300))), sum((40, 90, 160)))
        self.assertGreater(sum(rgb.getpixel((1190, 20))), sum((40, 90, 160)) - 30)

    def test_existing_photo_thumb_is_not_redrawn(self):
        thumb.build("en", DAY, "science", Image.new("RGB", (1536, 1024), (40, 90, 160)))
        before = self.out.read_bytes()
        with mock.patch.object(thumb, "photo", side_effect=AssertionError("다시 그리면 안 된다")), \
             mock.patch.dict(os.environ, {"THUMB_REDRAW": ""}):
            thumb.build("en", DAY, "science")
        self.assertEqual(self.out.read_bytes(), before)

    def test_broken_content_falls_back_without_stopping(self):
        (self.tmp / "content" / "en" / f"{DAY}.json").write_text('{"sentences": [{"ko": "en 없음"}]}', encoding="utf-8")
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}), \
             mock.patch.object(thumb.urllib.request, "urlopen", side_effect=AssertionError("부르면 안 된다")):
            self.assertIsNone(thumb.photo("en", DAY))
            thumb.build("en", DAY, "science")
        self.assertFalse(thumb.is_photo(self.out))

    def test_compose_failure_falls_back_to_illustration(self):
        with mock.patch.object(thumb, "compose", side_effect=ValueError("bad")):
            thumb.build("en", DAY, "science", Image.new("RGB", (1536, 1024)))
        self.assertFalse(thumb.is_photo(self.out))
        self.assertFalse(self.out.with_name("photo.jpg").exists())

    def test_title_without_spaces_is_cut_to_width(self):
        d = ImageDraw.Draw(Image.new("RGB", (10, 10)))
        f = thumb.font("ExtraBold", 44)
        lines = thumb._wrap(d, "띄어쓰기없이아주길게이어진제목이썸네일폭을넘어가는경우에도잘려야한다", f, 640 * thumb.S)
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].endswith("…"))
        self.assertLessEqual(d.textlength(lines[0], font=f), 640 * thumb.S)

    def test_long_title_wraps_to_two_lines(self):
        d = ImageDraw.Draw(Image.new("RGB", (10, 10)))
        f = thumb.font("ExtraBold", 44)
        lines = thumb._wrap(d, "아주 긴 제목이 여러 줄로 넘어가는 경우에도 썸네일 안에서 두 줄까지만 보이고 나머지는 말줄임표로 줄인다", f, 640 * thumb.S)
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[1].endswith("…"))
        for line in lines:
            self.assertLessEqual(d.textlength(line, font=f), 640 * thumb.S)


if __name__ == "__main__":
    unittest.main()


class TestPageHero(unittest.TestCase):
    """사진이 있는 날은 날짜 페이지 상단에 글 없는 사진 배너(시안 P1), 없는 날은 예전 작은 썸네일."""

    def setUp(self):
        import subprocess
        import publish
        self.publish = publish
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "en" / DAY).mkdir(parents=True)
        orig = subprocess.run(["git", "show", f"edd0f36:en/{DAY}/index.html"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
        (self.tmp / "en" / DAY / "index.html").write_text(orig, encoding="utf-8")
        self.patch = mock.patch.object(publish, "ROOT", self.tmp)
        self.patch.start()
        self.page = self.tmp / "en" / DAY / "index.html"

    def tearDown(self):
        self.patch.stop()
        shutil.rmtree(self.tmp)

    def test_photo_day_gets_hero_instead_of_small_thumb(self):
        (self.tmp / "en" / DAY / "photo.jpg").write_bytes(b"x")
        self.publish.patch_page("en", DAY)
        once = self.page.read_text(encoding="utf-8")
        self.assertIn('<div class="hero"><img src="photo.jpg"', once)
        self.assertNotIn('<img class="thumb"', once)
        self.publish.patch_page("en", DAY)
        self.assertEqual(self.page.read_text(encoding="utf-8"), once)

    def test_day_without_photo_keeps_small_thumb(self):
        self.publish.patch_page("en", DAY)
        page = self.page.read_text(encoding="utf-8")
        self.assertIn('<img class="thumb" src="thumb.png"', page)
        self.assertNotIn('class="hero"', page)
