#!/usr/bin/env python3
"""맥 미니 이미지 생성 API 서버 (OpenAI 호환).

POST /v1/images/generations  – FLUX.1 schnell 로 이미지 생성
GET  /health                 – 서버 상태 확인 (인증 불필요)

환경 변수:
  FLUX_MODEL_DIR       (필수) mflux 모델 디렉터리 경로
  IMAGE_API_TOKEN_FILE 토큰 파일 경로 (기본: ~/.config/image-api/token)
  IMAGE_API_HOST       바인딩 주소 (기본: 127.0.0.1; plist 에서 Tailscale IP 로 덮어씀)
  IMAGE_API_PORT       바인딩 포트 (기본: 8790)
  MFLUX_BIN            mflux-generate 실행 파일 경로
                       (기본: PATH 와 ~/.local/bin 에서 자동 탐색)

사용: python3 tools/image-api/server.py
"""

import base64
import hmac
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# ── 서버 상태 (스레드 안전) ────────────────────────────────────────────────────
_job_lock  = threading.Lock()    # 실행 중인 작업 1개를 보호
_state_lock = threading.Lock()   # _waiting / _running 보호
_waiting   = 0                   # _job_lock 을 기다리는 요청 수
_running   = False               # 현재 작업이 실행 중인지 여부

_MAX_WAIT    = 3      # 대기열 최대 크기
_JOB_TIMEOUT = 300   # 대기 최대 시간(초)
_MAX_DIM     = 1536  # 허용 최대 이미지 한 변 크기(px)
_BODY_LIMIT  = 16 * 1024  # 요청 본문 최대 크기(16 KB)


# ── 대기열 헬퍼 ───────────────────────────────────────────────────────────────
def _inc_waiting() -> bool:
    """대기열에 추가한다. 이미 꽉 찼으면 False."""
    global _waiting
    with _state_lock:
        if _waiting >= _MAX_WAIT:
            return False
        _waiting += 1
        return True


def _dec_waiting():
    global _waiting
    with _state_lock:
        _waiting -= 1


def _set_running(val: bool):
    global _running
    with _state_lock:
        _running = val


def _is_busy() -> bool:
    with _state_lock:
        return _running


# ── 설정 헬퍼 (lazy – 테스트에서 환경변수를 덮어쓸 수 있다) ─────────────────────
def _get_host() -> str:
    return os.environ.get("IMAGE_API_HOST", "127.0.0.1")


def _get_port() -> int:
    return int(os.environ.get("IMAGE_API_PORT", "8790"))


def _get_token_file() -> Path:
    return Path(os.environ.get(
        "IMAGE_API_TOKEN_FILE",
        Path.home() / ".config" / "image-api" / "token",
    ))


def _read_token() -> bytes:
    p = _get_token_file()
    if not p.exists():
        raise FileNotFoundError(f"토큰 파일이 없습니다: {p}")
    return p.read_text().strip().encode()


def _find_mflux() -> str:
    override = os.environ.get("MFLUX_BIN", "")
    if override:
        return override
    search = os.environ.get("PATH", "").split(":") + [str(Path.home() / ".local" / "bin")]
    for d in search:
        p = Path(d) / "mflux-generate"
        if p.is_file():
            return str(p)
    return "mflux-generate"


# ── 크기 검증 ─────────────────────────────────────────────────────────────────
def _parse_size(size_str: str) -> tuple[int, int]:
    """'WxH' 형식을 파싱한다. 조건에 맞지 않으면 ValueError."""
    try:
        w_s, h_s = size_str.lower().split("x")
        w, h = int(w_s), int(h_s)
    except (ValueError, AttributeError):
        raise ValueError(f"size 형식이 올바르지 않습니다: {size_str!r}  (예: '1216x640')")
    for dim, name in ((w, "너비"), (h, "높이")):
        if dim <= 0:
            raise ValueError(f"{name}({dim})은 양수여야 합니다.")
        if dim % 16 != 0:
            raise ValueError(f"{name}({dim})은 16 의 배수여야 합니다.")
        if dim > _MAX_DIM:
            raise ValueError(f"{name}({dim})이 최대 {_MAX_DIM} 를 넘습니다.")
    return w, h


# ── mflux 실행 ────────────────────────────────────────────────────────────────
def _run_mflux(prompt: str, width: int, height: int, steps: int, seed) -> str:
    """mflux-generate 를 실행하고 결과 PNG 를 base64 로 돌려준다."""
    model_dir = os.environ.get("FLUX_MODEL_DIR", "").strip()
    if not model_dir:
        raise EnvironmentError("FLUX_MODEL_DIR 환경변수가 설정돼 있지 않습니다.")

    mflux = _find_mflux()
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "out.png"
        cmd = [
            mflux,
            "-m", model_dir,
            "--base-model", "schnell",
            "--low-ram",
            "--prompt", prompt,
            "--width", str(width),
            "--height", str(height),
            "--steps", str(steps),
            "--output", str(out_path),
        ]
        if seed is not None:
            cmd += ["--seed", str(int(seed))]
        subprocess.run(cmd, timeout=300, check=True, capture_output=True)
        return base64.b64encode(out_path.read_bytes()).decode()


# ── HTTP 핸들러 ───────────────────────────────────────────────────────────────
class _Handler(BaseHTTPRequestHandler):
    server_version = "image-api/1"
    sys_version    = ""

    def log_message(self, fmt, *args):  # noqa: N802
        pass  # 요청당 1줄은 _log() 로 직접 남긴다

    def _log(self, status: int, size_str: str, elapsed: float, note: str = ""):
        t = time.strftime("%Y-%m-%dT%H:%M:%S")
        msg = f"{t} {status} {size_str or '-'} {elapsed:.1f}s"
        if note:
            msg += f"  {note}"
        print(msg, file=sys.stderr, flush=True)

    def _json(self, code: int, body: dict):
        data = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _error(self, code: int, msg: str, err_type: str = "server_error"):
        self._json(code, {"error": {"message": msg, "type": err_type}})

    def _check_auth(self) -> bool:
        """Bearer 토큰을 검증한다. 실패 시 응답을 보내고 False 를 돌려준다."""
        try:
            expected = _read_token()
        except FileNotFoundError as e:
            self._error(500, str(e), "configuration_error")
            return False
        hdr = self.headers.get("Authorization", "")
        scheme, _, token = hdr.partition(" ")
        if scheme.lower() != "bearer" or not token:
            self._error(401, "Authorization 헤더가 없거나 Bearer 형식이 아닙니다.", "auth_error")
            return False
        if not hmac.compare_digest(expected, token.strip().encode()):
            self._error(401, "토큰이 올바르지 않습니다.", "auth_error")
            return False
        return True

    def do_GET(self):  # noqa: N802
        if self.path == "/health":
            self._json(200, {"ok": True, "busy": _is_busy()})
        else:
            self._error(404, "Not found", "not_found")

    def do_POST(self):  # noqa: N802
        if self.path != "/v1/images/generations":
            self._error(404, "Not found", "not_found")
            return

        # ── 본문 크기 제한 ──────────────────────────────────────────────────
        try:
            content_length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            content_length = 0
        if content_length > _BODY_LIMIT:
            self._error(400, f"요청 본문이 {_BODY_LIMIT // 1024} KB 를 넘습니다.", "invalid_request")
            return

        # ── 인증 ────────────────────────────────────────────────────────────
        if not self._check_auth():
            return

        t0 = time.monotonic()

        # ── 본문 파싱 ────────────────────────────────────────────────────────
        try:
            raw = self.rfile.read(min(content_length, _BODY_LIMIT))
            body = json.loads(raw)
        except Exception as e:
            self._error(400, f"JSON 파싱 오류: {e}", "invalid_request")
            return

        prompt = str(body.get("prompt", "")).strip()
        if not prompt:
            self._error(400, "prompt 가 없습니다.", "invalid_request")
            return

        size_str = str(body.get("size", "1216x640"))
        try:
            width, height = _parse_size(size_str)
        except ValueError as e:
            self._error(400, str(e), "invalid_request")
            return

        if body.get("n", 1) != 1:
            self._error(400, "n 은 1 만 지원합니다.", "invalid_request")
            return

        seed  = body.get("seed")
        steps = int(body.get("steps", 4))

        # ── 대기열 확인 ──────────────────────────────────────────────────────
        if not _inc_waiting():
            self._log(429, size_str, 0.0, "queue_full")
            self._error(429, "서버가 바쁩니다. 잠시 후 다시 시도하세요.", "rate_limit")
            return

        acquired = _job_lock.acquire(timeout=_JOB_TIMEOUT)
        _dec_waiting()

        if not acquired:
            elapsed = time.monotonic() - t0
            self._log(429, size_str, elapsed, "queue_timeout")
            self._error(429, "대기 시간이 초과됐습니다. 잠시 후 다시 시도하세요.", "rate_limit")
            return

        _set_running(True)
        try:
            b64 = _run_mflux(prompt, width, height, steps, seed)
            elapsed = time.monotonic() - t0
            self._log(200, size_str, elapsed)
            self._json(200, {
                "created": int(time.time()),
                "data": [{"b64_json": b64}],
            })
        except subprocess.TimeoutExpired:
            elapsed = time.monotonic() - t0
            self._log(500, size_str, elapsed, "mflux_timeout")
            self._error(500, "이미지 생성 시간이 초과됐습니다.", "server_error")
        except Exception as e:
            elapsed = time.monotonic() - t0
            self._log(500, size_str, elapsed, type(e).__name__)
            self._error(500, f"이미지 생성 오류: {type(e).__name__}", "server_error")
        finally:
            _set_running(False)
            _job_lock.release()


def main():
    host = _get_host()
    port = _get_port()
    server = ThreadingHTTPServer((host, port), _Handler)
    print(f"이미지 API 시작: http://{host}:{port}", file=sys.stderr, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
