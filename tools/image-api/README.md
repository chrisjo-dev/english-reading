# image-api

맥 미니에서 FLUX.1 schnell 이미지를 생성하는 로컬 HTTP 서버입니다.
GitHub Actions 워크플로가 Tailscale 로 맥 미니에 접근해 이미지를 받아 갑니다.

## 구성 파일

| 파일 | 설명 |
|------|------|
| `server.py` | HTTP 서버 본체 (stdlib + mflux subprocess) |
| `com.chrisjo.image-api.plist.template` | LaunchAgent 템플릿 |
| `install.sh` | 맥 미니에서 한 번 실행하면 서비스가 등록됩니다 |

## 엔드포인트

### `GET /health`

인증 불필요. 서버 상태를 반환합니다.

```bash
curl http://100.123.77.30:8790/health
```

```json
{"ok": true, "busy": false}
```

### `POST /v1/images/generations`

`Authorization: Bearer <token>` 헤더 필요.

요청 본문:
```json
{
  "prompt": "A scientist examining crystals under a microscope.",
  "size": "1216x640",
  "steps": 4,
  "seed": 42
}
```

- `size`: `"WxH"` (기본 `"1216x640"`; 각 변 16 배수, 최대 1536)
- `n`: 1 만 허용
- `steps`: 기본 4 (schnell 권장값)
- `seed`: 선택 사항; 생략하면 매번 다른 이미지가 생성됩니다

응답:
```json
{
  "created": 1730300000,
  "data": [{"b64_json": "<PNG base64>"}]
}
```

오류 응답은 OpenAI 형식과 같습니다:
```json
{"error": {"message": "...", "type": "..."}}
```

```bash
TOKEN=$(cat ~/.config/image-api/token)
curl -s http://100.123.77.30:8790/v1/images/generations \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"A sunny mountain trail.","size":"1216x640"}' \
  | python3 -c "import sys,json,base64; d=json.load(sys.stdin); open('/tmp/out.png','wb').write(base64.b64decode(d['data'][0]['b64_json']))"
```

## 다른 프로젝트에서 호출하기

```python
import base64, io, json, os, urllib.request
from PIL import Image

url   = os.environ["LOCAL_IMAGE_URL"]   # http://100.123.77.30:8790
token = os.environ["LOCAL_IMAGE_TOKEN"]

body = json.dumps({"prompt": "...", "size": "1216x640"}).encode()
req  = urllib.request.Request(
    url + "/v1/images/generations", body,
    {"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
)
r   = json.loads(urllib.request.urlopen(req, timeout=300).read())
img = Image.open(io.BytesIO(base64.b64decode(r["data"][0]["b64_json"])))
```

## 설치 (맥 미니에서 실행)

```bash
bash tools/image-api/install.sh 100.123.77.30 /Users/chrisjo/models/schnell-q4
```

설치 후 토큰 값:
```bash
cat ~/.config/image-api/token
```

이 값을 GitHub 저장소의 `LOCAL_IMAGE_TOKEN` 시크릿에 등록하세요.

## 토큰 교체

```bash
openssl rand -hex 32 > ~/.config/image-api/token
chmod 600 ~/.config/image-api/token
# 서비스 재시작
launchctl bootout "gui/$(id -u)/com.chrisjo.image-api"
launchctl bootstrap "gui/$(id -u)" ~/Library/LaunchAgents/com.chrisjo.image-api.plist
# GitHub 시크릿 LOCAL_IMAGE_TOKEN 도 새 값으로 업데이트하세요
```

## 서비스 중지

```bash
launchctl bootout "gui/$(id -u)/com.chrisjo.image-api"
```

## Tailscale ACL 권장 설정

포트 8790 은 CI 태그와 소유자 기기에서만 접근할 수 있게 제한합니다.

```json
{
  "acls": [
    {
      "action": "accept",
      "src": ["tag:ci", "autogroup:owner"],
      "dst": ["100.123.77.30:8790"]
    }
  ]
}
```

## 환경 변수 (서버)

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `FLUX_MODEL_DIR` | (필수) | mflux 모델 디렉터리 |
| `IMAGE_API_TOKEN_FILE` | `~/.config/image-api/token` | 토큰 파일 경로 |
| `IMAGE_API_HOST` | `127.0.0.1` | 바인딩 주소 (plist 에서 Tailscale IP 로 설정) |
| `IMAGE_API_PORT` | `8790` | 바인딩 포트 |
| `MFLUX_BIN` | PATH 자동 탐색 | mflux-generate 실행 파일 경로 |
