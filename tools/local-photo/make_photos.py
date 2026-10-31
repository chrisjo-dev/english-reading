#!/usr/bin/env python3
"""맥 미니에서 FLUX.1 schnell 로 content/<lang>/<day>.photo.jpg 를 생성해 main 에 push 한다.

실행 조건: Asia/Seoul 05:00~11:00 (--day 또는 --lang 옵션이 있으면 시간 무관)

사용:
  python3 make_photos.py                             # 오늘 날짜 전체 언어 자동 실행
  python3 make_photos.py --day 2026-10-31            # 특정 날짜, 전체 언어
  python3 make_photos.py --day 2026-10-31 --lang en  # 특정 날짜, 특정 언어
  python3 make_photos.py --day 2026-10-31 --dry-run  # 생성만, git 조작 없이 /tmp 에 저장

환경 변수:
  FLUX_MODEL_DIR  FLUX 4비트 모델 디렉터리 경로 (필수)
  MFLUX_BIN       mflux-generate 명령 경로 (기본: mflux-generate)
"""
import argparse
import fcntl
import hashlib
import json
import logging
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

# 저장소 루트: tools/local-photo/ 에서 두 단계 위
REPO = Path(__file__).resolve().parent.parent.parent
LOCK_FILE = Path(tempfile.gettempdir()) / "read-photo.lock"
LOG_PATH = Path.home() / "Library" / "Logs" / "read-photo.log"
ALL_LANGS = ["en", "ja", "de"]

# FLUX.1 스타일 프롬프트 앞부분: 글씨/로고 없는 사실적 사진
STYLE = (
    "Realistic full-bleed photograph that fills the entire frame edge to edge, "
    "no borders, no white margins, no frames. Natural light, shallow depth of field, "
    "one clear main subject shown large and prominent, calm composition. "
    "Absolutely no text, letters, numbers, logos or watermarks anywhere. "
    "Avoid signs, labels, screens and packaging with writing."
)

KST = timezone(timedelta(hours=9))


def setup_logging() -> logging.Logger:
    """파일(~/Library/Logs/read-photo.log)과 stdout 에 동시 출력하는 로거를 만든다."""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("read-photo")
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%dT%H:%M:%S")
    if not logger.handlers:
        fh = logging.FileHandler(LOG_PATH, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(fmt)
        logger.addHandler(sh)
    return logger


def seed_for(day: str, lang: str) -> int:
    """날짜+언어 조합에서 결정적(deterministic) 32비트 시드를 만든다."""
    return int.from_bytes(hashlib.sha256(f"{day}{lang}".encode()).digest()[:4], "big")


def find_targets(day: str, langs: list, repo: Path = None) -> list:
    """photo_scene 이 있고 .photo.jpg 가 아직 없는 (lang, day, scene) 목록을 돌려준다."""
    root = repo or REPO
    targets = []
    for lang in langs:
        json_path = root / "content" / lang / f"{day}.json"
        photo_path = root / "content" / lang / f"{day}.photo.jpg"
        if not json_path.exists():
            continue
        if photo_path.exists():
            continue
        try:
            c = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        scene = c.get("photo_scene", "")
        if isinstance(scene, str) and scene.strip():
            targets.append((lang, day, scene.strip()))
    return targets


def _png_to_jpg(src: Path, dst: Path, log: logging.Logger) -> None:
    """PNG 를 JPEG(품질 88, 1216x640)로 변환한다. Pillow 가 없으면 sips(macOS 내장)를 쓴다."""
    try:
        from PIL import Image
        img = Image.open(src).convert("RGB")
        img.save(dst, "JPEG", quality=88, optimize=True, progressive=True)
        log.info("PNG→JPEG 변환 완료: %s (%.0f KB)", dst.name, dst.stat().st_size / 1024)
    except ImportError:
        # Pillow 미설치 시 macOS 내장 sips 사용
        subprocess.run(
            ["sips", "-s", "format", "jpeg", "-s", "formatOptions", "88", str(src), "--out", str(dst)],
            check=True, capture_output=True,
        )
        log.info("PNG→JPEG 변환(sips) 완료: %s", dst.name)


def generate_one(lang: str, day: str, scene: str, out_jpg: Path, dry_run: bool,
                 log: logging.Logger) -> bool:
    """mflux-generate 로 사진을 생성하고 JPEG 로 변환한다. 성공하면 True."""
    model_dir = os.environ.get("FLUX_MODEL_DIR", "").strip()
    if not model_dir:
        log.error("FLUX_MODEL_DIR 환경 변수가 없습니다.")
        return False
    mflux_bin = os.environ.get("MFLUX_BIN", "mflux-generate")
    s = seed_for(day, lang)
    prompt_text = f"{STYLE}\nScene: {scene}"

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        prompt_file = tmp_path / "prompt.txt"
        prompt_file.write_text(prompt_text, encoding="utf-8")
        out_base = tmp_path / "out.png"

        cmd = [
            mflux_bin,
            "-m", model_dir,
            "--base-model", "schnell",
            "--low-ram",
            "--prompt-file", str(prompt_file),
            "--width", "1216",
            "--height", "640",
            "--steps", "4",
            "--seed", str(s),
            "--output", str(out_base),
        ]
        log.info("[%s/%s] mflux 실행 seed=%d scene=%.60s...", lang, day, s, scene)
        t0 = time.monotonic()
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        except subprocess.TimeoutExpired:
            log.error("[%s/%s] mflux 타임아웃(300초)", lang, day)
            return False
        elapsed = time.monotonic() - t0

        if result.returncode != 0:
            log.error("[%s/%s] mflux 실패(exit %d): %s", lang, day,
                      result.returncode, result.stderr[:300])
            return False

        # mflux 는 out.png 대신 out_00001.png 로 저장하는 경우가 있으므로 디렉터리에서 찾는다
        pngs = sorted(tmp_path.glob("*.png"))
        if not pngs:
            log.error("[%s/%s] PNG 파일이 생성되지 않았습니다", lang, day)
            return False
        actual_png = pngs[0]
        log.info("[%s/%s] 생성 완료 (%.0f초) → %s", lang, day, elapsed, actual_png.name)

        if dry_run:
            dry_out = Path(tempfile.gettempdir()) / f"{day}_{lang}.photo.jpg"
            _png_to_jpg(actual_png, dry_out, log)
            log.info("[%s/%s] dry-run: %s 에 저장 (커밋하지 않음)", lang, day, dry_out)
            return True

        out_jpg.parent.mkdir(parents=True, exist_ok=True)
        _png_to_jpg(actual_png, out_jpg, log)
        return True


def git_commit_push(added_files: list, day: str, committed_langs: list,
                    log: logging.Logger) -> None:
    """추가된 jpg 파일들을 커밋하고 push 한다(최대 3회 재시도)."""
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}

    def git(*args):
        return subprocess.run(
            ["git", "-C", str(REPO)] + list(args),
            capture_output=True, text=True, env=env,
        )

    for f in added_files:
        r = git("add", str(f))
        if r.returncode != 0:
            log.error("git add 실패: %s\n%s", f, r.stderr[:200])
            return

    r = git("diff", "--cached", "--quiet")
    if r.returncode == 0:
        log.info("커밋할 변경 없음 (이미 커밋됐을 수 있음)")
        return

    langs_str = " ".join(committed_langs)
    msg = f"Add local photo {langs_str} {day} [skip ci]"
    r = git(
        "-c", "user.name=chrisjo",
        "-c", "user.email=wonsang.dev@gmail.com",
        "commit", "-m", msg,
        "--author=chrisjo <wonsang.dev@gmail.com>",
    )
    if r.returncode != 0:
        log.error("git commit 실패: %s", r.stderr[:200])
        return
    log.info("커밋: %s", msg)

    for attempt in range(1, 4):
        r = git("push", "origin", "HEAD:main")
        if r.returncode == 0:
            log.info("push 성공 (%d회 시도)", attempt)
            return
        log.warning("push 실패 (시도 %d/3): %s", attempt, r.stderr[:100])
        if attempt < 3:
            rb = git("pull", "--rebase", "origin", "main")
            if rb.returncode != 0:
                log.error("git pull --rebase 실패: %s", rb.stderr[:200])
                return
    log.error("push 3회 모두 실패")


def main() -> None:
    parser = argparse.ArgumentParser(description="FLUX.1 로컬 사진 생성 스크립트")
    parser.add_argument("--day", help="처리할 날짜 YYYY-MM-DD (생략 시 오늘 Asia/Seoul)")
    parser.add_argument("--lang", help="처리할 언어 코드 en/ja/de (생략 시 전체)")
    parser.add_argument("--dry-run", action="store_true",
                        help="생성만 하고 git 조작 없이 /tmp 에 저장")
    args = parser.parse_args()

    log = setup_logging()
    now_kst = datetime.now(KST)
    day = args.day or now_kst.strftime("%Y-%m-%d")
    langs = [args.lang] if args.lang else ALL_LANGS

    # 시간 제한: --day/--lang 옵션 없을 때만 05:00~11:00(KST) 에 실행
    if not args.day and not args.lang:
        h = now_kst.hour
        if not (5 <= h < 11):
            sys.exit(0)  # 조용히 종료

    # 락 파일: 동시에 두 프로세스가 실행되지 않도록 한다
    lock_fd = open(LOCK_FILE, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        log.info("다른 프로세스가 실행 중입니다. 건너뜁니다.")
        sys.exit(0)

    try:
        # git pull --rebase 로 최신 상태를 받아온다
        if not args.dry_run:
            r = subprocess.run(
                ["git", "-C", str(REPO), "pull", "--rebase", "origin", "main"],
                capture_output=True, text=True,
                env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
            )
            if r.returncode != 0:
                log.error("git pull --rebase 실패: %s", r.stderr[:200])
                sys.exit(1)

        targets = find_targets(day, langs)
        if not targets:
            log.info("%s: 생성할 대상 없음 (photo_scene 없거나 이미 생성됨)", day)
            sys.exit(0)

        log.info("%s: 대상 %d건 — %s", day, len(targets),
                 [f"{l}" for l, _, _ in targets])

        added = []
        done_langs = []
        for lang, d, scene in targets:
            out_jpg = REPO / "content" / lang / f"{d}.photo.jpg"
            ok = generate_one(lang, d, scene, out_jpg, args.dry_run, log)
            if ok and not args.dry_run:
                added.append(out_jpg)
                done_langs.append(lang)

        if added:
            git_commit_push(added, day, done_langs, log)

    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()


if __name__ == "__main__":
    main()
