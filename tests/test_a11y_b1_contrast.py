"""a11y-b1-contrast: .no 버튼 B1 크기와 WCAG AA 대비 검사."""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

# 확인할 언어별 대표 날짜
LANG_DAYS = {
    "en": "2026-11-02",
    "ja": "2026-10-27",
    "de": "2026-11-01",
}


def day_pages():
    """모든 언어의 생성된 날짜 페이지 경로 목록."""
    pages = []
    for lang in ["en", "ja", "de"]:
        lang_dir = ROOT / lang
        if not lang_dir.exists():
            continue
        for d in lang_dir.iterdir():
            if d.is_dir() and len(d.name) == 10 and d.name[4] == "-":
                p = d / "index.html"
                if p.exists():
                    pages.append(p)
    return pages


def list_pages():
    """아카이브/언어 목록 페이지 경로 목록."""
    pages = []
    for lang in ["en", "ja", "de"]:
        for sub in ("", "archive"):
            p = ROOT / lang / sub / "index.html"
            if p.exists():
                pages.append(p)
    return pages


class TestNoButtonSize(unittest.TestCase):
    """모든 날짜 페이지에서 .no 버튼이 B1 크기(32x32, radius 10)이어야 한다."""

    def test_no_button_css_32px_in_all_day_pages(self):
        pages = day_pages()
        self.assertGreater(len(pages), 0, "날짜 페이지가 없음")
        missing = []
        for p in pages:
            text = p.read_text(encoding="utf-8")
            # width/height 32px
            if "width: 32px; height: 32px" not in text:
                missing.append(str(p.relative_to(ROOT)))
        if missing:
            self.fail(f".no 32x32px 없음 ({len(missing)}개): {missing[:5]}")

    def test_no_before_hit_area_in_all_day_pages(self):
        pages = day_pages()
        self.assertGreater(len(pages), 0)
        missing = []
        for p in pages:
            text = p.read_text(encoding="utf-8")
            if ".no::before" not in text:
                missing.append(str(p.relative_to(ROOT)))
        if missing:
            self.fail(f".no::before(44px 터치 영역) 없음 ({len(missing)}개): {missing[:5]}")


class TestNoOldColors(unittest.TestCase):
    """날짜/목록 페이지에 구 컬러가 없어야 한다."""

    # CSS 변수 선언 안에만 있을 경우, 실제 사용 값으로 체크한다
    # vote CSS 안의 카테고리 칩 등 전체 범위 포함

    def _check_color(self, color_hex, pages, label):
        bad = []
        for p in pages:
            text = p.read_text(encoding="utf-8")
            if color_hex in text:
                bad.append(str(p.relative_to(ROOT)))
        if bad:
            self.fail(f"구 컬러 {color_hex}({label}) 잔류 ({len(bad)}개): {bad[:5]}")

    def test_no_8b95a1_muted_in_day_pages(self):
        self._check_color("#8b95a1", day_pages(), "muted grey")

    def test_no_8b95a1_muted_in_list_pages(self):
        self._check_color("#8b95a1", list_pages(), "muted grey")

    def test_no_3182f6_blue_in_day_pages(self):
        self._check_color("#3182f6", day_pages(), "blue link")

    def test_no_3182f6_blue_in_list_pages(self):
        self._check_color("#3182f6", list_pages(), "blue link")

    def test_no_e89a14_culture_in_day_pages(self):
        self._check_color("#e89a14", day_pages(), "culture text")

    def test_no_e89a14_culture_in_list_pages(self):
        self._check_color("#e89a14", list_pages(), "culture text")


class TestNewColors(unittest.TestCase):
    """새 컬러가 실제로 적용됐는지 대표 페이지로 확인한다."""

    def _page(self, lang, day):
        p = ROOT / lang / day / "index.html"
        if not p.exists():
            self.skipTest(f"페이지 없음: {lang}/{day}")
        return p.read_text(encoding="utf-8")

    def test_muted_var_updated(self):
        page = self._page("en", LANG_DAYS["en"])
        self.assertIn("--muted: #6b7684", page)
        self.assertNotIn("--muted: #8b95a1", page)

    def test_blue_var_updated(self):
        page = self._page("en", LANG_DAYS["en"])
        self.assertIn("--blue: #1b64da", page)
        self.assertNotIn("--blue: #3182f6", page)

    def test_blue_press_var_updated(self):
        page = self._page("en", LANG_DAYS["en"])
        self.assertIn("--blue-press: #1550b8", page)

    def test_no_button_32x32(self):
        page = self._page("en", LANG_DAYS["en"])
        self.assertIn("width: 32px; height: 32px", page)
        self.assertIn("border-radius: 10px", page)
        self.assertIn(".no::before { content: ''; position: absolute; inset: -6px; }", page)


class TestIdempotent(unittest.TestCase):
    """patch_page 두 번 실행 결과가 같아야 한다."""

    def test_patch_page_is_idempotent(self):
        sys.path.insert(0, str(ROOT / "tools"))
        import publish  # noqa: E402
        lang, day = "en", LANG_DAYS["en"]
        p = ROOT / lang / day / "index.html"
        if not p.exists():
            self.skipTest("페이지 없음")
        # 실제 페이지를 고치지 않도록 임시 폴더 사본에서 실행한다
        import shutil, tempfile  # noqa: E401
        tmp = Path(tempfile.mkdtemp())
        orig = publish.ROOT
        try:
            (tmp / lang / day).mkdir(parents=True)
            shutil.copy(p, tmp / lang / day / "index.html")
            (tmp / "content").symlink_to(ROOT / "content")
            p = tmp / lang / day / "index.html"
            publish.ROOT = tmp
            publish.patch_page(lang, day)
            first = p.read_text(encoding="utf-8")
            publish.patch_page(lang, day)
            second = p.read_text(encoding="utf-8")
        finally:
            publish.ROOT = orig
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertEqual(first, second, "patch_page 두 번 실행 결과가 다름")


if __name__ == "__main__":
    unittest.main()
