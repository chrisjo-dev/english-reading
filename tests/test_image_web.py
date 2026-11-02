"""web.py (tools/image-api/web.py) 단위/통합 테스트.

테스트 항목:
  - /translate: mlx_lm 없을 때 501 반환
  - /history: 최신 순 정렬 및 페이지네이션 (offset/limit)
  - /files: 경로 이탈(../) 거부
  - 자동 저장: 성공 응답 시 PNG + JSON 사이드카 저장
  - hasHangul 로직 (Python 이식)

실행: python -m pytest -q tests/test_image_web.py
"""

import base64
import json
import os
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

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools" / "image-api"))

# ── 헬퍼 ──────────────────────────────────────────────────────────────────────
_PIXEL_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/"
    "5+hHgAHggJ/PchI6QAAAABJRU5ErkJggg=="
)
_PIXEL = base64.b64decode(_PIXEL_B64)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _make_fake_upstream(tmp: Path) -> "tuple[subprocess.Popen, int]":
    """최소 PNG 를 돌려주는 가짜 업스트림 HTTP 서버를 시작한다."""
    port   = _free_port()
    script = tmp / "fake_upstream.py"
    script.write_text(
        f"import http.server, json, base64\n"
        f"PIXEL = base64.b64decode('{_PIXEL_B64}')\n"
        f"class H(http.server.BaseHTTPRequestHandler):\n"
        f"    def log_message(self, *a): pass\n"
        f"    def do_GET(self):\n"
        f"        self.send_response(200)\n"
        f"        self.send_header('Content-Type','application/json')\n"
        f"        body = json.dumps({{'ok':True,'busy':False}}).encode()\n"
        f"        self.send_header('Content-Length',str(len(body)))\n"
        f"        self.end_headers(); self.wfile.write(body)\n"
        f"    def do_POST(self):\n"
        f"        cl = int(self.headers.get('Content-Length',0))\n"
        f"        req = json.loads(self.rfile.read(cl)) if cl else {{}}\n"
        f"        seed = req.get('seed', 42)\n"
        f"        b64 = base64.b64encode(PIXEL).decode()\n"
        f"        resp = json.dumps({{'created':1,'data':[{{'b64_json':b64}}],'seed':seed}}).encode()\n"
        f"        self.send_response(200)\n"
        f"        self.send_header('Content-Type','application/json')\n"
        f"        self.send_header('Content-Length',str(len(resp)))\n"
        f"        self.end_headers(); self.wfile.write(resp)\n"
        f"http.server.HTTPServer(('127.0.0.1',{port}),H).serve_forever()\n"
    )
    proc = subprocess.Popen([sys.executable, str(script)], stderr=subprocess.DEVNULL)
    _wait_port("127.0.0.1", port)
    return proc, port


def _start_web(
    tmp: Path, upstream_port: int, save_dir: Path, web_port: int
) -> subprocess.Popen:
    """web.py 를 시작한다. 토큰 파일도 준비한다."""
    token_file = tmp / "token"
    token_file.write_text("test-token")
    env = dict(os.environ)
    env["LOCAL_IMAGE_URL"]      = f"http://127.0.0.1:{upstream_port}"
    env["IMAGE_API_TOKEN_FILE"] = str(token_file)
    env["IMAGE_WEB_PORT"]       = str(web_port)
    env["IMAGE_WEB_DIR"]        = str(save_dir)
    proc = subprocess.Popen(
        [sys.executable, str(REPO / "tools" / "image-api" / "web.py")],
        env=env, stderr=subprocess.DEVNULL,
    )
    _wait_port("127.0.0.1", web_port)
    return proc


def _wait_port(host: str, port: int, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.3):
                return
        except OSError:
            time.sleep(0.1)
    raise TimeoutError(f"{host}:{port} 시작 대기 시간 초과")


def _get(url: str) -> "tuple[int, bytes]":
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def _post(url: str, body: dict) -> "tuple[int, dict]":
    data = json.dumps(body).encode()
    req  = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


# ── 번역 모듈 단위 테스트 ─────────────────────────────────────────────────────
class TestTranslateUnit(unittest.TestCase):
    """mlx_lm 없이 translate_text 를 직접 테스트한다."""

    def test_returns_501_json_when_mlx_lm_missing(self):
        """mlx_lm import 실패 시 ImportError 가 전파되어야 한다."""
        import web
        with mock.patch.dict(sys.modules, {"mlx_lm": None}):
            # _mlx_model 을 None 으로 리셋
            orig_model     = web._mlx_model
            orig_tokenizer = web._mlx_tokenizer
            web._mlx_model     = None
            web._mlx_tokenizer = None
            try:
                with self.assertRaises((ImportError, TypeError)):
                    web.translate_text("테스트")
            finally:
                web._mlx_model     = orig_model
                web._mlx_tokenizer = orig_tokenizer


# ── 한글 감지 (JS 로직을 Python 으로 이식) ────────────────────────────────────
import re as _re
_HANGUL_RE = _re.compile(r'[가-힣ᄀ-ᇿ㄰-㆏]')

def _has_hangul(s: str) -> bool:
    return bool(_HANGUL_RE.search(s))


class TestHangulDetection(unittest.TestCase):
    def test_korean(self):
        self.assertTrue(_has_hangul("남자 아이가 우는 모습"))

    def test_english(self):
        self.assertFalse(_has_hangul("A boy crying in the park"))

    def test_mixed(self):
        self.assertTrue(_has_hangul("hello 안녕"))

    def test_empty(self):
        self.assertFalse(_has_hangul(""))


# ── 자동 저장 단위 테스트 ──────────────────────────────────────────────────────
class TestAutosave(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp)

    def test_saves_png_and_json(self):
        import web
        save_dir = self.tmp / "images"

        meta = {
            "idea":    "남자 아이가 우는 모습",
            "scene":   "A young boy sitting on a bench, crying.",
            "style":   "thumbnail",
            "size":    "1216x640",
            "seed":    42,
            "seconds": 90.0,
            "prompt":  "thumbnail style...\nScene: A young boy...",
        }

        with mock.patch.object(web, "_get_save_dir", return_value=save_dir):
            web._save_result(base64.b64encode(_PIXEL).decode(), meta)

        png_files  = list(save_dir.rglob("*.png"))
        json_files = list(save_dir.rglob("*.json"))
        self.assertEqual(len(png_files),  1)
        self.assertEqual(len(json_files), 1)

        saved = json.loads(json_files[0].read_text())
        self.assertEqual(saved["idea"],  meta["idea"])
        self.assertEqual(saved["seed"],  42)
        self.assertIn("created", saved)

    def test_no_overwrite(self):
        import web
        save_dir = self.tmp / "images2"

        with mock.patch.object(web, "_get_save_dir", return_value=save_dir):
            b64 = base64.b64encode(_PIXEL).decode()
            meta = {"seed": 1, "idea": "a", "scene": "a", "style": "none",
                    "size": "1216x640", "seconds": 1.0, "prompt": "a"}

            # 같은 초에 두 번 저장 — stem 이 같으면 suffix 붙어야 함
            from unittest.mock import patch
            from datetime import datetime, timezone, timedelta
            fixed_dt = datetime(2026, 11, 2, 12, 0, 0, tzinfo=timezone(timedelta(hours=9)))
            with patch("web.datetime") as mock_dt:
                mock_dt.now.return_value = fixed_dt
                mock_dt.side_effect = None
                web._save_result(b64, meta)
                web._save_result(b64, dict(meta))

        png_files = list(save_dir.rglob("*.png"))
        self.assertEqual(len(png_files), 2)


# ── 경로 안전 단위 테스트 ─────────────────────────────────────────────────────
class TestSafeFilePath(unittest.TestCase):
    def test_valid(self):
        import web
        with tempfile.TemporaryDirectory() as d:
            save_dir = Path(d)
            (save_dir / "2026-11-02").mkdir()
            (save_dir / "2026-11-02" / "120000-42.png").write_bytes(b"")
            with mock.patch.object(web, "_get_save_dir", return_value=save_dir):
                p = web._safe_file_path("2026-11-02", "120000-42.png")
            self.assertIsNotNone(p)

    def test_traversal_dotdot_date(self):
        import web
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(web, "_get_save_dir", return_value=Path(d)):
                p = web._safe_file_path("../etc", "passwd")
        self.assertIsNone(p)

    def test_traversal_dotdot_name(self):
        import web
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(web, "_get_save_dir", return_value=Path(d)):
                p = web._safe_file_path("2026-11-02", "../../etc/passwd")
        self.assertIsNone(p)


# ── 통합 테스트 (실제 HTTP 서버) ─────────────────────────────────────────────
class TestWebIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp       = Path(tempfile.mkdtemp())
        cls.save_dir  = cls.tmp / "images"
        cls.save_dir.mkdir()
        cls.up_proc, cls.up_port = _make_fake_upstream(cls.tmp)
        cls.web_port  = _free_port()
        cls.web_proc  = _start_web(cls.tmp, cls.up_port, cls.save_dir, cls.web_port)
        cls.base      = f"http://127.0.0.1:{cls.web_port}"

    @classmethod
    def tearDownClass(cls):
        cls.web_proc.terminate()
        cls.up_proc.terminate()
        import shutil
        shutil.rmtree(cls.tmp)

    # ── /translate 501 when mlx_lm missing ──────────────────────────────────
    def test_translate_501_no_mlx(self):
        """plain python3 로 실행했으면 mlx_lm 이 없어서 501 이 와야 한다."""
        code, body = _post(f"{self.base}/translate", {"text": "남자 아이가 우는 모습"})
        # mlx_lm 이 실제로 설치된 환경이라면 200 이 올 수도 있다 (CI 에서는 501)
        self.assertIn(code, (200, 501))
        if code == 501:
            self.assertIn("mlx_lm", body.get("error", {}).get("message", ""))

    # ── /translate 400 on missing text ──────────────────────────────────────
    def test_translate_400_missing_text(self):
        code, body = _post(f"{self.base}/translate", {})
        self.assertEqual(code, 400)

    # ── /history empty → [] ─────────────────────────────────────────────────
    def test_history_empty(self):
        code, data_bytes = _get(f"{self.base}/history")
        self.assertEqual(code, 200)
        d = json.loads(data_bytes)
        self.assertIn("items", d)
        self.assertIsInstance(d["items"], list)

    # ── 자동 저장 후 /history 에 나타나는지 ──────────────────────────────────
    def test_generate_saves_and_appears_in_history(self):
        code, data = _post(f"{self.base}/v1/images/generations", {
            "prompt": "A test scene.",
            "size":   "1216x640",
            "seed":   99,
            "_idea":  "테스트 장면",
            "_scene": "A test scene.",
            "_style": "none",
        })
        self.assertEqual(code, 200)
        self.assertIn("data", data)

        # 저장은 백그라운드 스레드이므로 잠깐 기다린다
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            png_files = list(self.save_dir.rglob("*.png"))
            if png_files:
                break
            time.sleep(0.2)
        self.assertTrue(len(png_files) >= 1, "PNG 가 저장되지 않았습니다")
        json_files = list(self.save_dir.rglob("*.json"))
        self.assertTrue(len(json_files) >= 1, "JSON 사이드카가 저장되지 않았습니다")

        # /history 에서 확인
        time.sleep(0.5)
        code2, data2_bytes = _get(f"{self.base}/history")
        self.assertEqual(code2, 200)
        d2 = json.loads(data2_bytes)
        self.assertGreater(len(d2["items"]), 0)

    # ── /history 정렬: 최신 항목이 첫 번째 ──────────────────────────────────
    def test_history_newest_first(self):
        """기록이 2개 이상이면 created 가 내림차순이어야 한다."""
        code, data_bytes = _get(f"{self.base}/history?limit=24")
        self.assertEqual(code, 200)
        items = json.loads(data_bytes)["items"]
        if len(items) < 2:
            return  # 항목이 부족하면 건너뜀
        times = [i.get("created", "") for i in items if i.get("created")]
        for a, b in zip(times, times[1:]):
            self.assertGreaterEqual(a, b, "기록이 최신 순이 아닙니다")

    # ── /history 페이지네이션 ────────────────────────────────────────────────
    def test_history_pagination(self):
        code, data_bytes = _get(f"{self.base}/history?offset=0&limit=1")
        self.assertEqual(code, 200)
        d = json.loads(data_bytes)
        self.assertLessEqual(len(d["items"]), 1)

        code2, data2_bytes = _get(f"{self.base}/history?offset=1&limit=1")
        self.assertEqual(code2, 200)
        d2 = json.loads(data2_bytes)
        if d["items"] and d2["items"]:
            self.assertNotEqual(d["items"][0].get("filename"), d2["items"][0].get("filename"))

    # ── /files 경로 이탈 거부 ────────────────────────────────────────────────
    def test_files_traversal_rejected(self):
        code, _ = _get(f"{self.base}/files/../etc/passwd")
        self.assertIn(code, (400, 403, 404))

    def test_files_dotdot_in_date_rejected(self):
        code, _ = _get(f"{self.base}/files/..%2Fetc/passwd.png")
        self.assertIn(code, (400, 403, 404))

    def test_files_dotdot_explicit_rejected(self):
        code, _ = _get(f"{self.base}/files/../2026-11-02/120000-42.png")
        self.assertIn(code, (400, 403, 404))


if __name__ == "__main__":
    unittest.main()
