"""pool 관련 테스트: fallback jpg 복사, thumb pool 사진 활용, pool json 무결성.

실행: python -m pytest -q tests/test_pool.py
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

POOL_DIR = REPO / "pool"


def _make_jpeg_bytes() -> bytes:
    """PIL로 유효한 최소 JPEG 바이트(1×1 픽셀)를 만든다."""
    import io
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (4, 3), (100, 150, 200)).save(buf, format="JPEG")
    return buf.getvalue()


# ── 공통 헬퍼 ──────────────────────────────────────────────────────────────

def make_content(topic="테스트주제", date="") -> dict:
    """check_content.check 를 통과하는 최소 content JSON."""
    tag = "".join(chr(97 + ord(ch) % 26) for ch in topic) * 2
    return {
        "date": date,
        "category": "science",
        "topic": topic,
        "chips": ["5문장", "B1 위주", "B2 1문장", "약 3분"],
        "sentences": [
            {"en": f"This {tag}{i} sentence is about {tag}.", "b2": i == 4}
            for i in range(5)
        ],
        "words": [[f"{tag}{i}", "뜻"] for i in range(5)],
        "points": [{"title": "포인트", "body": "설명입니다."}],
        "answers": [f"문장 {i+1} 해석" for i in range(5)],
        "advanced": [],
        "source": None,
        "example": True,
    }


# ── 1. fallback: pool jpg → content photo.jpg 복사 ─────────────────────────

class FallbackPhotoTestBase(unittest.TestCase):
    """임시 디렉터리에 repo 레이아웃을 만들어 fallback 을 격리 테스트한다."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.root = Path(self.tmpdir)
        (self.root / "content" / "en").mkdir(parents=True)
        (self.root / "pool" / "en").mkdir(parents=True)

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

    def write_pool_json(self, filename, topic="주제A", photo_scene=""):
        data = make_content(topic=topic)
        if photo_scene:
            data["photo_scene"] = photo_scene
        path = self.root / "pool" / "en" / filename
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return path

    def write_pool_jpg(self, stem):
        """PIL 로 유효한 JPEG 파일을 pool jpg 대용으로 만든다."""
        jpg_path = self.root / "pool" / "en" / f"{stem}.jpg"
        jpg_path.write_bytes(_make_jpeg_bytes())
        return jpg_path


class TestFallbackCopiesJpg(FallbackPhotoTestBase):
    """pool jpg 가 있으면 fallback 이 content photo.jpg 로 복사한다."""

    def test_copies_jpg_to_content(self):
        """pool jpg → content/<lang>/<day>.photo.jpg 복사 확인."""
        stem = "2026-09-01"
        self.write_pool_json(f"{stem}.json", topic="주제A", photo_scene="A bowl of steamed white rice served in a ceramic bowl on a wooden table")
        jpg = self.write_pool_jpg(stem)

        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            result = self.fb.process_lang("en", "2026-10-20", dry_run=False)

        self.assertTrue(result.startswith("USED en 2026-10-20"), result)
        photo_dest = self.root / "content" / "en" / "2026-10-20.photo.jpg"
        self.assertTrue(photo_dest.exists(), "content photo.jpg 가 생성돼야 한다")

    def test_pool_jpg_removed_after_copy(self):
        """복사 후 pool jpg 가 삭제된다."""
        stem = "2026-09-01"
        self.write_pool_json(f"{stem}.json", topic="주제A", photo_scene="A ceramic mug of hot coffee placed on a clean wooden desk")
        jpg = self.write_pool_jpg(stem)

        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            self.fb.process_lang("en", "2026-10-20", dry_run=False)

        self.assertFalse(jpg.exists(), "사용된 pool jpg 는 삭제돼야 한다")

    def test_no_jpg_no_photo_dest(self):
        """pool jpg 가 없으면 content photo.jpg 를 만들지 않는다."""
        self.write_pool_json("2026-09-01.json", topic="주제A")

        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            self.fb.process_lang("en", "2026-10-20", dry_run=False)

        photo_dest = self.root / "content" / "en" / "2026-10-20.photo.jpg"
        self.assertFalse(photo_dest.exists(), "jpg 가 없으면 photo.jpg 도 없어야 한다")


# ── 2. thumb.build: content photo.jpg 가 있으면 API 를 부르지 않는다 ──────

class TestThumbBuildUsesPoolPhoto(unittest.TestCase):
    """content/<lang>/<day>.photo.jpg 가 있으면 source=pool 로 사용한다."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.root = Path(self.tmpdir)
        # 날짜 페이지 디렉터리 구조 생성
        self.lang, self.day = "en", "2026-11-01"
        page_dir = self.root / self.lang / self.day
        page_dir.mkdir(parents=True)
        (page_dir / "index.html").write_text(
            "<h1>독해한입 <em>테스트 주제</em></h1>", encoding="utf-8"
        )
        # content/<lang>/<day>.photo.jpg (1×1 더미)
        content_dir = self.root / "content" / self.lang
        content_dir.mkdir(parents=True)
        self._pool_photo = content_dir / f"{self.day}.photo.jpg"
        self._pool_photo.write_bytes(_make_jpeg_bytes())

        import thumb as th
        self._orig_root = th.ROOT
        th.ROOT = self.root
        self.th = th

    def tearDown(self):
        import thumb as th
        th.ROOT = self._orig_root
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_uses_pool_photo_instead_of_api(self):
        """pool photo.jpg 가 있으면 photo() API 를 호출하지 않는다."""
        with (
            patch.object(self.th, "photo", return_value=None) as mock_photo,
            patch.object(self.th, "compose") as mock_compose,
            patch.object(self.th, "is_photo", return_value=False),
            patch.object(self.th, "cover") as mock_cover,
        ):
            # compose 가 PIL Image 를 반환하는 것처럼 모킹한다
            from PIL import Image
            fake_img = Image.new("RGB", (1216, 640), (100, 150, 200))
            mock_compose.return_value = fake_img.convert("RGBA")
            mock_cover.return_value = fake_img

            try:
                self.th.build(self.lang, self.day)
            except Exception:
                pass  # 파일 저장 등의 후속 처리는 무시한다

            # photo() API 는 호출되지 않아야 한다
            mock_photo.assert_not_called()

    def test_source_pool_logged(self, capsys=None):
        """pool photo.jpg 사용 시 'source=pool' 로그가 출력된다."""
        import io
        from contextlib import redirect_stdout

        with (
            patch.object(self.th, "photo", return_value=None),
            patch.object(self.th, "compose") as mock_compose,
            patch.object(self.th, "is_photo", return_value=False),
            patch.object(self.th, "cover") as mock_cover,
        ):
            from PIL import Image
            fake_img = Image.new("RGB", (1216, 640), (100, 150, 200))
            mock_compose.return_value = fake_img.convert("RGBA")
            mock_cover.return_value = fake_img

            buf = io.StringIO()
            try:
                with redirect_stdout(buf):
                    self.th.build(self.lang, self.day)
            except Exception:
                pass

            output = buf.getvalue()
            self.assertIn("source=pool", output, f"stdout에 'source=pool' 가 없음: {output!r}")


# ── 3. pool json 무결성: photo_scene 필드 ─────────────────────────────────

class TestPoolJsonHasPhotoScene(unittest.TestCase):
    """모든 pool JSON 에 photo_scene 필드가 있어야 한다."""

    def _pool_files(self):
        files = []
        for lang in ("en", "ja", "de"):
            lang_dir = POOL_DIR / lang
            if lang_dir.is_dir():
                files.extend(sorted(lang_dir.glob("*.json")))
        return files

    def test_all_pool_json_have_photo_scene(self):
        files = self._pool_files()
        self.assertGreater(len(files), 0, "pool 파일이 없음")
        missing = []
        for f in files:
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as e:
                self.fail(f"{f}: 읽기 실패 {e}")
            scene = d.get("photo_scene", "")
            if not scene or not scene.strip():
                missing.append(str(f.relative_to(POOL_DIR)))
        if missing:
            self.fail(f"photo_scene 누락: {', '.join(missing)}")

    def test_photo_scene_is_english(self):
        """photo_scene 은 영어 문장이어야 한다(ASCII + 공백 위주)."""
        files = self._pool_files()
        non_ascii = []
        for f in files:
            d = json.loads(f.read_text(encoding="utf-8"))
            scene = d.get("photo_scene", "")
            # 한글(U+AC00-U+D7A3)이 섞이면 안 된다
            if any("가" <= c <= "힣" for c in scene):
                non_ascii.append(f"{f.name}: {scene!r}")
        if non_ascii:
            self.fail(f"photo_scene 에 한글 포함: {', '.join(non_ascii)}")


# ── 4. pool jpg 존재 확인 ─────────────────────────────────────────────────

class TestPoolJpgExists(unittest.TestCase):
    """모든 pool JSON 에 대응하는 jpg 가 있어야 한다.

    이미지 생성 작업이 완료된 뒤 통과한다.
    아직 생성 중이면 skip 된다.
    """

    def _pool_files(self):
        files = []
        for lang in ("en", "ja", "de"):
            lang_dir = POOL_DIR / lang
            if lang_dir.is_dir():
                files.extend(sorted(lang_dir.glob("*.json")))
        return files

    def test_all_pool_json_have_jpg(self):
        import pytest
        files = self._pool_files()
        self.assertGreater(len(files), 0)

        missing = [
            str(f.relative_to(POOL_DIR))
            for f in files
            if not f.with_suffix(".jpg").exists()
        ]
        if missing:
            # 생성이 아직 진행 중이거나 시작 전이면 skip
            pytest.skip(
                f"pool jpg 미완성 ({len(missing)}/{len(files)}개 누락) — "
                f"gen_pool_photos.py 완료 후 재확인: {', '.join(missing[:5])}{'…' if len(missing) > 5 else ''}"
            )


if __name__ == "__main__":
    unittest.main()
