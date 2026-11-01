#!/usr/bin/env python3
"""맥북 로컬 웹 UI 및 프록시 서버.

맥미니 이미지 API(tools/image-api/server.py) 앞에 놓이는 로컬 서버입니다.
- 브라우저에 이미지 생성 UI 를 제공합니다 (tools/image-api/web/index.html)
- 토큰은 이 서버가 보관하고 요청에 추가합니다 (브라우저에 노출되지 않습니다)
- 맥미니가 연결되지 않으면 502 를 반환합니다

환경 변수:
  LOCAL_IMAGE_URL      업스트림 맥미니 주소 (기본: http://100.123.77.30:8790)
  IMAGE_API_TOKEN_FILE 토큰 파일 경로 (기본: ~/.config/image-api/mini-token)
  IMAGE_WEB_PORT       바인딩 포트 (기본: 8793)

사용: python3 tools/image-api/web.py
     브라우저에서 http://127.0.0.1:8793 를 열면 됩니다.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent


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


class _Handler(BaseHTTPRequestHandler):
    server_version = "image-web/1"
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
            # 토큰을 로그에 남기지 않는다

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

    def do_GET(self):  # noqa: N802
        if self.path == "/":
            self._send_file(HERE / "web" / "index.html", "text/html; charset=utf-8")
        elif self.path == "/styles.json":
            self._send_file(HERE / "styles.json", "application/json; charset=utf-8")
        elif self.path == "/health":
            self._proxy("GET", "/health", None, add_auth=False)
        else:
            self._error(404, "Not found", "not_found")

    def do_POST(self):  # noqa: N802
        if self.path == "/v1/images/generations":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
            except ValueError:
                content_length = 0
            body = self.rfile.read(content_length) if content_length > 0 else None
            self._proxy("POST", "/v1/images/generations", body, add_auth=True)
        else:
            self._error(404, "Not found", "not_found")


def main():
    port = _get_port()
    server = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
    print(f"이미지 웹 서버 시작: http://127.0.0.1:{port}", file=sys.stderr, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
