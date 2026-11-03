"""2026-11-03 사용자 지적 재발 방지: 뜻풀이, 제목, 일본어 출처, AI 서비스 이름."""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import check_content  # noqa: E402


def run(lang, day, c):
    return check_content.check_style(c, ROOT / "content" / lang / f"{day}.json")


class TestStyleGuard(unittest.TestCase):
    def test_ja_kana_in_meaning_is_error(self):
        errors, _ = run("ja", "2026-11-05", {"words": [["7つ", "일곱 개 (ななつ)"]]})
        self.assertTrue(errors)
        errors, _ = run("ja", "2026-11-05", {"words": [["{平和|へいわ}", "평화"]]})
        self.assertFalse(errors)

    def test_paraphrased_meaning_warns(self):
        _, w = run("ja", "2026-11-05", {"words": [["{平和|へいわ}", "전쟁이 없고 평온함"]], "source": {"title": "t", "url": "u"}})
        self.assertTrue(any("풀어 쓴" in x for x in w))
        _, w = run("de", "2026-11-05", {"words": [["Pfand", "(빈 병) 보증금 (중성 das)"]], "advanced": [{"word": "Einwegflasche", "meaning": "일회용 병"}]})
        self.assertFalse(w)

    def test_long_title_warns(self):
        _, w = run("en", "2026-11-05", {"title_ko": "카메라를 시험하려고 일부러 만드는 안개와 비"})
        self.assertTrue(any("title_ko" in x for x in w))
        _, w = run("en", "2026-11-05", {"title_ko": "일부러 만든 안개 속 카메라 시험"})
        self.assertFalse(w)

    def test_ja_source_days(self):
        _, w = run("ja", "2026-11-04", {"source": None})  # 수요일
        self.assertTrue(any("출처" in x for x in w))
        _, w = run("ja", "2026-11-05", {"source": None})  # 목요일
        self.assertFalse(w)

    def test_old_days_not_warned(self):
        _, w = run("en", "2026-10-24", {"title_ko": "40년 동안 마당에서 배를 만든 할아버지 이야기 모음"})
        self.assertFalse(w)


class TestNoModelNames(unittest.TestCase):
    def test_sources_and_pages_do_not_name_ai_services(self):
        files = [ROOT / "tools" / "template.html", ROOT / "index.html"]
        files += list((ROOT / "landing" / "src").rglob("*.ts*"))
        files += sorted(ROOT.glob("*/20??-??-??/index.html"))
        hits = [str(f.relative_to(ROOT)) for f in files if re.search(r"ChatGPT|Claude", f.read_text(encoding="utf-8"))]
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
