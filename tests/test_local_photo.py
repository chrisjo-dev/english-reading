"""이미지 API 서버(tools/image-api/server.py) 단위 및 통합 테스트.

테스트 항목:
  - 서버 인증: 헤더 없음, 잘못된 토큰, 올바른 토큰
  - 대기열(429): 큐가 꽉 찼을 때
  - 크기 검증: 16 배수 아님, 최대 초과
  - OpenAI 호환 응답: 가짜 mflux 로 PNG 생성 확인
  - thumb.photo() 로컬 API 경로: env + photo_scene 있을 때 로컬 API 사용
  - thumb.photo() 폴백: 로컬 API 실패 시 OpenAI 경로

실행: python -m pytest -q tests/test_local_photo.py
"""

import base64
import io
import json
import os
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

from PIL import Image

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(REPO / "tools" / "image-api"))
import thumb  # noqa: E402

DAY   = "2026-10-30"
SCENE = (
    "A scientist in a white lab coat examining glowing crystals under "
    "a microscope in a clean laboratory setting."
)


# ── 헬퍼 ──────────────────────────────────────────────────────────────────────
def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _make_fake_mflux(tmp: Path) -> Path:
    """--output 경로에 최소 PNG 를 쓰는 가짜 mflux-generate 실행 파일."""
    # 1×1 픽셀 PNG (stdlib 만 사용; 별도 라이브러리 불필요)
    pixel_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/"
        "5+hHgAHggJ/PchI6QAAAABJRU5ErkJggg=="
    )
    script = tmp / "fake-mflux"
    script.write_text(
        f"#!{sys.executable}\n"
        "import base64, sys\n"
        f"PIXEL = base64.b64decode('{pixel_b64}')\n"
        "args = sys.argv[1:]\n"
        "for i, a in enumerate(args):\n"
        "    if a == '--output' and i + 1 < len(args):\n"
        "        open(args[i + 1], 'wb').write(PIXEL)\n"
        "        break\n"
    )
    script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP)
    return script


def _start_server(
    tmp: Path, fake_mflux: Path
) -> "tuple[subprocess.Popen, int, str]":
    """테스트용 서버를 시작하고 (proc, port, token) 을 돌려준다."""
    token = "test-token-abc123"
    token_file = tmp / "token"
    token_file.write_text(token)
    token_file.chmod(0o600)

    port = _free_port()
    env = {
        **os.environ,
        "MFLUX_BIN": str(fake_mflux),
        "FLUX_MODEL_DIR": "/fake/model",
        "IMAGE_API_TOKEN_FILE": str(token_file),
        "IMAGE_API_HOST": "127.0.0.1",
        "IMAGE_API_PORT": str(port),
    }
    proc = subprocess.Popen(
        [sys.executable, str(REPO / "tools" / "image-api" / "server.py")],
        env=env,
        stderr=subprocess.PIPE,
    )
    # 서버가 준비될 때까지 기다린다 (최대 5 초)
    health_url = f"http://127.0.0.1:{port}/health"
    for _ in range(50):
        try:
            urllib.request.urlopen(health_url, timeout=0.5)
            break
        except Exception:
            if proc.poll() is not None:
                raise RuntimeError(f"서버가 일찍 종료됐습니다 (port {port})")
            time.sleep(0.1)
    else:
        proc.terminate()
        raise RuntimeError(f"서버가 5 초 내에 시작되지 않았습니다 (port {port})")

    return proc, port, token


# ── 서버 통합 테스트 ───────────────────────────────────────────────────────────
class TestImageAPIServer(unittest.TestCase):
    """서버를 실제로 기동해 HTTP 동작을 검증합니다."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.fake_mflux = _make_fake_mflux(cls.tmp)
        cls.proc, cls.port, cls.token = _start_server(cls.tmp, cls.fake_mflux)

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=5)
        shutil.rmtree(str(cls.tmp))

    def _post(self, body: dict, token=None, expect_code: int = 200) -> dict:
        data = json.dumps(body).encode()
        headers: dict = {
            "Content-Type": "application/json",
            "Content-Length": str(len(data)),
        }
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/v1/images/generations",
            data=data,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == expect_code:
                return json.loads(e.read())
            raise

    # ── 헬스 엔드포인트 ──────────────────────────────────────────────────────
    def test_health_no_auth(self):
        resp = json.loads(
            urllib.request.urlopen(
                f"http://127.0.0.1:{self.port}/health", timeout=5
            ).read()
        )
        self.assertTrue(resp["ok"])
        self.assertIn("busy", resp)

    # ── 인증 ────────────────────────────────────────────────────────────────
    def test_missing_auth_header_returns_401(self):
        r = self._post({"prompt": "test"}, token=None, expect_code=401)
        self.assertIn("error", r)

    def test_wrong_token_returns_401(self):
        r = self._post({"prompt": "test"}, token="wrong-token", expect_code=401)
        self.assertIn("error", r)

    def test_correct_token_returns_200(self):
        r = self._post(
            {"prompt": "A sunny mountain landscape.", "size": "32x16", "steps": 1},
            token=self.token,
        )
        self.assertIn("data", r)
        self.assertEqual(len(r["data"]), 1)
        b64 = r["data"][0]["b64_json"]
        img = Image.open(io.BytesIO(base64.b64decode(b64)))
        self.assertEqual(img.format, "PNG")
        self.assertIn("created", r)

    # ── 크기 검증 ────────────────────────────────────────────────────────────
    def test_size_not_multiple_of_16_returns_400(self):
        r = self._post(
            {"prompt": "test", "size": "100x200"}, token=self.token, expect_code=400
        )
        self.assertIn("error", r)

    def test_size_exceeds_max_returns_400(self):
        r = self._post(
            {"prompt": "test", "size": "2048x2048"}, token=self.token, expect_code=400
        )
        self.assertIn("error", r)

    # ── 기타 입력 검증 ────────────────────────────────────────────────────────
    def test_n_not_1_returns_400(self):
        r = self._post({"prompt": "test", "n": 2}, token=self.token, expect_code=400)
        self.assertIn("error", r)

    def test_missing_prompt_returns_400(self):
        r = self._post({"size": "32x16"}, token=self.token, expect_code=400)
        self.assertIn("error", r)


# ── 429 대기열 단위 테스트 ─────────────────────────────────────────────────────
class TestServerQueue(unittest.TestCase):
    """대기열 로직을 server 모듈에서 직접 검증합니다."""

    def setUp(self):
        import server as s
        self.s = s
        self.orig = s._waiting
        s._waiting = 0

    def tearDown(self):
        self.s._waiting = self.orig

    def test_inc_waiting_fails_when_queue_full(self):
        import server as s
        s._waiting = s._MAX_WAIT   # 대기열이 꽉 찬 상태로 강제 설정
        self.assertFalse(s._inc_waiting(), "꽉 찬 대기열에는 추가되면 안 됩니다")

    def test_inc_waiting_succeeds_when_not_full(self):
        import server as s
        s._waiting = 0
        result = s._inc_waiting()
        self.assertTrue(result, "빈 대기열에는 추가돼야 합니다")
        s._dec_waiting()  # 정리


# ── install.sh / plist 검증 ───────────────────────────────────────────────────
class TestInstallFiles(unittest.TestCase):
    def test_bash_syntax(self):
        result = subprocess.run(
            ["bash", "-n", str(REPO / "tools" / "image-api" / "install.sh")],
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode())

    def test_plist_syntax_after_render(self):
        if not shutil.which("plutil"):
            self.skipTest("plutil 이 없어서 건너뜁니다")
        template = (
            REPO / "tools" / "image-api" / "com.chrisjo.image-api.plist.template"
        ).read_text()
        rendered = (
            template.replace("__SERVER_PY__", "/Users/chrisjo/image-api/server.py")
            .replace("__HOME__", "/Users/chrisjo")
            .replace("__TAILNET_IP__", "100.123.77.30")
            .replace("__FLUX_MODEL_DIR__", "/Users/chrisjo/models/schnell-q4")
        )
        with tempfile.NamedTemporaryFile(suffix=".plist", mode="w", delete=False) as f:
            fname = f.name
            f.write(rendered)
        try:
            r = subprocess.run(["plutil", "-lint", fname], capture_output=True)
            self.assertEqual(r.returncode, 0, r.stderr.decode())
        finally:
            os.unlink(fname)


# ── thumb.photo() 통합 테스트 ──────────────────────────────────────────────────
def _fake_openai_response() -> bytes:
    """OpenAI 이미지 API 응답을 흉내 낸 JSON 바이트."""
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), (200, 100, 50)).save(buf, "PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return json.dumps({"data": [{"b64_json": b64}]}).encode()


def _content_dir_with_scene(scene: str) -> "tuple[Path, Path]":
    """photo_scene 이 있는 content JSON 을 담은 임시 루트와 JSON 경로를 반환합니다."""
    d = Path(tempfile.mkdtemp())
    (d / "content" / "en").mkdir(parents=True)
    src = REPO / "content" / "en" / f"{DAY}.json"
    data = json.loads(src.read_text(encoding="utf-8"))
    data["photo_scene"] = scene
    p = d / "content" / "en" / f"{DAY}.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return d, p


class TestThumbLocalAPI(unittest.TestCase):
    """thumb.photo() 가 로컬 API 와 OpenAI 폴백을 올바르게 사용하는지 검사합니다."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.fake_mflux = _make_fake_mflux(cls.tmp)
        cls.proc, cls.port, cls.token = _start_server(cls.tmp, cls.fake_mflux)

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=5)
        shutil.rmtree(str(cls.tmp))

    def test_uses_local_api_when_env_and_photo_scene(self):
        """LOCAL_IMAGE_URL + LOCAL_IMAGE_TOKEN 있고 photo_scene 있으면 로컬 API 사용."""
        d, _ = _content_dir_with_scene(SCENE)
        patch = mock.patch.object(thumb, "ROOT", d)
        patch.start()
        try:
            with mock.patch.dict(
                os.environ,
                {
                    "LOCAL_IMAGE_URL": f"http://127.0.0.1:{self.port}",
                    "LOCAL_IMAGE_TOKEN": self.token,
                    "OPENAI_API_KEY": "",
                },
            ):
                result = thumb.photo("en", DAY)
            self.assertIsNotNone(result, "로컬 API 성공 시 None 이 아닌 이미지를 반환해야 합니다")
            self.assertIsInstance(result, Image.Image)
        finally:
            patch.stop()
            shutil.rmtree(str(d))

    def test_falls_back_to_openai_when_local_fails(self):
        """로컬 API 가 실패하면 OpenAI 경로로 폴백합니다."""
        d, _ = _content_dir_with_scene(SCENE)
        patch = mock.patch.object(thumb, "ROOT", d)
        patch.start()
        try:
            openai_called = []

            def mock_urlopen(req, timeout=None):
                url = getattr(req, "full_url", str(req))
                if f"127.0.0.1:{self.port}" in url:
                    raise OSError("로컬 API 강제 오류")
                openai_called.append(url)
                resp = mock.MagicMock()
                resp.read.return_value = _fake_openai_response()
                return resp

            with mock.patch.dict(
                os.environ,
                {
                    "LOCAL_IMAGE_URL": f"http://127.0.0.1:{self.port}",
                    "LOCAL_IMAGE_TOKEN": self.token,
                    "OPENAI_API_KEY": "test-key",
                },
            ), mock.patch.object(thumb.urllib.request, "urlopen", mock_urlopen):
                result = thumb.photo("en", DAY)

            self.assertIsNotNone(result, "OpenAI 폴백 성공 시 이미지를 반환해야 합니다")
            self.assertTrue(openai_called, "OpenAI 폴백이 호출되지 않았습니다")
        finally:
            patch.stop()
            shutil.rmtree(str(d))

    def test_no_photo_scene_skips_local_api(self):
        """photo_scene 이 없으면 로컬 API 를 호출하지 않습니다."""
        d = Path(tempfile.mkdtemp())
        (d / "content" / "en").mkdir(parents=True)
        src = REPO / "content" / "en" / f"{DAY}.json"
        data = json.loads(src.read_text(encoding="utf-8"))
        data.pop("photo_scene", None)
        (d / "content" / "en" / f"{DAY}.json").write_text(
            json.dumps(data), encoding="utf-8"
        )
        patch = mock.patch.object(thumb, "ROOT", d)
        patch.start()
        try:
            local_called = []

            def mock_urlopen(req, timeout=None):
                url = getattr(req, "full_url", str(req))
                if f"127.0.0.1:{self.port}" in url:
                    local_called.append(url)
                raise OSError("테스트 강제 오류")

            with mock.patch.dict(
                os.environ,
                {
                    "LOCAL_IMAGE_URL": f"http://127.0.0.1:{self.port}",
                    "LOCAL_IMAGE_TOKEN": self.token,
                    "OPENAI_API_KEY": "",
                },
            ), mock.patch.object(thumb.urllib.request, "urlopen", mock_urlopen):
                result = thumb.photo("en", DAY)

            self.assertFalse(
                local_called, "photo_scene 없으면 로컬 API 를 호출하면 안 됩니다"
            )
            self.assertIsNone(result)
        finally:
            patch.stop()
            shutil.rmtree(str(d))

    def test_no_local_env_uses_openai_directly(self):
        """LOCAL_IMAGE_URL 이 없으면 OpenAI 를 바로 시도합니다 (key 없으면 None)."""
        d, _ = _content_dir_with_scene(SCENE)
        patch = mock.patch.object(thumb, "ROOT", d)
        patch.start()
        try:
            with mock.patch.dict(
                os.environ,
                {
                    "LOCAL_IMAGE_URL": "",
                    "LOCAL_IMAGE_TOKEN": "",
                    "OPENAI_API_KEY": "",
                },
            ):
                result = thumb.photo("en", DAY)
            self.assertIsNone(result)
        finally:
            patch.stop()
            shutil.rmtree(str(d))


if __name__ == "__main__":
    unittest.main()
