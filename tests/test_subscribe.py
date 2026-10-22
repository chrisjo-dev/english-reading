"""구독 카드(sub_html) 단위 테스트와 patch_page 교체/멱등성 테스트.

실행: python -m pytest -q tests/test_subscribe.py
"""
import re
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
import publish  # noqa: E402


# 최소한의 day page HTML — OG/thumb/footer 는 이미 있다고 표시해 patch_page 의 카드 삽입 로직만 테스트한다.
MINIMAL_PAGE = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta property="og:image" content="https://read.wspace.ai.kr/en/2026-10-22/thumb.png">
<title>테스트</title><link rel="canonical" href="https://read.wspace.ai.kr/en/2026-10-22/"><link rel="stylesheet" href="../shared/style.css">
<style>
  .gnb { display: flex; }
</style>
</head>
<body>
<main>
  <header class="gnb"><a>홈</a></header>
  <div class="top">
    <img class="thumb" src="thumb.png" width="76" height="76" alt="">
    <div class="date">2026-10-22</div>
  </div>
  <p class="intro">소개</p>

  <section class="card" id="passage">
    <div class="sent"><div class="en">Test sentence.</div><div class="ko" hidden>테스트 문장.</div></div>
  </section>
</main>
<footer class="site-footer"><a href="https://www.wspace.ai.kr/">wspace 홈</a></footer>
</body></html>
"""

# 이전 버전 카드 (data-v="2" 없음)
OLD_CARD = (
    '  <section class="card sub" id="subscribe">\n'
    '    <h2>매일 아침 영어 지문 받기</h2>\n'
    '    <p>새 영어 지문이 올라오면 아침에 메일로 보내 드려요.</p>\n'
    '    <form action="https://buttondown.com/api/emails/embed-subscribe/english-reading" method="post" target="_blank">\n'
    '      <input type="hidden" name="metadata__lang" value="en">\n'
    '      <input type="email" name="email" required placeholder="이메일 주소" autocomplete="email" aria-label="이메일 주소">\n'
    '      <button type="submit">구독하기</button>\n'
    '    </form>\n'
    '    <p class="note">지금은 이메일 주소 하나로 한 언어만 구독할 수 있어요.</p>\n'
    '  </section>\n'
)

PAGE_WITH_OLD_CARD = MINIMAL_PAGE.replace("</main>", OLD_CARD + "</main>").replace(
    "  .gnb {",
    "  .sub { scroll-margin-top: 84px; }\n  .sub h2 { margin-bottom: 4px; }\n  .sub .note { margin: 10px 0 0; }\n  .gnb {",
)


class SubHtmlEnTest(unittest.TestCase):
    """영어 sub_html 에 수준 선택 라디오가 있는지 확인한다."""

    def setUp(self):
        self.html = publish.sub_html("en")

    def test_has_two_radios(self):
        radios = re.findall(r'<input[^>]+type=["\']radio["\']', self.html)
        self.assertEqual(len(radios), 2, "영어 구독 카드에 라디오 입력이 2개여야 합니다")

    def test_has_value_a(self):
        self.assertIn('value="a"', self.html, "기초(a) 라디오 값이 있어야 합니다")

    def test_has_value_b(self):
        self.assertIn('value="b"', self.html, "중급(b) 라디오 값이 있어야 합니다")

    def test_b_is_checked_by_default(self):
        # 중급(b) 라디오에 checked 속성이 있어야 한다
        b_match = re.search(r'<input[^>]+value="b"[^>]*>', self.html)
        self.assertIsNotNone(b_match, "value=b 라디오가 있어야 합니다")
        self.assertIn("checked", b_match.group(), "중급(b)이 기본 선택이어야 합니다")

    def test_a_not_checked(self):
        a_match = re.search(r'<input[^>]+value="a"[^>]*>', self.html)
        self.assertIsNotNone(a_match, "value=a 라디오가 있어야 합니다")
        self.assertNotIn("checked", a_match.group(), "기초(a)가 기본 선택이면 안 됩니다")

    def test_radio_name_is_metadata__level(self):
        # 모든 라디오의 name이 metadata__level 이어야 한다
        for m in re.finditer(r'<input[^>]+type=["\']radio["\'][^>]*>', self.html):
            self.assertIn('name="metadata__level"', m.group(),
                          f"라디오 name 이 metadata__level 이어야 합니다: {m.group()}")

    def test_has_version_marker(self):
        self.assertIn('data-v="2"', self.html, "버전 마커 data-v=2 가 있어야 합니다")

    def test_has_level_note(self):
        self.assertIn("기초 지문은 준비 중이에요", self.html, "기초 안내 노트가 있어야 합니다")


class SubHtmlJaTest(unittest.TestCase):
    """일본어 sub_html 에 수준 선택이 없는지 확인한다."""

    def setUp(self):
        self.html = publish.sub_html("ja")

    def test_no_radios(self):
        radios = re.findall(r'<input[^>]+type=["\']radio["\']', self.html)
        self.assertEqual(len(radios), 0, "일본어 구독 카드에 라디오가 없어야 합니다")

    def test_no_metadata__level_input(self):
        # GA 스크립트에 셀렉터로 metadata__level 문자열이 있을 수 있으므로, input 요소 여부로 확인한다
        inputs = re.findall(r'<input[^>]+name=["\']metadata__level["\']', self.html)
        self.assertEqual(len(inputs), 0, "일본어 구독 카드에 metadata__level input 이 없어야 합니다")

    def test_has_metadata__lang_ja(self):
        self.assertIn('value="ja"', self.html, "일본어 lang 값이 있어야 합니다")


class PatchPageTest(unittest.TestCase):
    """patch_page 가 이전 카드를 교체하고 멱등적으로 동작하는지 확인한다."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        day_dir = self.tmp / "en" / "2026-10-22"
        day_dir.mkdir(parents=True)
        # 썸네일 없이 최소 페이지 준비
        self.page_path = day_dir / "index.html"

    def write_page(self, content: str):
        self.page_path.write_text(content, encoding="utf-8")
        return self.page_path

    def read_page(self) -> str:
        return self.page_path.read_text(encoding="utf-8")

    def _patch(self, page_content: str) -> str:
        """publish.ROOT를 임시 디렉터리로 바꾸고 patch_page를 실행한다."""
        original_root = publish.ROOT
        try:
            publish.ROOT = self.tmp
            self.write_page(page_content)
            publish.patch_page("en", "2026-10-22")
            return self.read_page()
        finally:
            publish.ROOT = original_root

    def test_fresh_page_gets_card(self):
        # 카드가 없는 새 페이지에 카드가 삽입된다
        result = self._patch(MINIMAL_PAGE)
        self.assertIn('class="card sub"', result)
        self.assertIn('data-v="2"', result)

    def test_fresh_page_has_radios_for_en(self):
        result = self._patch(MINIMAL_PAGE)
        radios = re.findall(r'<input[^>]+type=["\']radio["\']', result)
        self.assertEqual(len(radios), 2)

    def test_old_card_replaced(self):
        # 이전 버전 카드(data-v 없음)가 새 카드로 교체된다
        result = self._patch(PAGE_WITH_OLD_CARD)
        self.assertIn('data-v="2"', result, "이전 카드가 새 버전으로 교체되어야 합니다")
        # 이전 카드가 남아 있으면 안 된다 (section 이 두 개면 안 된다)
        count = result.count('class="card sub"')
        self.assertEqual(count, 1, f"카드가 하나만 있어야 하는데 {count}개입니다")

    def test_old_card_gets_level_choice(self):
        result = self._patch(PAGE_WITH_OLD_CARD)
        radios = re.findall(r'<input[^>]+type=["\']radio["\']', result)
        self.assertEqual(len(radios), 2, "교체된 카드에 수준 선택 라디오가 있어야 합니다")

    def test_idempotent_on_already_updated_page(self):
        # 이미 새 카드가 있는 페이지를 다시 실행해도 중복 삽입이 없다
        result_first = self._patch(MINIMAL_PAGE)
        # 같은 페이지로 다시 실행
        result_second = self._patch(result_first)
        count = result_second.count('class="card sub"')
        self.assertEqual(count, 1, f"멱등 실행 후 카드가 1개여야 하는데 {count}개입니다")
        radios = re.findall(r'<input[^>]+type=["\']radio["\']', result_second)
        self.assertEqual(len(radios), 2)


if __name__ == "__main__":
    unittest.main()
