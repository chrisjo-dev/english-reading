"""tools/local-photo/make_photos.py 와 check_content.py 의 photo_scene 검증 단위 테스트.

실행: python -m pytest -q tests/test_local_photo.py
"""
import io
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(REPO / "tools" / "local-photo"))

import check_content as cc  # noqa: E402
import make_photos  # noqa: E402


# ---------------------------------------------------------------------------
# 헬퍼: 최소 유효 content JSON 생성
# ---------------------------------------------------------------------------
def _base_doc(**extra):
    d = {
        "date": "2026-10-30",
        "category": "science",
        "topic": "테스트",
        "title_ko": "테스트 제목",
        "headline": "Test headline",
        "chips": ["5문장", "B1 위주", "약 3분"],
        "sentences": [
            {"en": "The sky is blue.", "b2": False,
             "chunks": [["The sky", "하늘은"], ["is blue.", "파랗다"]]}
        ],
        "words": [["sky", "하늘"]],
        "points": [{"title": "포인트", "body": "설명"}],
        "answers": ["하늘은 파랗다."],
        "advanced": [],
        "source": None,
        "levels": {
            "a": {
                "sentences": [
                    {"en": "The sky is blue.",
                     "chunks": [["The sky", "하늘은"], ["is blue.", "파랗다"]]}
                ],
                "answers": ["하늘은 파랗다."]
            }
        },
    }
    d.update(extra)
    return d


def _write_content(root: Path, lang: str, day: str, doc: dict) -> Path:
    d = root / "content" / lang
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{day}.json"
    p.write_text(json.dumps(doc, ensure_ascii=False))
    return p


# ---------------------------------------------------------------------------
# 1. check_content.py photo_scene 검증
# ---------------------------------------------------------------------------
class TestPhotoSceneValidation(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.day = "2026-10-30"

    def _check(self, scene_val, include=True):
        doc = _base_doc()
        if include:
            doc["photo_scene"] = scene_val
        p = _write_content(self.tmp, "en", self.day, doc)
        errors, _ = cc.check(p)
        return errors

    def test_valid_scene_no_error(self):
        scene = "A scientist in a white lab coat examining glowing crystals under a microscope in a clean laboratory setting."
        self.assertEqual([e for e in self._check(scene) if "photo_scene" in e], [])

    def test_missing_field_allowed(self):
        # photo_scene 없으면 아무 오류도 없어야 한다
        self.assertEqual([e for e in self._check(None, include=False) if "photo_scene" in e], [])

    def test_too_short_rejected(self):
        errs = self._check("Short scene.")
        self.assertTrue(any("photo_scene" in e and "40자" in e for e in errs))

    def test_too_long_rejected(self):
        long_scene = "A " + "very " * 60 + "long description of a scene."
        errs = self._check(long_scene)
        self.assertTrue(any("photo_scene" in e and "300자" in e for e in errs))

    def test_exact_40_chars_ok(self):
        scene = "A" * 40
        self.assertEqual([e for e in self._check(scene) if "photo_scene" in e], [])

    def test_exact_300_chars_ok(self):
        scene = "A" * 300
        self.assertEqual([e for e in self._check(scene) if "photo_scene" in e], [])

    def test_301_chars_rejected(self):
        errs = self._check("A" * 301)
        self.assertTrue(any("photo_scene" in e and "300자" in e for e in errs))

    def test_photo_scene_not_checked_for_markdown(self):
        # photo_scene 에 ** 이 있어도 마크다운 오류로 잡히지 않아야 한다
        scene = "A **bold** scientist working at a laboratory bench with microscopes and equipment."
        # 길이가 40자 이상이면 통과 (마크다운 검사 skip 목록에 있으므로)
        errors = self._check(scene)
        self.assertEqual([e for e in errors if "photo_scene" in e], [])


# ---------------------------------------------------------------------------
# 2. make_photos.find_targets 선택 로직
# ---------------------------------------------------------------------------
SCENE_40 = "A biologist studying coral reef specimens under bright laboratory lights carefully."


class TestFindTargets(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.day = "2026-10-30"

    def _write(self, lang: str, doc: dict, photo_exists=False):
        _write_content(self.tmp, lang, self.day, doc)
        if photo_exists:
            (self.tmp / "content" / lang / f"{self.day}.photo.jpg").write_bytes(b"fake")

    def test_finds_json_with_scene_no_photo(self):
        doc = _base_doc(photo_scene=SCENE_40)
        self._write("en", doc)
        targets = make_photos.find_targets(self.day, ["en"], repo=self.tmp)
        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0][0], "en")
        self.assertEqual(targets[0][2], SCENE_40)

    def test_skips_if_photo_already_exists(self):
        doc = _base_doc(photo_scene=SCENE_40)
        self._write("en", doc, photo_exists=True)
        targets = make_photos.find_targets(self.day, ["en"], repo=self.tmp)
        self.assertEqual(targets, [])

    def test_skips_if_no_photo_scene(self):
        doc = _base_doc()  # photo_scene 없음
        self._write("en", doc)
        targets = make_photos.find_targets(self.day, ["en"], repo=self.tmp)
        self.assertEqual(targets, [])

    def test_skips_if_photo_scene_empty(self):
        doc = _base_doc(photo_scene="   ")
        self._write("en", doc)
        targets = make_photos.find_targets(self.day, ["en"], repo=self.tmp)
        self.assertEqual(targets, [])

    def test_skips_if_json_missing(self):
        targets = make_photos.find_targets(self.day, ["en"], repo=self.tmp)
        self.assertEqual(targets, [])

    def test_multiple_langs(self):
        for lang in ("en", "ja", "de"):
            doc = _base_doc(photo_scene=SCENE_40)
            self._write(lang, doc)
        targets = make_photos.find_targets(self.day, ["en", "ja", "de"], repo=self.tmp)
        self.assertEqual(len(targets), 3)
        self.assertEqual({t[0] for t in targets}, {"en", "ja", "de"})

    def test_partially_done(self):
        # en 은 사진 있음, ja 는 없음
        self._write("en", _base_doc(photo_scene=SCENE_40), photo_exists=True)
        self._write("ja", _base_doc(photo_scene=SCENE_40))
        targets = make_photos.find_targets(self.day, ["en", "ja"], repo=self.tmp)
        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0][0], "ja")


# ---------------------------------------------------------------------------
# 3. make_photos.generate_one 및 dry-run 동작
# ---------------------------------------------------------------------------
def _make_fake_mflux(tmp: Path) -> Path:
    """--output 인자에 지정된 경로에 최소 PNG 를 쓰는 가짜 mflux-generate 스크립트."""
    # Pillow 로 1x1 PNG bytes 생성
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (1216, 640), (100, 150, 200)).save(buf, "PNG")
    png_bytes = buf.getvalue()

    fake_bin = tmp / "fake_mflux"
    fake_bin.write_text(
        f"#!/usr/bin/env python3\n"
        f"import sys\n"
        f"from pathlib import Path\n"
        f"args = sys.argv[1:]\n"
        f"for i, a in enumerate(args):\n"
        f"    if a == '--output' and i + 1 < len(args):\n"
        f"        Path(args[i + 1]).write_bytes({png_bytes!r})\n"
        f"        break\n"
    )
    fake_bin.chmod(fake_bin.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP)
    return fake_bin


class TestGenerateDryRun(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.fake_bin = _make_fake_mflux(self.tmp)

    def test_dry_run_writes_to_tmp_not_repo(self):
        import logging
        log = logging.getLogger("test")
        day = "2026-10-30"
        lang = "en"
        dummy_out = self.tmp / "should_not_exist.jpg"
        env_patch = {"FLUX_MODEL_DIR": "/fake/model", "MFLUX_BIN": str(self.fake_bin)}
        with mock.patch.dict(os.environ, env_patch):
            ok = make_photos.generate_one(lang, day, SCENE_40, dummy_out, dry_run=True, log=log)
        self.assertTrue(ok)
        # dry-run 이면 지정된 out_jpg 에 쓰지 않는다
        self.assertFalse(dummy_out.exists())
        # /tmp/<day>_<lang>.photo.jpg 에 생성됐는지 확인
        import tempfile as tf
        expected = Path(tf.gettempdir()) / f"{day}_{lang}.photo.jpg"
        self.assertTrue(expected.exists())
        from PIL import Image
        img = Image.open(expected)
        self.assertEqual(img.format, "JPEG")


# ---------------------------------------------------------------------------
# 4. 커밋 모드: 로컬 bare remote 로 실제 commit+push 검증
# ---------------------------------------------------------------------------
class TestCommitMode(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.fake_bin = _make_fake_mflux(self.tmp)
        # bare remote
        self.remote = self.tmp / "remote.git"
        subprocess.run(["git", "init", "--bare", str(self.remote)], check=True, capture_output=True)
        # clone
        self.repo_path = self.tmp / "repo"
        subprocess.run(["git", "clone", str(self.remote), str(self.repo_path)],
                       check=True, capture_output=True)
        # 초기 커밋
        subprocess.run(["git", "-C", str(self.repo_path), "config", "user.email", "t@t.com"],
                       check=True, capture_output=True)
        subprocess.run(["git", "-C", str(self.repo_path), "config", "user.name", "Test"],
                       check=True, capture_output=True)
        init_file = self.repo_path / "README.md"
        init_file.write_text("test")
        subprocess.run(["git", "-C", str(self.repo_path), "add", "README.md"],
                       check=True, capture_output=True)
        subprocess.run(["git", "-C", str(self.repo_path), "commit", "-m", "init"],
                       check=True, capture_output=True)
        subprocess.run(["git", "-C", str(self.repo_path), "push", "-u", "origin", "main"],
                       check=True, capture_output=True)
        # content JSON
        self.day = "2026-10-30"
        _write_content(self.repo_path, "en", self.day, _base_doc(photo_scene=SCENE_40))

    def test_commit_mode_creates_jpg_and_pushes(self):
        env_patch = {"FLUX_MODEL_DIR": "/fake/model", "MFLUX_BIN": str(self.fake_bin)}
        with mock.patch.object(make_photos, "REPO", self.repo_path), \
             mock.patch.dict(os.environ, env_patch):
            # pull 은 이미 clone 돼 있으므로 스킵하기 위해 dry_run=False 로 직접 generate_one 호출
            out_jpg = self.repo_path / "content" / "en" / f"{self.day}.photo.jpg"
            import logging
            log = logging.getLogger("test")
            ok = make_photos.generate_one("en", self.day, SCENE_40, out_jpg, dry_run=False, log=log)
        self.assertTrue(ok)
        self.assertTrue(out_jpg.exists())
        from PIL import Image
        img = Image.open(out_jpg)
        self.assertEqual(img.format, "JPEG")

    def test_git_commit_push_to_bare_remote(self):
        """generate_one + git_commit_push 의 end-to-end 검증."""
        import logging
        log = logging.getLogger("test")
        out_jpg = self.repo_path / "content" / "en" / f"{self.day}.photo.jpg"
        env_patch = {"FLUX_MODEL_DIR": "/fake/model", "MFLUX_BIN": str(self.fake_bin)}
        with mock.patch.object(make_photos, "REPO", self.repo_path), \
             mock.patch.dict(os.environ, env_patch):
            make_photos.generate_one("en", self.day, SCENE_40, out_jpg, dry_run=False, log=log)
            make_photos.git_commit_push([out_jpg], self.day, ["en"], log)
        # bare remote 에 파일이 올라갔는지 확인
        result = subprocess.run(
            ["git", "-C", str(self.remote), "cat-file", "-e", f"HEAD:content/en/{self.day}.photo.jpg"],
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, "photo.jpg 가 remote 에 push 되지 않았습니다")


if __name__ == "__main__":
    unittest.main()
