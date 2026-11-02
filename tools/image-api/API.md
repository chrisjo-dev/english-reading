# 맥미니 이미지 API

맥 미니에서 FLUX.1 schnell 모델로 이미지를 생성하는 HTTP 서버입니다.
Tailscale 테일넷 안에서만 접근할 수 있습니다.

## 웹 UI 사용법

맥북에서 로컬 프록시 서버를 시작하면 토큰 없이 브라우저로 사용할 수 있습니다.

```bash
# mlx-lm 파이썬으로 실행해야 번역이 동작합니다
~/.local/share/uv/tools/mlx-lm/bin/python tools/image-api/web.py
```

브라우저에서 http://127.0.0.1:8793 을 열면 됩니다.

환경 변수:

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `LOCAL_IMAGE_URL` | `http://100.123.77.30:8790` | 맥미니 주소 |
| `IMAGE_API_TOKEN_FILE` | `~/.config/image-api/mini-token` | 토큰 파일 경로 |
| `IMAGE_WEB_PORT` | `8793` | 웹 서버 포트 |
| `IMAGE_WEB_DIR` | `~/Pictures/mini-image` | 이미지 자동 저장 폴더 |

### 번역 (한국어 → 영어 장면)

한국어로 장면을 입력하면 로컬 LLM(Qwen3-8B-MLX-4bit, mlx_lm)으로 영어 장면 문장을 만들어 FLUX 에 전달합니다.
mlx-lm python 으로 실행하지 않으면 번역 없이 501 을 반환합니다.

### 자동 저장

생성에 성공하면 서버가 `IMAGE_WEB_DIR` 에 자동 저장합니다.

```
~/Pictures/mini-image/
  YYYY-MM-DD/
    HHMMSS-<seed>.png     ← PNG 원본
    HHMMSS-<seed>.json    ← 메타데이터 사이드카
```

JSON 사이드카 필드: `created` (ISO, Asia/Seoul), `idea` (원문), `scene` (영어 장면), `style`, `size`, `seed`, `seconds`, `prompt`.
파일이 겹치면 `-1`, `-2` 접미사를 붙이며 절대 덮어쓰지 않습니다.

### 웹 UI 전용 엔드포인트

#### `POST /translate`

한국어(또는 영어) 텍스트를 영어 장면 설명으로 변환합니다.

```json
{ "text": "남자 아이가 우는 모습" }
```

응답:

```json
{ "scene": "A young boy sitting on a park bench, crying ...", "seconds": 2.8 }
```

mlx_lm 이 없으면 501 을 반환합니다.

#### `GET /history?offset=0&limit=24`

저장 폴더에서 최신 순으로 목록을 반환합니다.

```json
{
  "items": [
    {
      "created": "2026-11-02T12:00:00+09:00",
      "idea": "남자 아이가 우는 모습",
      "scene": "A young boy ...",
      "style": "thumbnail",
      "size": "1216x640",
      "seed": 42,
      "seconds": 91.0,
      "prompt": "...",
      "url": "/files/2026-11-02/120000-42.png",
      "filename": "120000-42.png",
      "date": "2026-11-02"
    }
  ],
  "offset": 0,
  "limit": 24,
  "count": 1
}
```

#### `GET /files/<date>/<name>.png`

저장된 이미지를 서빙합니다. `IMAGE_WEB_DIR` 바깥으로의 경로 이탈은 403 으로 거부합니다.

토큰은 `~/.config/image-api/mini-token` 파일에 넣어 두면 됩니다.
맥미니에서 `cat ~/.config/image-api/token` 으로 값을 확인하고, 맥북으로 옮길 때는
터미널에 직접 붙여넣거나 AirDrop 으로 파일을 전송하세요. 화면에 출력하거나 메모에 저장하지 마세요.

```bash
# 맥북에서 한 번만 실행 (맥미니 값을 붙여넣는다)
mkdir -p ~/.config/image-api
echo "붙여넣은_토큰값" > ~/.config/image-api/mini-token
chmod 600 ~/.config/image-api/mini-token
```

---

## 직접 API 호출

### 주소

```
http://100.123.77.30:8790
```

Tailscale 테일넷 안에서만 접근할 수 있습니다. 외부 인터넷에서는 연결되지 않습니다.

### 인증

모든 생성 요청에 `Authorization: Bearer <토큰>` 헤더가 필요합니다.
토큰 파일은 맥미니의 `~/.config/image-api/token` 에 있습니다.
다른 기기에 옮길 때는 화면에 출력하지 말고 파일 전송(scp, AirDrop)을 사용하세요.

---

### `GET /health`

인증 불필요. 서버 상태를 반환합니다.

```bash
curl http://100.123.77.30:8790/health
```

```json
{"ok": true, "busy": false}
```

`busy` 가 `true` 이면 이미지를 생성 중입니다. 생성은 한 번에 하나씩 처리합니다.

---

### `POST /v1/images/generations`

이미지를 생성합니다.

**요청 헤더**

```
Authorization: Bearer <토큰>
Content-Type: application/json
```

**요청 본문**

```json
{
  "prompt": "A scientist examining glowing crystals under a microscope in a clean laboratory.",
  "size": "1216x640",
  "steps": 4,
  "seed": 42,
  "n": 1
}
```

| 필드 | 필수 | 기본값 | 설명 |
|------|------|--------|------|
| `prompt` | 필수 | | 생성 프롬프트 |
| `size` | | `1216x640` | `"WxH"` 형식. 각 변은 16 의 배수, 최대 1536 |
| `steps` | | `4` | 1~50. schnell 권장값은 4 |
| `seed` | | 랜덤 | 재현용 시드. 생략하면 매번 다른 값이 선택됩니다 |
| `n` | | `1` | 1 만 지원합니다 |

**지원하는 크기**

| 이름 | 값 |
|------|----|
| 가로 (기본) | `1216x640` |
| 정사각 | `1024x1024` |
| 세로 | `640x1216` |

크기는 두 변 모두 16 의 배수여야 하며 최대 1536 입니다.

**응답**

```json
{
  "created": 1730300000,
  "data": [{"b64_json": "<PNG base64>"}],
  "seed": 42
}
```

`seed` 는 실제로 사용된 시드 정수입니다. 요청에 시드를 지정하지 않았더라도 응답에는 항상 포함됩니다.

**오류 응답**

OpenAI 형식을 따릅니다.

```json
{"error": {"message": "...", "type": "..."}}
```

| HTTP 코드 | 원인 |
|-----------|------|
| 400 | 잘못된 요청 (크기 오류, prompt 없음 등) |
| 401 | 토큰 없음 또는 토큰 불일치 |
| 429 | 대기열 초과 (최대 3개) 또는 대기 시간 초과 (300초) |
| 500 | mflux 오류 또는 서버 설정 오류 |

---

## 예제

### curl

```bash
TOKEN=$(cat ~/.config/image-api/mini-token)

curl -s http://100.123.77.30:8790/v1/images/generations \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"A sunny mountain trail with pine trees.","size":"1216x640","seed":7}' \
  | python3 -c "
import sys, json, base64
d = json.load(sys.stdin)
open('/tmp/out.png', 'wb').write(base64.b64decode(d['data'][0]['b64_json']))
print('시드:', d['seed'])
"
```

### Python (urllib)

```python
import base64, io, json, os, urllib.request
from PIL import Image

url   = "http://100.123.77.30:8790"
token = open(os.path.expanduser("~/.config/image-api/mini-token")).read().strip()

body = json.dumps({"prompt": "A foggy harbor at dawn.", "size": "1216x640"}).encode()
req  = urllib.request.Request(
    url + "/v1/images/generations",
    body,
    {"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
)
resp = json.loads(urllib.request.urlopen(req, timeout=300).read())
img  = Image.open(io.BytesIO(base64.b64decode(resp["data"][0]["b64_json"])))
print("시드:", resp["seed"])
img.save("out.png")
```

### JavaScript (fetch, 같은 출처 프록시 경유)

```js
// web.py 프록시를 통해 호출할 때 — 토큰 불필요
const resp = await fetch("/v1/images/generations", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ prompt: "A child reading under a tree.", size: "1216x640" }),
});
const data = await resp.json();
const img  = new Image();
img.src    = "data:image/png;base64," + data.data[0].b64_json;
console.log("시드:", data.seed);
```

### GitHub Actions (Tailscale 경유)

`tailscale/github-action` 으로 테일넷에 연결한 다음 API 를 호출합니다.

```yaml
- name: Tailscale 연결
  uses: tailscale/github-action@v3
  with:
    oauth-client-id:     ${{ secrets.TS_OAUTH_CLIENT_ID }}
    oauth-secret:        ${{ secrets.TS_OAUTH_SECRET }}
    tags:                tag:ci
    # OAuth 클라이언트에 Auth Keys: Write 권한이 있어야 합니다 (없으면 404 오류)

- name: 이미지 생성
  env:
    LOCAL_IMAGE_URL:   http://100.123.77.30:8790
    LOCAL_IMAGE_TOKEN: ${{ secrets.LOCAL_IMAGE_TOKEN }}
  run: |
    python3 tools/thumb.py en "$DATE"
```

**OAuth 클라이언트 설정**: Tailscale 콘솔 → Settings → OAuth clients → New client.
Scope 에 **Auth Keys: Write** 를 포함하고, 태그는 `tag:ci` 를 지정하세요.
Write 권한이 없으면 Actions 에서 404 "not found" 오류가 발생합니다 (이 오류의 원인이었습니다).

---

## 스타일 프리셋과 프롬프트 작성 규칙

스타일 프리셋은 `tools/image-api/styles.json` 에 정의되어 있습니다.
웹 UI 와 `thumb.py` 가 모두 이 파일에서 읽어 동기화합니다.

| 프리셋 | 설명 |
|--------|------|
| `thumbnail` | 썸네일 구도 (주인공 오른쪽, 왼쪽 여백) 포함한 FLUX 사진 스타일 |
| `photo` | 구도 지정 없이 사실적인 FLUX 사진 스타일 |
| `none` | 스타일 없음 (프롬프트를 그대로 사용) |

프롬프트 조립 방법 (웹 UI 와 동일):
```
prompt = styles[preset] + "\nScene: " + scene   # preset 이 none 이면 scene 만 사용
```

**프롬프트 작성 규칙**

- 주어, 장소, 빛, 거리 순서로 한 문장으로 씁니다.
- 비유 대신 실제 모습으로 씁니다. "희망의 상징" → "씨앗이 싹트는 흙".
- 여러 주인공은 함께 넣습니다. "A doctor and patient" (따로따로 쓰면 한 명만 나옵니다).
- 추상 주제는 구체적인 장면 하나로 바꿉니다. "AI 발전" → "A robot arm assembling a circuit board in a factory".

---

## 제한 사항

| 항목 | 값 |
|------|----|
| 동시 생성 | 1개 (직렬 처리) |
| 대기열 | 최대 3개 |
| 대기 시간 초과 | 300초 |
| 생성 소요 시간 | 약 90초 (1216x640, schnell 4-bit) |
| 요청 타임아웃 | 300초 |
| 크기 최대값 | 1536px (한 변) |
| 크기 조건 | 16 의 배수 |
| n | 1 만 지원 |
| steps | 1~50 |

---

## 문제 해결

| 증상 | 원인과 해결 |
|------|------------|
| HTTP 401 | 토큰이 없거나 틀렸습니다. `~/.config/image-api/token` (맥미니) 값을 확인하세요 |
| HTTP 429 | 대기열이 꽉 찼거나 대기 시간이 초과됐습니다. 잠시 후 다시 시도하세요 |
| HTTP 500 `CalledProcessError` | mflux 가 실행되지 않습니다. Python 버전을 확인하세요. Python 3.9 에 설치하면 오류가 납니다. `uv tool install --force --python 3.12 mflux==0.24.0` 로 재설치하세요 |
| GitHub Actions 404 | Tailscale OAuth 클라이언트에 **Auth Keys: Write** 권한이 없습니다. Tailscale 콘솔에서 클라이언트를 재발급하세요 |
| 맥미니 연결 안 됨 | Tailscale 상태를 확인하세요 (`tailscale status`). 맥미니가 켜져 있는지도 확인하세요 |
| 502 (웹 UI) | web.py 가 맥미니에 연결할 수 없습니다. Tailscale 과 맥미니 전원을 확인하세요 |
