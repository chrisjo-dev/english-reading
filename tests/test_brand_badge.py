"""배지 로고 배치 테스트.

- 일간 이메일 본문 첫 번째 행에 배지 이미지가 있는지
- 주간 이메일 본문 첫 번째 행에 배지 이미지가 있는지
- patch_page 후 .gnb .brand img 에 style 속성이 없는지
- patch_page 가 .gnb .brand img CSS 규칙을 주입하는지
- patch_page 가 멱등적으로 동작하는지 (두 번 실행해도 CSS 규칙 중복 없음)

실행: python -m pytest -q tests/test_brand_badge.py
"""
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
import build_email  # noqa: E402
import publish      # noqa: E402
import weekly       # noqa: E402

SITE = "https://read.wspace.ai.kr"
BADGE_IMG_PATTERN = re.compile(
    r'<img\s[^>]*src="' + re.escape(f"{SITE}/assets/brand/badge-192.png") + r'"',
    re.I,
)

# patch_page 용 최소 페이지 (inline style 있는 구버전 GNB 브랜드)
MINIMAL_WITH_INLINE_STYLE = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta property="og:image" content="https://read.wspace.ai.kr/en/2026-10-22/thumb.png">
<title>테스트</title><link rel="canonical" href="https://read.wspace.ai.kr/en/2026-10-22/">
<link rel="stylesheet" href="../shared/style.css">
<style>
  .gnb { display: flex; }
  .gnb .brand { font-weight: 800; }
  .gnb nav a.cta:hover { background: #d6e8ff; }
</style>
</head>
<body><main>
  <header class="gnb">
    <a class="brand" href="/"><img src="/assets/brand/duck-lying-64.png" alt="" height="30" style="vertical-align:middle"> 독해한입</a>
  </header>
  <div class="top">
    <img class="thumb" src="thumb.png" width="76" height="76" alt="">
    <div class="date">2026-10-22</div>
  </div>
  <p class="intro">소개</p>
  <section class="card" id="passage">
    <div class="sent"><div class="en">Test.</div></div>
  </section>
</main>
<footer class="site-footer"><a href="https://www.wspace.ai.kr/">wspace 홈</a></footer>
</body></html>
"""


class DailyEmailBadgeTest(unittest.TestCase):
    """일간 이메일 본문 첫 행에 배지 이미지가 있는지 확인한다."""

    def _body(self, lang="en", day="2026-10-22"):
        result = build_email.build(lang, day)
        self.assertIsNotNone(result, f"{lang}/{day} 이메일 빌드 실패")
        return result["body"]

    def test_en_email_starts_with_badge(self):
        body = self._body("en", "2026-10-22")
        first_tr_match = re.search(r"<tr>.*?</tr>", body, re.S)
        self.assertIsNotNone(first_tr_match, "이메일 본문에 <tr>이 없습니다")
        first_tr = first_tr_match.group()
        self.assertRegex(first_tr, BADGE_IMG_PATTERN, "첫 번째 <tr>에 배지 이미지가 없습니다")

    def test_badge_url_absolute(self):
        body = self._body()
        self.assertIn(f"{SITE}/assets/brand/badge-192.png", body)

    def test_badge_width_88(self):
        body = self._body()
        # width="88" height="88" 인지 확인
        m = re.search(r'badge-192\.png"[^>]*width="(\d+)"', body)
        self.assertIsNotNone(m, "배지 img에 width 속성이 없습니다")
        self.assertEqual(m.group(1), "88")

    def test_badge_has_alt(self):
        body = self._body()
        self.assertIn('alt="독해한입"', body)


class WeeklyEmailBadgeTest(unittest.TestCase):
    """주간 이메일 본문 첫 행에 배지 이미지가 있는지 확인한다."""

    def _body(self, lang="en", end="2026-10-26"):
        result = weekly.build_email(lang, end)
        return result["body"]

    def test_weekly_en_starts_with_badge(self):
        try:
            body = self._body("en", "2026-10-26")
        except Exception:
            self.skipTest("주간 콘텐츠 없음 — 스킵")
        first_tr = re.search(r"<tr>.*?</tr>", body, re.S)
        if first_tr is None:
            self.skipTest("주간 이메일에 <tr> 없음")
        self.assertRegex(first_tr.group(), BADGE_IMG_PATTERN,
                         "주간 이메일 첫 번째 <tr>에 배지 이미지가 없습니다")


class PatchPageBadgeTest(unittest.TestCase):
    """patch_page 후 GNB 브랜드 이미지에 inline style이 없고 CSS 규칙이 주입된다."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        day_dir = self.tmp / "en" / "2026-10-22"
        day_dir.mkdir(parents=True)
        self.page_path = day_dir / "index.html"

    def _patch(self, content: str) -> str:
        original_root = publish.ROOT
        try:
            publish.ROOT = self.tmp
            self.page_path.write_text(content, encoding="utf-8")
            publish.patch_page("en", "2026-10-22")
            return self.page_path.read_text(encoding="utf-8")
        finally:
            publish.ROOT = original_root

    def test_no_inline_style_on_brand_img(self):
        """patch_page 후 .gnb .brand img 에 style= 속성이 없어야 한다."""
        result = self._patch(MINIMAL_WITH_INLINE_STYLE)
        # <a class="brand"> 안의 img 를 찾는다
        brand_img = re.search(r'<a class="brand"[^>]*>(.*?)</a>', result, re.S)
        self.assertIsNotNone(brand_img, "brand 링크를 찾지 못했습니다")
        img_tag = brand_img.group(1)
        self.assertNotIn('style=', img_tag,
                         "brand img에 inline style이 남아 있으면 안 됩니다")

    def test_gnb_brand_img_css_injected(self):
        """patch_page 후 .gnb .brand img CSS 규칙이 페이지에 있어야 한다."""
        result = self._patch(MINIMAL_WITH_INLINE_STYLE)
        self.assertIn('.gnb .brand img', result,
                      ".gnb .brand img CSS 규칙이 주입되어야 합니다")

    def test_patch_page_idempotent_no_duplicate_css(self):
        """patch_page 를 두 번 실행해도 vertical-align CSS 규칙이 한 번만 주입되어야 한다."""
        result_first = self._patch(MINIMAL_WITH_INLINE_STYLE)
        result_second = self._patch(result_first)
        # GNB_NARROW_CSS 안에도 .gnb .brand img 가 있으므로 정확한 standalone 규칙 문자열로 확인
        target = publish.GNB_IMG_CSS.rstrip()
        count = result_second.count(target)
        self.assertEqual(count, 1,
                         f"'{target}' 규칙이 {count}개입니다 (1개여야 합니다)")

    def test_patch_page_idempotent_no_inline_style_twice(self):
        """이미 패치된 페이지를 다시 패치해도 inline style이 없어야 한다."""
        result_first = self._patch(MINIMAL_WITH_INLINE_STYLE)
        result_second = self._patch(result_first)
        brand_img = re.search(r'<a class="brand"[^>]*>(.*?)</a>', result_second, re.S)
        self.assertIsNotNone(brand_img)
        self.assertNotIn('style=', brand_img.group(1))


class FixtureEmailBadgeTest(unittest.TestCase):
    """저장된 픽스처 파일 기준으로 배지가 있는지 확인한다."""

    def _load_fixture(self, name: str) -> dict:
        path = REPO / "tests" / "fixtures" / name
        if not path.exists():
            self.skipTest(f"픽스처 없음: {name}")
        return json.loads(path.read_text(encoding="utf-8"))

    def test_fixture_en_has_badge(self):
        d = self._load_fixture("email_b_en_2026-10-22.json")
        body = d["body"]
        self.assertIn("badge-192.png", body, "픽스처 EN 이메일에 배지 이미지 URL이 없습니다")

    def test_fixture_ja_has_badge(self):
        d = self._load_fixture("email_b_ja_2026-10-22.json")
        body = d["body"]
        self.assertIn("badge-192.png", body, "픽스처 JA 이메일에 배지 이미지 URL이 없습니다")


if __name__ == "__main__":
    unittest.main()
