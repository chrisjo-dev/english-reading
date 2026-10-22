"""플레이어 바 교체 검증: #slow 버튼이 없고 #pbar 마크업이 있는지 확인.

실행: python3 -m pytest -q tests/test_pbar.py
"""
import sys
import tempfile
import json
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
import render  # noqa: E402
import publish  # noqa: E402


def make_day(tmp_root, lang, day):
    """최소 콘텐츠로 day 페이지를 렌더링하고 HTML 문자열을 반환한다."""
    content_dir = tmp_root / "content" / lang
    content_dir.mkdir(parents=True, exist_ok=True)
    if lang == "en":
        c = {
            "date": day,
            "category": "tech",
            "topic": "테스트",
            "title_ko": "테스트 제목",
            "headline": "Test headline",
            "chips": ["3문장"],
            "sentences": [
                {"en": "This is a **test** sentence.", "b2": False,
                 "chunks": [["This is", "이것은"], ["a **test** sentence.", "테스트 문장이에요."]]},
                {"en": "Another sentence.", "b2": False,
                 "chunks": [["Another sentence.", "다른 문장이에요."]]},
            ],
            "words": [["test", "테스트"]],
            "points": [{"title": "포인트", "body": "설명"}],
            "answers": ["해석1", "해석2"],
            "advanced": [],
            "source": None,
        }
    else:
        c = {
            "date": day,
            "category": "tech",
            "topic": "テスト",
            "title_ko": "테스트 제목",
            "headline": "テストの見出し",
            "chips": ["3文"],
            "sentences": [
                {"en": "これはテストです。", "b2": False},
                {"en": "もう一つの文です。", "b2": False},
            ],
            "words": [["テスト", "테스트"]],
            "points": [{"title": "ポイント", "body": "説明"}],
            "answers": ["해석1", "해석2"],
            "advanced": [],
            "source": None,
        }
    (content_dir / f"{day}.json").write_text(json.dumps(c, ensure_ascii=False))

    out_dir = tmp_root / lang / day
    out_dir.mkdir(parents=True, exist_ok=True)

    # render.render uses REPO paths internally; render to a temp root would require
    # monkeypatching. Instead test the actual rendered pages that already exist.
    return None


class PbarMarkupTest(unittest.TestCase):
    """실제 렌더링된 대표 페이지에서 마크업을 확인한다."""

    def _html(self, lang, day):
        path = REPO / lang / day / "index.html"
        self.assertTrue(path.exists(), f"{path} 가 없어요")
        return path.read_text(encoding="utf-8")

    def test_en_no_slow_button(self):
        html = self._html("en", "2026-10-22")
        self.assertNotIn('id="slow"', html, "en 페이지에 #slow 버튼이 남아 있어요")

    def test_en_has_pbar(self):
        html = self._html("en", "2026-10-22")
        self.assertIn('id="pbar"', html, "en 페이지에 #pbar 가 없어요")
        self.assertIn('id="pbar-sp"', html, "en 페이지에 속도 버튼(#pbar-sp)이 없어요")
        self.assertIn('id="pbar-pp"', html, "en 페이지에 재생/일시정지 버튼(#pbar-pp)이 없어요")

    def test_ja_no_slow_button(self):
        html = self._html("ja", "2026-10-22")
        self.assertNotIn('id="slow"', html, "ja 페이지에 #slow 버튼이 남아 있어요")

    def test_ja_has_pbar(self):
        html = self._html("ja", "2026-10-22")
        self.assertIn('id="pbar"', html, "ja 페이지에 #pbar 가 없어요")
        self.assertIn('id="pbar-sp"', html, "ja 페이지에 속도 버튼(#pbar-sp)이 없어요")

    def test_en_pbar_speed_cycles(self):
        """SPEEDS 배열과 사이클 로직이 템플릿에 포함되었는지 확인한다."""
        html = self._html("en", "2026-10-22")
        self.assertIn("SPEEDS", html, "SPEEDS 배열이 없어요")
        self.assertIn("speed_change", html, "speed_change GA 이벤트가 없어요")
        self.assertIn("read_speed", html, "localStorage read_speed 키가 없어요")

    def test_en_tools_4_buttons(self):
        """en 도구 줄에 slow 버튼 대신 4개 버튼(전체 듣기, 지문 복사, 해석 보기, 끊어 읽기)이 있어야 한다."""
        html = self._html("en", "2026-10-22")
        self.assertNotIn("느리게", html, "en 페이지에 '느리게' 텍스트가 남아 있어요")
        # 네 버튼의 id 확인
        for btn_id in ("play", "copy", "kobtn", "chunkbtn"):
            self.assertIn(f'id="{btn_id}"', html, f"en 페이지에 #{btn_id} 가 없어요")

    def test_ja_tools_no_slow(self):
        """ja 도구 줄에 slow 버튼이 없어야 한다."""
        html = self._html("ja", "2026-10-22")
        self.assertNotIn("느리게", html, "ja 페이지에 '느리게' 텍스트가 남아 있어요")


if __name__ == "__main__":
    unittest.main()
