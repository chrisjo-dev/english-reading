#!/usr/bin/env bash
# setup-mini.sh: 맥 미니에서 FLUX.1 로컬 사진 생성 LaunchAgent 를 설정한다.
# sudo 없이 실행 가능하며, 반복 실행해도 안전한 idempotent 스크립트다.
#
# 사용법:
#   bash setup-mini.sh <저장소 경로> <FLUX 모델 디렉터리>
#
# 예시:
#   bash setup-mini.sh ~/repos/english-reading ~/models/flux-schnell-q4

set -euo pipefail

REPO_PATH="${1:-}"
FLUX_MODEL_DIR="${2:-}"

# --- 인자 확인 ---
if [ -z "$REPO_PATH" ] || [ -z "$FLUX_MODEL_DIR" ]; then
    echo "사용법: bash setup-mini.sh <저장소 경로> <FLUX 모델 디렉터리>"
    echo "예시:   bash setup-mini.sh ~/repos/english-reading ~/models/flux-schnell-q4"
    exit 1
fi

# 절대 경로로 변환
REPO_PATH="$(cd "$REPO_PATH" 2>/dev/null && pwd || echo "$REPO_PATH")"
FLUX_MODEL_DIR="$(cd "$FLUX_MODEL_DIR" 2>/dev/null && pwd || echo "$FLUX_MODEL_DIR")"

echo "=== 맥 미니 로컬 사진 생성 설정 ==="
echo "저장소: $REPO_PATH"
echo "모델:   $FLUX_MODEL_DIR"
echo ""

# --- Apple Silicon 확인 ---
ARCH="$(uname -m)"
if [ "$ARCH" != "arm64" ]; then
    echo "경고: Apple Silicon(arm64)이 아닙니다 (현재: $ARCH)."
    echo "      Intel Mac 에서도 동작하지만 속도가 느릴 수 있습니다."
fi

# --- 디스크 여유 공간 확인 (10GB 이상 권장) ---
AVAIL_GB="$(df -g / | awk 'NR==2 {print $4}')"
if [ "${AVAIL_GB:-0}" -lt 10 ] 2>/dev/null; then
    echo "경고: 루트 파티션 여유 공간이 ${AVAIL_GB}GB 입니다."
    echo "      4비트 모델 9GB + 작업 공간을 위해 최소 10GB 를 권장합니다."
fi

# --- uv 설치 여부 확인 ---
if ! command -v uv >/dev/null 2>&1; then
    echo ""
    echo "uv 가 설치되어 있지 않습니다."
    echo "공식 설치 명령어를 직접 실행하세요:"
    echo ""
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo ""
    echo "설치 후 셸을 재시작하고 이 스크립트를 다시 실행하세요."
    exit 1
fi
echo "uv 설치 확인: $(uv --version)"

# --- mflux 설치 ---
echo ""
echo "mflux 설치 중 (이미 설치돼 있으면 업그레이드)..."
uv tool install mflux --upgrade
MFLUX_BIN="$(uv tool run which mflux-generate 2>/dev/null || true)"
if [ -z "$MFLUX_BIN" ]; then
    # uv tool 경로에서 직접 찾기
    MFLUX_BIN="$(uv tool dir)/mflux/bin/mflux-generate"
fi
echo "mflux-generate 경로: $MFLUX_BIN"

# uv bin 디렉터리 (PATH 에 추가)
UV_BIN_DIR="$(dirname "$(uv tool run which mflux-generate 2>/dev/null || echo /usr/local/bin/mflux-generate)")"

# --- 저장소 확인 및 git push 권한 검증 ---
if [ ! -d "$REPO_PATH/.git" ]; then
    echo ""
    echo "저장소를 클론합니다..."
    PARENT="$(dirname "$REPO_PATH")"
    REPO_NAME="$(basename "$REPO_PATH")"
    git clone "https://github.com/chrisjo-dev/english-reading.git" "$PARENT/$REPO_NAME"
else
    echo ""
    echo "저장소 업데이트 중..."
    git -C "$REPO_PATH" pull --rebase origin main
fi

echo ""
echo "git push 권한 확인 중 (dry-run)..."
if git -C "$REPO_PATH" push --dry-run origin HEAD:main 2>/dev/null; then
    echo "push 권한 확인 완료"
else
    echo "경고: git push --dry-run 이 실패했습니다."
    echo "      SSH 키 또는 토큰이 설정되어 있는지 확인하세요."
    echo "      계속 진행하지만, LaunchAgent 실행 시 push 가 실패할 수 있습니다."
fi

# --- Python 경로 확인 ---
PYTHON="$(command -v python3)"
echo ""
echo "Python: $PYTHON ($(python3 --version))"

# --- LaunchAgent 폴더 ---
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
mkdir -p "$LAUNCH_AGENTS_DIR"

# --- 로그 디렉터리 ---
LOG_DIR="$HOME/Library/Logs"
mkdir -p "$LOG_DIR"
LOG_PATH="$LOG_DIR/read-photo.log"

# --- plist 렌더링 ---
PLIST_TEMPLATE="$(dirname "$0")/com.wspace.read-photo.plist.template"
PLIST_DST="$LAUNCH_AGENTS_DIR/com.wspace.read-photo.plist"

echo ""
echo "LaunchAgent plist 생성: $PLIST_DST"
sed \
    -e "s|__PYTHON__|$PYTHON|g" \
    -e "s|__REPO_PATH__|$REPO_PATH|g" \
    -e "s|__FLUX_MODEL_DIR__|$FLUX_MODEL_DIR|g" \
    -e "s|__UV_BIN_DIR__|$UV_BIN_DIR|g" \
    -e "s|__LOG_PATH__|$LOG_PATH|g" \
    "$PLIST_TEMPLATE" > "$PLIST_DST"

# plist 문법 검증
if command -v plutil >/dev/null 2>&1; then
    plutil -lint "$PLIST_DST" && echo "plist 문법 검증 통과"
fi

# --- LaunchAgent 등록 ---
LABEL="com.wspace.read-photo"
echo ""
echo "LaunchAgent 등록 중..."
# 이미 로드된 경우 먼저 해제
launchctl bootout "gui/$UID/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$UID" "$PLIST_DST"
echo "LaunchAgent 등록 완료"

# --- 모델 취득 안내 ---
echo ""
echo "======================================"
echo "FLUX 모델 취득 방법 (둘 중 하나 선택)"
echo "======================================"
echo ""
echo "방법 1: MacBook Air 에서 복사 (빠름, ~9GB)"
echo "  scp -r /Users/wonsang/test/english-reading/design/local-thumb/models/schnell-q4 \\"
echo "    $(hostname -s).$FLUX_MODEL_DIR"
echo "  또는 AirDrop 으로 schnell-q4 폴더 전체를 전송하세요."
echo ""
echo "방법 2: Hugging Face 에서 직접 다운로드 (~9GB, 시간 소요)"
echo "  uvx hf auth login"
echo "  mflux-save -m schnell -q 4 --path $FLUX_MODEL_DIR"
echo ""
echo "======================================"
echo "절전 모드 방지 설정 (중요)"
echo "======================================"
echo "  시스템 설정 > 디스플레이 > '디스플레이 끄기' 를 '안 함' 으로 설정하세요."
echo "  잠자기는 막지 않아도 되지만, '전원 어댑터 연결 시 절전 방지' 를 켜 두세요."
echo "  (이 설정은 스크립트가 자동으로 변경하지 않습니다.)"
echo ""
echo "설정 완료!"
echo ""
echo "LaunchAgent 상태 확인:  launchctl list $LABEL"
echo "로그 확인:              tail -f $LOG_PATH"
echo "수동 테스트:            python3 $REPO_PATH/tools/local-photo/make_photos.py --day YYYY-MM-DD --lang en --dry-run"
echo "비활성화:               launchctl bootout gui/$UID/$LABEL"
