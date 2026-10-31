#!/usr/bin/env bash
# 맥 미니에서 실행하면 이미지 API LaunchAgent 가 설치됩니다.
# 사용: bash install.sh <Tailscale_IP> <FLUX_모델_디렉터리>
# 예:   bash install.sh 100.123.77.30 /Users/chrisjo/models/schnell-q4
#
# sudo 없이 현재 사용자 계정에 설치합니다. 재실행해도 안전합니다(멱등).
set -euo pipefail

TAILNET_IP="${1:?첫 번째 인수로 Tailscale IP 를 지정하세요 (예: 100.123.77.30)}"
FLUX_MODEL_DIR="${2:?두 번째 인수로 FLUX 모델 디렉터리를 지정하세요}"

LABEL="com.chrisjo.image-api"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVER_PY="${SCRIPT_DIR}/server.py"
PLIST_TEMPLATE="${SCRIPT_DIR}/com.chrisjo.image-api.plist.template"
PLIST_DST="${HOME}/Library/LaunchAgents/${LABEL}.plist"
TOKEN_FILE="${HOME}/.config/image-api/token"
LOG_DIR="${HOME}/Library/Logs"

echo "=== 이미지 API 설치 시작 (${LABEL}) ==="

# ── mflux-generate 확인 ───────────────────────────────────────────────────────
if ! command -v mflux-generate >/dev/null 2>&1 && \
   ! [ -x "${HOME}/.local/bin/mflux-generate" ]; then
    if command -v uv >/dev/null 2>&1; then
        echo "mflux-generate 를 설치합니다 (uv tool install mflux)..."
        uv tool install mflux
    else
        echo "오류: mflux-generate 를 찾을 수 없고 uv 도 없습니다." >&2
        echo "https://docs.astral.sh/uv/ 에서 uv 를 설치하거나" >&2
        echo "pip install mflux 로 mflux 를 직접 설치하세요." >&2
        exit 1
    fi
fi
echo "mflux-generate 확인 완료"

# ── 토큰 파일 생성 (없을 때만 새로 만든다) ────────────────────────────────────
mkdir -p "$(dirname "${TOKEN_FILE}")"
if [ ! -f "${TOKEN_FILE}" ]; then
    openssl rand -hex 32 > "${TOKEN_FILE}"
    chmod 600 "${TOKEN_FILE}"
    echo "토큰 파일을 새로 만들었습니다: ${TOKEN_FILE}"
    echo "(토큰 값은 보안상 여기에 표시하지 않습니다. cat 으로 직접 확인하세요.)"
else
    echo "기존 토큰 파일을 그대로 씁니다: ${TOKEN_FILE}"
fi

# ── 로그 디렉터리 확인 ────────────────────────────────────────────────────────
mkdir -p "${HOME}/Library/LaunchAgents"
mkdir -p "${LOG_DIR}"

# ── plist 렌더링 ──────────────────────────────────────────────────────────────
sed \
    -e "s|__SERVER_PY__|${SERVER_PY}|g" \
    -e "s|__HOME__|${HOME}|g" \
    -e "s|__TAILNET_IP__|${TAILNET_IP}|g" \
    -e "s|__FLUX_MODEL_DIR__|${FLUX_MODEL_DIR}|g" \
    "${PLIST_TEMPLATE}" > "${PLIST_DST}"
echo "plist 설치: ${PLIST_DST}"

# ── 서비스 재시작 (bootout 실패는 무시) ──────────────────────────────────────
launchctl bootout "gui/$(id -u)/${LABEL}" 2>/dev/null || true
sleep 1
launchctl bootstrap "gui/$(id -u)" "${PLIST_DST}"
echo "서비스를 시작했습니다."
sleep 3

# ── 헬스 체크 ─────────────────────────────────────────────────────────────────
PORT="8790"
echo "헬스 체크: http://${TAILNET_IP}:${PORT}/health"
if curl -fsS "http://${TAILNET_IP}:${PORT}/health"; then
    echo ""
    echo "=== 설치 완료 ==="
else
    echo "" >&2
    echo "경고: Tailscale IP 로 헬스 체크 실패. 127.0.0.1 로 재시도합니다..." >&2
    curl -fsS "http://127.0.0.1:${PORT}/health" || \
        echo "경고: 서버가 아직 시작 중일 수 있습니다. 잠시 후 다시 확인하세요." >&2
fi

echo ""
echo "토큰 확인:  cat ${TOKEN_FILE}"
echo "로그 확인:  tail -f ${LOG_DIR}/image-api.log"
echo "서비스 중지: launchctl bootout gui/\$(id -u)/${LABEL}"
