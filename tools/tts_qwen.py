"""Qwen3-TTS(CustomVoice 1.7B, 화자 Serena)로 독일어 문장과 단어 음성을 CPU에서 만든다.

founder/de-voice 의 C2 설정을 그대로 따른다(이슈 #9).
- 모델: Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice, speaker=Serena, language=German, fp32 CPU
- 지시문 INSTRUCT, temperature 0.7, top_p 0.9, repetition_penalty 1.05, 항목마다 seed 7
- 후처리: 앞뒤 무음 0.08초만 남기고 -18 LUFS(피크 -1dBFS 제한), atempo 1.0(템포 변경 없음), mp3 44.1kHz 128k
- 단어: 'Das Wort heißt: X.' 안에서 만든 뒤 Whisper 단어 시각으로 X 만 잘라낸다(faster-whisper)

사용:
  python tools/tts_qwen.py gen   ITEMS.json OUT_DIR [--trim-model base]
  python tools/tts_qwen.py check ITEMS.json OUT_DIR [--model base]
ITEMS.json: {"items": [{"key": "s1", "kind": "sentence"|"word", "text": "..."}]}
gen 은 OUT_DIR/<key>.mp3 와 timing.json, check 는 whisper.json 을 남기고 표를 출력한다.
나중에 tools/audio.py 가 load()와 generate()를 그대로 불러 쓸 수 있게 나눠 두었다.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"
SPEAKER = "Serena"
INSTRUCT = ("Speak as a calm, warm and friendly female narrator reading a short news text aloud for "
            "language learners. Clear German pronunciation, relaxed natural pace, natural pauses.")
GEN = dict(temperature=0.7, top_p=0.9, subtalker_temperature=0.7, repetition_penalty=1.05)
SEED = 7
TARGET_LUFS = -18.0
TEMPO = 1.0  # C2 최종본은 atempo 1.0(rebuild.py C2 1.0)
SR_MP3 = 44100
CARRIER = "Das Wort heißt: {}."
# 게이트 검증에 쓸 Whisper 모델 크기. audio.py 와 check_de_audio.py 가 함께 참조한다.
WHISPER_GATE_MODEL = "small"


def log(*a):
    print(*a, flush=True)


# ---------- 모델 ----------

def load(repo=REPO):
    """모델을 받아(캐시에 있으면 건너뜀) CPU fp32 로 올린다. (model, {download_sec, load_sec})"""
    import torch
    from huggingface_hub import snapshot_download
    from qwen_tts import Qwen3TTSModel

    if os.environ.get("TTS_THREADS"):
        torch.set_num_threads(int(os.environ["TTS_THREADS"]))
    t0 = time.time()
    path = snapshot_download(repo)
    t1 = time.time()
    m = Qwen3TTSModel.from_pretrained(path, device_map="cpu", dtype=torch.float32)
    t2 = time.time()
    return m, {"download_sec": round(t1 - t0, 2), "load_sec": round(t2 - t1, 2), "threads": torch.get_num_threads()}


def generate(m, text, seed=SEED):
    import torch
    torch.manual_seed(seed)
    w, sr = m.generate_custom_voice(text=text, language="German", speaker=SPEAKER, instruct=INSTRUCT, **GEN)
    return w[0], sr


# ---------- 후처리 ----------

def lufs(f):
    r = subprocess.run(["ffmpeg", "-nostats", "-i", str(f), "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r)
    return float(m[-1]) if m else None


def polish(wav, target=TARGET_LUFS, pad=0.08):
    """앞뒤 무음을 pad 초만 남기고 자르고 통합 음량을 target LUFS 로 맞춘다(선형 이득, 피크 -1dBFS 제한)."""
    import numpy as np
    import soundfile as sf
    x, sr = sf.read(str(wav))
    if x.ndim > 1:
        x = x.mean(1)
    env = np.abs(x)
    idx = np.where(env > 10 ** (-45 / 20) * max(env.max(), 1e-9))[0]
    if len(idx):
        x = x[max(idx[0] - int(pad * sr), 0):min(idx[-1] + int(pad * sr), len(x))]
    sf.write(str(wav), x, sr)
    cur = lufs(wav)
    if cur is not None:
        g = 10 ** ((target - cur) / 20)
        peak = np.abs(x).max() * g
        if peak > 0.89:
            g *= 0.89 / peak
        sf.write(str(wav), x * g, sr)


def to_mp3(wav, mp3, tempo=TEMPO, bitrate="128k"):
    af = ["-af", f"atempo={tempo}"] if tempo and tempo != 1.0 else []
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), *af, "-ac", "1", "-ar", str(SR_MP3),
                    "-b:a", bitrate, str(mp3)], check=True)


def duration(f):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", str(f)]).strip())


# ---------- 단어 잘라내기 ----------

_whisper = {}


def whisper_model(size):
    if size not in _whisper:
        from faster_whisper import WhisperModel
        _whisper[size] = WhisperModel(size, device="cpu", compute_type="int8")
    return _whisper[size]


def audio16k(path):
    """Whisper 입력용 16kHz mono float32 배열(ffmpeg 로 디코드해 PyAV 버전 차이를 피한다)."""
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", str(path), "-ac", "1", "-ar", "16000",
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def quietest(x, sr, t0, t1):
    """t0~t1 구간에서 40ms 창 에너지가 가장 낮은 곳을 찾고, 소리가 다시 커지기(+25dB) 직전 40ms 앞을 자른다."""
    import numpy as np
    a, b = max(int(t0 * sr), 0), min(int(t1 * sr), len(x))
    hop, win = int(0.01 * sr), int(0.04 * sr)
    best, bi = 1e9, b
    for i in range(a, max(b - win, a + 1), hop):
        e = float(np.mean(x[i:i + win] ** 2))
        if e <= best:
            best, bi = e, i
    j = bi
    while j + win < len(x) and float(np.mean(x[j:j + win] ** 2)) < max(best, 1e-12) * 10 ** 2.5:
        j += hop
    return max(j - win, bi)


def trim_carrier(x, sr, word, wav_path, size):
    """'Das Wort heißt: X.' 음성에서 X 만 남긴다. 경계를 못 찾으면 None."""
    segs, _ = whisper_model(size).transcribe(audio16k(wav_path), language="de", beam_size=1, word_timestamps=True)
    ws = [w for s in segs for w in (s.words or [])]
    # 운반 문장의 마지막 단어 'heißt' 를 기준으로 자른다(목표 단어를 Whisper 가 잘못 들어도 경계는 찾게)
    hits = [i for i, w in enumerate(ws) if w.word.strip(" .:,").lower() in ("heißt", "heisst")]
    k = hits[-1] if hits else len(ws) - len(word.split()) - 1
    if k < 0 or k + 1 >= len(ws):
        return None
    cut = quietest(x, sr, ws[k].end - 0.1, ws[k + 1].start + 0.35)
    return x[cut:]


# ---------- WER 계산 ----------

def norm_words(s):
    return re.findall(r"[a-zäöüß]+", s.lower().replace("8", "acht"))


def compute_wer(audio_file, ref_text, wm_or_size="base"):
    """음성 파일과 참조 텍스트의 단어 오류율(WER)을 계산한다.

    wm_or_size: faster_whisper.WhisperModel 인스턴스 또는 크기 문자열('base', 'tiny' 등).
    """
    import difflib
    if isinstance(wm_or_size, str):
        wm = whisper_model(wm_or_size)
    else:
        wm = wm_or_size
    segs, _ = wm.transcribe(audio16k(audio_file), language="de", beam_size=5)
    hyp = " ".join(s.text.strip() for s in segs)
    r = norm_words(ref_text)
    h = norm_words(hyp)
    if not r:
        return 0.0
    errs = sum(max(a2 - a1, b2 - b1) for op, a1, a2, b1, b2 in
               difflib.SequenceMatcher(a=r, b=h).get_opcodes() if op != "equal")
    return errs / len(r)


def compute_wer_word_carrier(carrier_wav, word_text, wm_or_size="base"):
    """캐리어 문장('Das Wort heißt: X.') 음성에서 단어 X 가 올바르게 발음됐는지 WER 로 확인한다.

    단어가 캐리어 전사에 포함되면 WER=0, 없으면 편집거리 기반 WER 을 반환한다.
    """
    import difflib
    if isinstance(wm_or_size, str):
        wm = whisper_model(wm_or_size)
    else:
        wm = wm_or_size
    segs, _ = wm.transcribe(audio16k(carrier_wav), language="de", beam_size=5)
    hyp = " ".join(s.text.strip() for s in segs)
    ref = norm_words(word_text)
    hyp_w = norm_words(hyp)
    if not ref:
        return 0.0
    # 단어가 hyp 에 포함됐는지 확인 (순서 보존 부분일치)
    for i in range(len(hyp_w) - len(ref) + 1):
        if hyp_w[i:i + len(ref)] == ref:
            return 0.0
    # 없으면 편집거리 기반 WER (ref 기준)
    errs = sum(max(a2 - a1, b2 - b1) for op, a1, a2, b1, b2 in
               difflib.SequenceMatcher(a=ref, b=hyp_w).get_opcodes() if op != "equal")
    return min(errs / len(ref), 1.0)


# ---------- 합격 판정 ----------

def count_word_errors(audio_file, ref_text, wm_or_size="base"):
    """참조 텍스트 대비 절대 단어 오류 수를 반환한다(WER 비율이 아닌 개수).

    문장 게이트: 반환값이 1 이하면 합격으로 간주한다.
    wm_or_size: WhisperModel 인스턴스 또는 크기 문자열.
    """
    import difflib
    if isinstance(wm_or_size, str):
        wm = whisper_model(wm_or_size)
    else:
        wm = wm_or_size
    segs, _ = wm.transcribe(audio16k(audio_file), language="de", beam_size=5)
    hyp = " ".join(s.text.strip() for s in segs)
    r = norm_words(ref_text)
    h = norm_words(hyp)
    if not r:
        return 0
    return sum(max(a2 - a1, b2 - b1) for op, a1, a2, b1, b2 in
               difflib.SequenceMatcher(a=r, b=h).get_opcodes() if op != "equal")


# 독일어 정관사/부정관사: 전사에 포함돼도 단어 클립 허용
_ARTICLES_DE = frozenset([
    "der", "die", "das", "dem", "den", "des",
    "ein", "eine", "einen", "einem", "einer",
])


def compute_wer_word_clip(audio_file, word_text, wm_or_size="base", min_dur=0.25):
    """트림된 단어 클립을 검증한다.

    - duration < min_dur(기본 0.25초)이면 1.0 반환(거부)
    - 관사(der/die/das 등)를 제외하고 핵심 단어를 비교한다
    - word_text 의 핵심 단어가 전사에 포함되면 0.0(합격), 아니면 편집거리 기반 WER(최대 1.0)

    wm_or_size: WhisperModel 인스턴스 또는 크기 문자열.
    """
    import difflib
    try:
        dur = duration(audio_file)
    except Exception:
        return 1.0
    if dur < min_dur:
        return 1.0  # 너무 짧은 클립 거부
    if isinstance(wm_or_size, str):
        wm = whisper_model(wm_or_size)
    else:
        wm = wm_or_size
    segs, _ = wm.transcribe(audio16k(audio_file), language="de", beam_size=5)
    hyp = " ".join(s.text.strip() for s in segs)
    ref = [w for w in norm_words(word_text) if w not in _ARTICLES_DE]
    hyp_w = [w for w in norm_words(hyp) if w not in _ARTICLES_DE]
    if not ref:
        return 0.0
    # ref 가 hyp_w 에 포함되면 합격 (관사 제외 후 순서 보존 부분일치)
    for i in range(len(hyp_w) - len(ref) + 1):
        if hyp_w[i:i + len(ref)] == ref:
            return 0.0
    errs = sum(max(a2 - a1, b2 - b1) for op, a1, a2, b1, b2 in
               difflib.SequenceMatcher(a=ref, b=hyp_w).get_opcodes() if op != "equal")
    return min(errs / len(ref), 1.0)


# ---------- 생성 ----------

def synth_items(m, items, out, trim_model="base"):
    """items 마다 out/<key>.mp3 를 만든다. 항목별 시간 기록을 돌려준다."""
    import soundfile as sf
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        for it in items:
            key, text, kind = it["key"], it["text"], it.get("kind", "sentence")
            wav = Path(tmp) / f"{key}.wav"
            note = ""
            t0 = time.time()
            if kind == "word":
                x, sr = generate(m, CARRIER.format(text))
                t_gen = time.time() - t0
                sf.write(str(wav), x, sr)
                t1 = time.time()
                y = trim_carrier(x, sr, text, wav, trim_model)
                t_trim = time.time() - t1
                if y is None:
                    note = "trim 실패, 단어 단독 생성"
                    t2 = time.time()
                    y, sr = generate(m, text)
                    t_gen += time.time() - t2
                sf.write(str(wav), y, sr)
            else:
                x, sr = generate(m, text)
                t_gen, t_trim = time.time() - t0, 0.0
                sf.write(str(wav), x, sr)
            t3 = time.time()
            polish(wav)
            to_mp3(wav, out / f"{key}.mp3")
            row = {"key": key, "kind": kind, "gen_sec": round(t_gen, 2), "trim_sec": round(t_trim, 2),
                   "post_sec": round(time.time() - t3, 2), "audio_sec": round(duration(out / f"{key}.mp3"), 2)}
            if note:
                row["note"] = note
            rows.append(row)
            log(json.dumps(row, ensure_ascii=False))
    return rows


def table(rows, cols):
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(str(r.get(c, "")) for c in cols) + " |" for r in rows]
    return "\n".join(lines)


def summary_out(text):
    log(text)
    p = os.environ.get("GITHUB_STEP_SUMMARY")
    if p:
        with open(p, "a", encoding="utf-8") as f:
            f.write(text + "\n\n")


def cmd_gen(a):
    items = json.loads(Path(a.items).read_text(encoding="utf-8"))["items"]
    t0 = time.time()
    m, info = load()
    log("model", json.dumps(info))
    t_warm = time.time()
    generate(m, "Guten Tag.")  # 첫 호출의 그래프 준비 비용을 따로 잰다
    info["warmup_sec"] = round(time.time() - t_warm, 2)
    rows = synth_items(m, items, a.out, a.trim_model)
    total = time.time() - t0
    sent = [r for r in rows if r["kind"] == "sentence"]
    word = [r for r in rows if r["kind"] == "word"]
    per = lambda rs: round(sum(r["gen_sec"] + r["trim_sec"] + r["post_sec"] for r in rs), 2)
    info.update({"sentences_sec": per(sent), "sentence_avg_sec": round(per(sent) / max(len(sent), 1), 2),
                 "words_sec": per(word), "word_avg_sec": round(per(word) / max(len(word), 1), 2),
                 "total_sec": round(total, 2), "audio_sentence_sec": round(sum(r["audio_sec"] for r in sent), 2),
                 "cpu": os.cpu_count(), "items": rows})
    Path(a.out, "timing.json").write_text(json.dumps(info, ensure_ascii=False, indent=1))
    summary_out("### Qwen3-TTS C2 생성 시간 (CPU)\n\n"
                + table([{k: v for k, v in info.items() if k != "items"}],
                        ["download_sec", "load_sec", "warmup_sec", "sentences_sec", "sentence_avg_sec",
                         "words_sec", "word_avg_sec", "total_sec", "threads", "cpu"])
                + "\n\n" + table(rows, ["key", "kind", "gen_sec", "trim_sec", "post_sec", "audio_sec", "note"]))


def cmd_check(a):
    import difflib
    items = json.loads(Path(a.items).read_text(encoding="utf-8"))["items"]
    t0 = time.time()
    wm = whisper_model(a.model)
    t_load = time.time() - t0
    rows = []
    for it in items:
        t1 = time.time()
        wer_val = compute_wer(Path(a.out) / f"{it['key']}.mp3", it["text"], wm)
        segs, _ = wm.transcribe(audio16k(Path(a.out) / f"{it['key']}.mp3"), language="de", beam_size=5)
        hyp = " ".join(s.text.strip() for s in segs)
        rows.append({"key": it["key"], "wer": round(wer_val, 3), "sec": round(time.time() - t1, 2), "hyp": hyp})
    total = time.time() - t0
    Path(a.out, f"whisper-{a.model}.json").write_text(json.dumps(
        {"model": a.model, "load_sec": round(t_load, 2), "total_sec": round(total, 2), "items": rows},
        ensure_ascii=False, indent=1))
    summary_out(f"### faster-whisper {a.model} 확인 (load {t_load:.1f}s, total {total:.1f}s)\n\n"
                + table(rows, ["key", "wer", "sec", "hyp"]))


def main(argv=None):
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("gen")
    g.add_argument("items")
    g.add_argument("out")
    g.add_argument("--trim-model", default="base")
    c = sub.add_parser("check")
    c.add_argument("items")
    c.add_argument("out")
    c.add_argument("--model", default="base")
    a = p.parse_args(argv)
    {"gen": cmd_gen, "check": cmd_check}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
