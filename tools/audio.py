"""content/YYYY-MM-DD.json 의 문장마다 Kokoro 음성을 만들어 YYYY-MM-DD/audio/s1.mp3 … 로 저장한다.

사용: python3 tools/audio.py 2026-10-12 [모델 폴더]
필요: pip install kokoro-onnx soundfile, ffmpeg, 모델 파일 kokoro-v1.0.int8.onnx 와 voices-v1.0.bin
이미 문장 수만큼 mp3 가 있으면 다시 만들지 않는다.
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main(day, models):
    c = json.loads((ROOT / "content" / f"{day}.json").read_text(encoding="utf-8"))
    sentences = [re.sub(r"\*\*(.+?)\*\*", r"\1", s["en"]) for s in c["sentences"]]
    out = ROOT / day / "audio"
    targets = [out / f"s{i}.mp3" for i in range(1, len(sentences) + 1)]
    if all(t.exists() for t in targets):
        print("audio already exists")
        return
    from kokoro_onnx import Kokoro
    import soundfile as sf

    k = Kokoro(str(Path(models) / "kokoro-v1.0.int8.onnx"), str(Path(models) / "voices-v1.0.bin"))
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for text, target in zip(sentences, targets):
            a, sr = k.create(text, voice="af_heart", speed=0.92, lang="en-us")
            wav = Path(tmp) / "s.wav"
            sf.write(wav, a, sr)
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-ac", "1", "-b:a", "48k", str(target)], check=True)
    print(f"audio: {len(targets)} files")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ".")
