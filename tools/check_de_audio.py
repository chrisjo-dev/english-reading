"""독일어 오디오 품질 검사 스크립트.

faster-whisper(tts_qwen.WHISPER_GATE_MODEL) 로 de/<day>/audio/ 의 모든 파일을 전사해
새 게이트 규칙을 통과하지 못하는 파일과 거의 무음인 파일을 보고한다.

사용:
  python3 tools/check_de_audio.py [--days 2026-10-30 ...]
  # days 없으면 de/ 아래 모든 날짜 검사

출력:
  - stdout: 검사 결과 표
  - REPORT_OUT 환경 변수 또는 --out 인수로 경로 지정 시 파일 저장

게이트 규칙:
  - 문장(s*, a*): 절대 단어 오류 수 ≤ 1 합격
  - 단어(w*, v*): compute_wer_word_clip == 0.0 이고 길이 ≥ 0.25초 합격
  - 추가: 길이 < 0.1초 이면 "거의 무음" 으로 별도 표시
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))


def _duration(f: Path) -> float:
    """ffprobe 로 오디오 길이(초)를 구한다."""
    try:
        out = subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(f)],
            stderr=subprocess.DEVNULL,
        )
        return float(out.strip())
    except Exception:
        return 0.0


def _load_content(day: str) -> dict:
    """content/de/<day>.json 을 로드한다. 없으면 빈 dict."""
    p = ROOT / "content" / "de" / f"{day}.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def _build_ref_map(day: str) -> dict:
    """key → reference text 맵을 반환한다."""
    import audio as audio_mod

    c = _load_content(day)
    refs = {}

    for i, s in enumerate(c.get("sentences", []), 1):
        refs[f"s{i}"] = audio_mod.plain(s["en"])

    for i, w in enumerate(c.get("words", []), 1):
        refs[f"w{i}"] = audio_mod.plain_word_tts(w[0], "de")

    for i, a in enumerate(c.get("advanced", []), 1):
        refs[f"v{i}"] = audio_mod.plain_word_tts(a["word"], "de")

    levels_a = (c.get("levels") or {}).get("a")
    if levels_a:
        for i, s in enumerate(levels_a.get("sentences", []), 1):
            refs[f"a{i}"] = audio_mod.plain(s["en"])

    return refs


def _key_kind(key: str) -> str:
    """파일 키로 kind('sentence' 또는 'word')를 판단한다."""
    return "sentence" if key[0] in ("s", "a") else "word"


def check_day(day: str, wm, small_wm=None, report_lines=None):
    """하루치 오디오를 검사하고 실패 항목을 출력한다.

    report_lines: 결과 줄을 append 할 리스트 (None 이면 stdout 만)
    small_wm: 경계값 파일을 'small' 모델로 추가 전사할 때 사용 (None 이면 생략)
    """
    import tts_qwen as qw

    audio_dir = ROOT / "de" / day / "audio"
    if not audio_dir.exists():
        _log(f"[{day}] audio 디렉터리 없음, 건너뜀", report_lines)
        return

    ref_map = _build_ref_map(day)
    files = sorted(audio_dir.glob("*.mp3"))
    if not files:
        _log(f"[{day}] mp3 파일 없음", report_lines)
        return

    _log(f"\n=== {day} ({len(files)}개) ===", report_lines)

    for f in files:
        key = f.stem
        dur = _duration(f)
        near_silent = dur < 0.1

        ref = ref_map.get(key)
        if ref is None:
            _log(f"  {key:6s}  dur={dur:.2f}s  [참조 없음]", report_lines)
            continue

        kind = _key_kind(key)

        if near_silent:
            status = "FAIL-SILENT"
            detail = f"dur={dur:.3f}s"
        elif kind == "sentence":
            errs = qw.count_word_errors(f, ref, wm)
            status = "PASS" if errs <= 1 else "FAIL"
            detail = f"errs={errs} dur={dur:.2f}s"
            if status == "FAIL" and small_wm is not None:
                segs, _ = small_wm.transcribe(qw.audio16k(f), language="de", beam_size=5)
                hyp_small = " ".join(s.text.strip() for s in segs)
                detail += f"  [small: {hyp_small!r}]"
        else:
            clip_wer = qw.compute_wer_word_clip(f, ref, wm)
            status = "PASS" if clip_wer == 0.0 else "FAIL"
            detail = f"wer={clip_wer:.2f} dur={dur:.2f}s"
            if status == "FAIL" and small_wm is not None:
                segs, _ = small_wm.transcribe(qw.audio16k(f), language="de", beam_size=5)
                hyp_small = " ".join(s.text.strip() for s in segs)
                detail += f"  [small: {hyp_small!r}]"

        line = f"  {key:6s}  {status:12s}  ref={ref!r:40s}  {detail}"
        _log(line, report_lines)


def _log(msg: str, lines):
    print(msg, flush=True)
    if lines is not None:
        lines.append(msg)


def main():
    ap = argparse.ArgumentParser(description="독일어 오디오 품질 검사")
    ap.add_argument("--days", nargs="*", help="검사할 날짜(없으면 전체)")
    ap.add_argument("--out", help="보고서 출력 경로")
    ap.add_argument("--model", default=None, help="Whisper 크기 (기본값: tts_qwen.WHISPER_GATE_MODEL)")
    ap.add_argument("--small-too", action="store_true",
                    help="경계값 파일을 small 모델로 추가 전사 (이미 small 이면 무시)")
    args = ap.parse_args()

    import tts_qwen as qw
    from faster_whisper import WhisperModel

    model = args.model or qw.WHISPER_GATE_MODEL
    print(f"Whisper {model} 로드 중...", flush=True)
    wm = WhisperModel(model, device="cpu", compute_type="int8")
    small_wm = None
    if args.small_too and model != "small":
        print("Whisper small 로드 중...", flush=True)
        small_wm = WhisperModel("small", device="cpu", compute_type="int8")

    # 검사할 날짜 목록
    if args.days:
        days = args.days
    else:
        days = sorted(
            d.name for d in (ROOT / "de").iterdir()
            if d.is_dir() and not d.name.startswith(".")
        )

    report_lines = []
    for day in days:
        check_day(day, wm, small_wm, report_lines)

    # 요약
    fail_count = sum(1 for l in report_lines if "FAIL" in l)
    pass_count = sum(1 for l in report_lines if " PASS " in l)
    summary = f"\n합격: {pass_count}  불합격: {fail_count}"
    _log(summary, report_lines)

    # 파일 저장
    out_path = args.out or os.environ.get("REPORT_OUT")
    if out_path:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text("\n".join(report_lines) + "\n", encoding="utf-8")
        print(f"\n보고서 저장: {out_path}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
