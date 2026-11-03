"""구역 도달 측정 스크립트(이슈 #24): 지문 페이지에만 한 번 들어가고, 여러 번 넣어도 같다."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import track  # noqa: E402


class TestTrack(unittest.TestCase):
    def test_day_page_once_and_idempotent(self):
        page = '<section class="card" id="passage"></section>\n</body></html>'
        once = track.apply(page)
        self.assertEqual(once.count('id="track-js"'), 1)
        self.assertEqual(track.apply(once), once)
        for name in ("section_view", "points_read", "#step-points"):
            self.assertIn(name, once)

    def test_other_pages_untouched(self):
        page = "<main>목록</main>\n</body></html>"
        self.assertEqual(track.apply(page), page)

    def test_published_day_page_has_script(self):
        page = (ROOT / "en" / "2026-11-03" / "index.html").read_text(encoding="utf-8")
        self.assertEqual(page.count('id="track-js"'), 1)


if __name__ == "__main__":
    unittest.main()
