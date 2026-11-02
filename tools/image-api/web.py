#!/usr/bin/env python3
"""맥북 로컬 웹 UI 및 프록시 서버.

맥미니 이미지 API(tools/image-api/server.py) 앞에 놓이는 로컬 서버입니다.
- 브라우저에 이미지 생성 UI 를 제공합니다 (tools/image-api/web/index.html)
- 토큰은 이 서버가 보관하고 요청에 추가합니다 (브라우저에 노출되지 않습니다)
- 맥미니가 연결되지 않으면 502 를 반환합니다
- 한국어 장면 설명을 로컬 LLM(Qwen3-8B)으로 영어로 번역합니다
- 생성된 이미지를 IMAGE_WEB_DIR 에 자동 저장합니다

환경 변수:
  LOCAL_IMAGE_URL      업스트림 맥미니 주소 (기본: http://100.123.77.30:8790)
  IMAGE_API_TOKEN_FILE 토큰 파일 경로 (기본: ~/.config/image-api/mini-token)
  IMAGE_WEB_PORT       바인딩 포트 (기본: 8793)
  IMAGE_WEB_DIR        저장 폴더 (기본: ~/Pictures/mini-image)

사용: ~/.local/share/uv/tools/mlx-lm/bin/python tools/image-api/web.py
     브라우저에서 http://127.0.0.1:8793 를 열면 됩니다.
"""

import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

HERE = Path(__file__).resolve().parent

# ── 저장 디렉터리 ──────────────────────────────────────────────────────────────
def _get_save_dir() -> Path:
    return Path(os.environ.get(
        "IMAGE_WEB_DIR",
        Path.home() / "Pictures" / "mini-image",
    )).expanduser()

# ── 업스트림 / 포트 / 토큰 ─────────────────────────────────────────────────────
def _get_upstream() -> str:
    return os.environ.get("LOCAL_IMAGE_URL", "http://100.123.77.30:8790").rstrip("/")


def _get_port() -> int:
    return int(os.environ.get("IMAGE_WEB_PORT", "8793"))


def _get_token_file() -> Path:
    return Path(os.environ.get(
        "IMAGE_API_TOKEN_FILE",
        Path.home() / ".config" / "image-api" / "mini-token",
    ))


def _read_token() -> str:
    p = _get_token_file()
    if not p.exists():
        raise FileNotFoundError(p)
    return p.read_text().strip()


# ── 번역 (mlx_lm, 지연 로드) ──────────────────────────────────────────────────
_TRANSLATE_LOCK = threading.Lock()
_mlx_model      = None
_mlx_tokenizer  = None

_SYSTEM_PROMPT = (
    "You turn a short Korean (or English) image idea into ONE English sentence "
    "describing a realistic photo scene for an image model. Say what the main "
    "subject is, where it is, the time of day or light, and how close the camera "
    "is. Describe what is literally visible; never use metaphors. If there are two "
    "subjects, keep them together in one place. If the idea is abstract, show it as "
    "one concrete everyday scene. No text or signs in the scene. First understand "
    "the Korean meaning carefully (e.g. 물가 means consumer prices, not water). "
    "Keep it natural and emotionally fitting; do not invent odd details or numbers. "
    "Output only the sentence, 20 to 45 words."
)

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def _load_mlx():
    """mlx_lm 모델을 한 번만 로드한다. 없으면 ImportError 를 전파한다."""
    global _mlx_model, _mlx_tokenizer
    if _mlx_model is not None:
        return
    import mlx_lm  # noqa: PLC0415
    _mlx_model, _mlx_tokenizer = mlx_lm.load("Qwen/Qwen3-8B-MLX-4bit")


def translate_text(text: str) -> "tuple[str, float]":
    """한국어(또는 영어) 텍스트를 영어 장면 설명으로 변환한다.

    Returns:
        (scene, seconds) 튜플.

    Raises:
        ImportError: mlx_lm 이 설치되지 않은 경우.
    """
    with _TRANSLATE_LOCK:
        _load_mlx()
        import mlx_lm  # noqa: PLC0415
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user",   "content": text},
        ]
        prompt = _mlx_tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
        t0 = time.monotonic()
        result = mlx_lm.generate(
            _mlx_model,
            _mlx_tokenizer,
            prompt=prompt,
            max_tokens=120,
            verbose=False,
        )
        secs = time.monotonic() - t0

    # <think>…</think> 제거, 앞뒤 따옴표/공백 제거
    scene = _THINK_RE.sub("", result).strip().strip('"\'')
    return scene, round(secs, 1)


# ── 자동 저장 ─────────────────────────────────────────────────────────────────
_KST = timezone(timedelta(hours=9))


def _save_result(b64_data: bytes, meta: dict) -> None:
    """PNG 와 JSON 사이드카를 IMAGE_WEB_DIR 에 저장한다."""
    import base64
    save_dir = _get_save_dir()
    now_kst   = datetime.now(_KST)
    date_str  = now_kst.strftime("%Y-%m-%d")
    time_str  = now_kst.strftime("%H%M%S")
    seed      = meta.get("seed", 0)

    day_dir = save_dir / date_str
    day_dir.mkdir(parents=True, exist_ok=True)

    base_stem = f"{time_str}-{seed}"
    png_path  = day_dir / f"{base_stem}.png"
    json_path = day_dir / f"{base_stem}.json"

    # 절대 덮어쓰지 않는다
    suffix = 0
    while png_path.exists() or json_path.exists():
        suffix += 1
        png_path  = day_dir / f"{base_stem}-{suffix}.png"
        json_path = day_dir / f"{base_stem}-{suffix}.json"

    try:
        png_bytes = base64.b64decode(b64_data)
        png_path.write_bytes(png_bytes)
    except Exception:
        return

    sidecar = dict(meta)
    sidecar["created"] = now_kst.isoformat()
    try:
        json_path.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2))
    except Exception:
        pass  # PNG 는 저장됐으므로 JSON 실패는 무시


# ── 히스토리 ──────────────────────────────────────────────────────────────────
def _collect_history(offset: int = 0, limit: int = 24) -> "list[dict]":
    """저장 폴더에서 최신 순으로 항목을 모아 반환한다."""
    save_dir = _get_save_dir()
    if not save_dir.exists():
        return []

    entries = []
    for json_path in sorted(save_dir.rglob("*.json"), reverse=True):
        try:
            meta = json.loads(json_path.read_text())
        except Exception:
            continue
        png_path = json_path.with_suffix(".png")
        if not png_path.exists():
            continue
        # 상대 URL: /files/<date>/<stem>.png
        rel = png_path.relative_to(save_dir)
        parts = rel.parts  # ('2026-11-02', '120000-1234.png')
        if len(parts) != 2:
            continue
        meta["url"]      = f"/files/{parts[0]}/{parts[1]}"
        meta["filename"] = parts[1]
        meta["date"]     = parts[0]
        entries.append(meta)

    return entries[offset: offset + limit]


# ── 경로 안전 확인 ─────────────────────────────────────────────────────────────
def _safe_file_path(date_seg: str, name_seg: str) -> "Path | None":
    """date_seg/name_seg 가 save_dir 안에 있는지 확인한다. 이탈이면 None."""
    save_dir = _get_save_dir().resolve()
    # 세그먼트에 /.. 가 포함되면 거부
    if ".." in date_seg or ".." in name_seg:
        return None
    candidate = (save_dir / date_seg / name_seg).resolve()
    try:
        candidate.relative_to(save_dir)
    except ValueError:
        return None
    return candidate


# ── HTTP 핸들러 ───────────────────────────────────────────────────────────────
class _Handler(BaseHTTPRequestHandler):
    server_version = "image-web/2"
    sys_version    = ""

    def log_message(self, fmt, *args):  # noqa: N802
        pass

    def _send_file(self, path: Path, content_type: str):
        try:
            data = path.read_bytes()
        except FileNotFoundError:
            self._error(404, "Not found")
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self, code: int, body: dict):
        data = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _error(self, code: int, msg: str, err_type: str = "server_error"):
        self._json(code, {"error": {"message": msg, "type": err_type}})

    def _proxy(self, method: str, path: str, body, add_auth: bool):
        """업스트림 맥미니로 요청을 전달한다. 연결 실패 시 502 를 반환한다."""
        url = _get_upstream() + path
        headers: dict = {}
        if body:
            headers["Content-Type"] = self.headers.get("Content-Type", "application/json")
        if add_auth:
            try:
                token = _read_token()
            except FileNotFoundError as e:
                self._error(500, f"토큰 파일이 없습니다: {e}. ~/.config/image-api/mini-token 을 확인하세요.")
                return
            headers["Authorization"] = f"Bearer {token}"

        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=330) as resp:
                data = resp.read()
                self.send_response(resp.status)
                self.send_header("Content-Type", resp.headers.get("Content-Type", "application/json"))
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
        except urllib.error.HTTPError as e:
            data = e.read()
            self.send_response(e.code)
            self.send_header("Content-Type", e.headers.get("Content-Type", "application/json"))
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except (OSError, urllib.error.URLError):
            self._error(502, "맥미니에 연결할 수 없습니다. Tailscale 연결과 맥미니 전원을 확인하세요.")

    def _proxy_and_save(self, body_bytes: bytes):
        """이미지 생성 요청을 전달하고 성공 시 자동 저장한다."""
        url = _get_upstream() + "/v1/images/generations"
        headers = {"Content-Type": "application/json"}
        try:
            token = _read_token()
        except FileNotFoundError as e:
            self._error(500, f"토큰 파일이 없습니다: {e}.")
            return
        headers["Authorization"] = f"Bearer {token}"

        try:
            req_body = json.loads(body_bytes)
        except Exception:
            req_body = {}

        req = urllib.request.Request(url, data=body_bytes, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=330) as resp:
                data = resp.read()
                self.send_response(resp.status)
                self.send_header("Content-Type", resp.headers.get("Content-Type", "application/json"))
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                # 성공 시 자동 저장
                try:
                    resp_json = json.loads(data)
                    b64 = resp_json.get("data", [{}])[0].get("b64_json")
                    if b64:
                        meta = {
                            "idea":    req_body.get("_idea", req_body.get("prompt", "")),
                            "scene":   req_body.get("_scene", req_body.get("prompt", "")),
                            "style":   req_body.get("_style", ""),
                            "size":    req_body.get("size", ""),
                            "seed":    resp_json.get("seed", req_body.get("seed", 0)),
                            "seconds": round(resp_json.get("seconds", 0), 1),
                            "prompt":  req_body.get("prompt", ""),
                        }
                        threading.Thread(
                            target=_save_result, args=(b64, meta), daemon=True
                        ).start()
                except Exception:
                    pass
        except urllib.error.HTTPError as e:
            data = e.read()
            self.send_response(e.code)
            self.send_header("Content-Type", e.headers.get("Content-Type", "application/json"))
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except (OSError, urllib.error.URLError):
            self._error(502, "맥미니에 연결할 수 없습니다. Tailscale 연결과 맥미니 전원을 확인하세요.")

    def do_GET(self):  # noqa: N802
        parsed = urlparse(self.path)
        path   = parsed.path

        if path == "/":
            self._send_file(HERE / "web" / "index.html", "text/html; charset=utf-8")
        elif path == "/styles.json":
            self._send_file(HERE / "styles.json", "application/json; charset=utf-8")
        elif path == "/health":
            self._proxy("GET", "/health", None, add_auth=False)
        elif path == "/history":
            qs     = parse_qs(parsed.query)
            offset = int((qs.get("offset", ["0"])[0]) or 0)
            limit  = int((qs.get("limit",  ["24"])[0]) or 24)
            limit  = min(limit, 100)
            items  = _collect_history(offset, limit)
            self._json(200, {"items": items, "offset": offset, "limit": limit, "count": len(items)})
        elif path.startswith("/files/"):
            # /files/<date>/<name>.png
            parts = path[len("/files/"):].split("/", 1)
            if len(parts) != 2 or not parts[1].endswith(".png"):
                self._error(400, "잘못된 파일 경로입니다.", "bad_request")
                return
            file_path = _safe_file_path(parts[0], parts[1])
            if file_path is None:
                self._error(403, "허용되지 않는 경로입니다.", "forbidden")
                return
            self._send_file(file_path, "image/png")
        else:
            self._error(404, "Not found", "not_found")

    def do_POST(self):  # noqa: N802
        if self.path == "/v1/images/generations":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
            except ValueError:
                content_length = 0
            body = self.rfile.read(content_length) if content_length > 0 else b""
            self._proxy_and_save(body)
        elif self.path == "/translate":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
            except ValueError:
                content_length = 0
            body_bytes = self.rfile.read(content_length) if content_length > 0 else b"{}"
            try:
                body_json = json.loads(body_bytes)
            except Exception:
                self._error(400, "JSON 파싱 오류입니다.", "bad_request")
                return
            text = (body_json.get("text") or "").strip()
            if not text:
                self._error(400, "text 필드가 필요합니다.", "bad_request")
                return
            try:
                scene, secs = translate_text(text)
                self._json(200, {"scene": scene, "seconds": secs})
            except ImportError:
                self._error(501, "이 환경에는 mlx_lm 이 설치되어 있지 않습니다. mlx-lm python 으로 실행하세요.")
            except Exception as exc:
                self._error(500, f"번역 오류: {exc}")
        else:
            self._error(404, "Not found", "not_found")


def main():
    port = _get_port()
    save_dir = _get_save_dir()
    server = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
    print(f"이미지 웹 서버 시작: http://127.0.0.1:{port}", file=sys.stderr, flush=True)
    print(f"자동 저장 폴더: {save_dir}", file=sys.stderr, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
