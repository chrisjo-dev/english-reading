"""tools/fallback.py 및 send_email.recently_sent 단위 테스트.

실행: python -m pytest -q tests/test_fallback.py
     python tests/test_fallback.py
"""
import datetime
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# 저장소 루트를 sys.path 에 추가해 tools/ 를 불러올 수 있게 한다
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))


def make_content(topic="테스트주제", date="") -> dict:
    """check_content.check 를 통과하는 최소 content JSON. 주제마다 본문과 단어가 달라 내용 겹침 검사에 걸리지 않는다."""
    tag = "".join(chr(97 + ord(ch) % 26) for ch in topic) * 2
    c = {
        "date": date,
        "category": "science",
        "topic": topic,
        "chips": ["5문장", "B1 위주", "B2 1문장", "약 3분"],
        "sentences": [
            {"en": "This is sentence one.", "b2": False},
            {"en": "This is sentence two.", "b2": False},
            {"en": "This is sentence three.", "b2": False},
            {"en": "This is sentence four.", "b2": False},
            {"en": "This is sentence five.", "b2": True},
        ],
        "words": [
            ["sentence", "문장"],
            ["one", "하나"],
            ["two", "둘"],
            ["three", "셋"],
            ["four", "넷"],
        ],
        "points": [{"title": "포인트", "body": "설명입니다."}],
        "answers": [
            "문장 1 해석",
            "문장 2 해석",
            "문장 3 해석",
            "문장 4 해석",
            "문장 5 해석",
        ],
        "advanced": [],
        "source": None,
        "example": True,  # 출처 없는 수치 경고를 피하기 위해
    }
    c["sentences"] = [{"en": f"This {tag}{i} sentence is about {tag}.", "b2": i == 4} for i in range(5)]
    c["words"] = [[f"{tag}{i}", "뜻"] for i in range(5)]
    return c


class FallbackTestBase(unittest.TestCase):
    """각 테스트마다 임시 디렉터리에 repo 레이아웃을 만든다."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.root = Path(self.tmpdir)
        (self.root / "content" / "en").mkdir(parents=True)
        (self.root / "content" / "ja").mkdir(parents=True)
        (self.root / "pool" / "en").mkdir(parents=True)
        (self.root / "pool" / "ja").mkdir(parents=True)

        # fallback 모듈이 ROOT 를 사용하므로 monkeypatch
        import fallback as fb
        self._orig_root = fb.ROOT
        self._orig_content = fb.CONTENT_DIR
        self._orig_pool = fb.POOL_DIR
        fb.ROOT = self.root
        fb.CONTENT_DIR = self.root / "content"
        fb.POOL_DIR = self.root / "pool"
        self.fb = fb

    def tearDown(self):
        import fallback as fb
        fb.ROOT = self._orig_root
        fb.CONTENT_DIR = self._orig_content
        fb.POOL_DIR = self._orig_pool
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def write_pool(self, lang, filename, topic="주제A", bad_markdown=False):
        data = make_content(topic=topic)
        if bad_markdown:
            data["sentences"][0]["en"] = "*bad markdown* text"
        path = self.root / "pool" / lang / filename
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return path

    def write_content(self, lang, day, topic="주제A"):
        data = make_content(topic=topic, date=day)
        path = self.root / "content" / lang / f"{day}.json"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return path


class TestExists(FallbackTestBase):
    """content/<lang>/<day>.json 이 이미 있으면 EXISTS 를 반환한다."""

    def test_exists_returns_exists(self):
        self.write_content("en", "2026-10-15")
        with patch("subprocess.run") as mock_run:
            result = self.fb.process_lang("en", "2026-10-15", dry_run=False)
        self.assertEqual(result, "EXISTS en")
        mock_run.assert_not_called()


class TestChooseOldest(FallbackTestBase):
    """파일명 순으로 가장 오래된 pool 파일을 선택한다."""

    def test_oldest_selected(self):
        self.write_pool("en", "2026-09-01.json", topic="주제A")
        self.write_pool("en", "2026-09-02.json", topic="주제B")

        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            result = self.fb.process_lang("en", "2026-10-20", dry_run=False)

        self.assertTrue(result.startswith("USED en 2026-10-20 2026-09-01.json"), result)
        # 선택된 파일은 content 에 써진다
        dest = self.root / "content" / "en" / "2026-10-20.json"
        self.assertTrue(dest.exists())
        data = json.loads(dest.read_text())
        self.assertEqual(data["date"], "2026-10-20")
        self.assertEqual(data["topic"], "주제A")
        # 사용된 pool 파일은 사라진다
        self.assertFalse((self.root / "pool" / "en" / "2026-09-01.json").exists())


class TestSkipRecentTopic(FallbackTestBase):
    """최근 60일 이내 content 에 쓰인 주제는 건너뛴다."""

    def test_skip_recent_topic(self):
        # content 에 최근 날짜로 주제A 가 있다
        self.write_content("en", "2026-10-10", topic="주제A")
        # pool 에 주제A(최근 사용), 주제B(새 주제) 두 파일이 있다
        self.write_pool("en", "2026-09-01.json", topic="주제A")  # 건너뜀
        self.write_pool("en", "2026-09-02.json", topic="주제B")  # 선택됨

        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            result = self.fb.process_lang("en", "2026-10-20", dry_run=False)

        self.assertTrue(result.startswith("USED en 2026-10-20 2026-09-02.json"), result)

    def test_old_topic_not_skipped(self):
        """60일을 초과한 주제는 다시 사용할 수 있다."""
        # 61일 전 content 에 주제A 가 있다
        old_day = (datetime.date(2026, 10, 20) - datetime.timedelta(days=61)).isoformat()
        self.write_content("en", old_day, topic="주제A")
        self.write_pool("en", "2026-09-01.json", topic="주제A")

        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            result = self.fb.process_lang("en", "2026-10-20", dry_run=False)

        self.assertTrue(result.startswith("USED en 2026-10-20 2026-09-01.json"), result)


class TestEmptyPool(FallbackTestBase):
    """pool 이 비어 있으면 EMPTY 를 반환한다."""

    def test_empty_pool(self):
        result = self.fb.process_lang("en", "2026-10-20", dry_run=False)
        self.assertEqual(result, "EMPTY en")

    def test_all_topics_excluded(self):
        """pool 에 파일은 있지만 모두 최근 주제라 건너뛰면 EMPTY."""
        self.write_content("en", "2026-10-10", topic="주제A")
        self.write_pool("en", "2026-09-01.json", topic="주제A")
        result = self.fb.process_lang("en", "2026-10-20", dry_run=False)
        self.assertEqual(result, "EMPTY en")


class TestCheckFailureFallthrough(FallbackTestBase):
    """check 실패 시 다음 후보로 넘어간다."""

    def test_check_failure_falls_through(self):
        # 첫 번째 파일은 마크다운 오류가 있어 check 실패
        self.write_pool("en", "2026-09-01.json", topic="주제A", bad_markdown=True)
        # 두 번째 파일은 정상
        self.write_pool("en", "2026-09-02.json", topic="주제B")

        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            result = self.fb.process_lang("en", "2026-10-20", dry_run=False)

        # 첫 번째가 실패했으므로 두 번째가 선택된다
        self.assertTrue(result.startswith("USED en 2026-10-20 2026-09-02.json"), result)
        # 실패한 파일의 content 는 삭제됐다(dest 없음 확인)
        # (이미 두 번째가 썼으므로 dest 는 있지만 내용이 주제B)
        dest = self.root / "content" / "en" / "2026-10-20.json"
        data = json.loads(dest.read_text())
        self.assertEqual(data["topic"], "주제B")

    def test_all_fail_returns_empty(self):
        """모든 후보가 check 를 통과하지 못하면 EMPTY."""
        self.write_pool("en", "2026-09-01.json", topic="주제A", bad_markdown=True)
        result = self.fb.process_lang("en", "2026-10-20", dry_run=False)
        self.assertEqual(result, "EMPTY en")


class TestRecentlySent(unittest.TestCase):
    """recently_sent(sent_at, now) 순수 함수 테스트."""

    def setUp(self):
        import send_email
        self.recently_sent = send_email.recently_sent
        self.now = datetime.datetime(2026, 10, 14, 7, 30, 0, tzinfo=datetime.timezone.utc)

    def test_within_30_minutes(self):
        sent_at = "2026-10-14T07:10:00+00:00"
        self.assertTrue(self.recently_sent(sent_at, self.now))

    def test_exactly_30_minutes(self):
        # 정확히 30분 = 1800초: 30분 이내(< 1800)가 아니므로 False
        sent_at = "2026-10-14T07:00:00+00:00"
        self.assertFalse(self.recently_sent(sent_at, self.now))

    def test_over_30_minutes(self):
        sent_at = "2026-10-14T06:50:00+00:00"
        self.assertFalse(self.recently_sent(sent_at, self.now))

    def test_z_suffix(self):
        sent_at = "2026-10-14T07:15:00Z"
        self.assertTrue(self.recently_sent(sent_at, self.now))

    def test_empty_string(self):
        self.assertFalse(self.recently_sent("", self.now))

    def test_none(self):
        self.assertFalse(self.recently_sent(None, self.now))

    def test_naive_now(self):
        """now 가 timezone-aware 가 아니어도 처리한다."""
        now_naive = datetime.datetime(2026, 10, 14, 7, 30, 0)
        sent_at = "2026-10-14T07:10:00+00:00"
        self.assertTrue(self.recently_sent(sent_at, now_naive))


if __name__ == "__main__":
    unittest.main()
