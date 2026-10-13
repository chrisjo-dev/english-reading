"""content/<언어>/YYYY-MM-DD.json 의 문장마다 음성을 만들어 <언어>/YYYY-MM-DD/audio/s1.mp3 … 로 저장한다.

사용: python3 tools/audio.py en 2026-10-12 [Kokoro 모델 폴더]
- 영어(tts=kokoro): pip install kokoro-onnx soundfile, 모델 파일 kokoro-v1.0.int8.onnx 와 voices-v1.0.bin
- 일본어(tts=voicevox): VOICEVOX 엔진이 VOICEVOX_URL(기본 http://localhost:50021)에서 돌고 있어야 한다
- 공통: ffmpeg
이미 문장 수만큼 mp3 가 있으면 다시 만들지 않는다.
"""
import json
import os
import re
import urllib.parse
import urllib.request
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import langs  # noqa: E402


def plain(text):
    """강조(**x**)를 벗기고 후리가나 표기({漢字|かんじ})는 한자만 남긴다."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    return re.sub(r"\{([^{}|]+)\|([^{}|]+)\}", r"\1", text)


def to_mp3(wav, target, bitrate):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-ac", "1", "-b:a", bitrate, str(target)], check=True)


def kokoro(L, sentences, targets, models, tmp):
    from kokoro_onnx import Kokoro
    import soundfile as sf

    k = Kokoro(str(Path(models) / "kokoro-v1.0.int8.onnx"), str(Path(models) / "voices-v1.0.bin"))
    for text, target in zip(sentences, targets):
        a, sr = k.create(text, voice=L["voice"], speed=L["speed"], lang=L["kokoro_lang"])
        wav = Path(tmp) / "s.wav"
        sf.write(wav, a, sr)
        to_mp3(wav, target, "48k")


def voicevox(L, sentences, targets, tmp):
    base = os.environ.get("VOICEVOX_URL", "http://localhost:50021")
    for text, target in zip(sentences, targets):
        q = f"{base}/audio_query?" + urllib.parse.urlencode({"speaker": L["voice"], "text": text})
        with urllib.request.urlopen(urllib.request.Request(q, method="POST"), timeout=60) as r:
            query = json.loads(r.read())
        query["speedScale"] = L["speed"]
        req = urllib.request.Request(f"{base}/synthesis?speaker={L['voice']}", data=json.dumps(query).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        wav = Path(tmp) / "s.wav"
        with urllib.request.urlopen(req, timeout=120) as r:
            wav.write_bytes(r.read())
        to_mp3(wav, target, "96k")


def main(lang, day, models):
    L = langs.get(lang)
    c = json.loads((ROOT / "content" / lang / f"{day}.json").read_text(encoding="utf-8"))
    sentences = [plain(s["en"]) for s in c["sentences"]]
    out = ROOT / lang / day / "audio"
    targets = [out / f"s{i}.mp3" for i in range(1, len(sentences) + 1)]
    if all(t.exists() for t in targets):
        print("audio already exists")
        return
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        if L["tts"] == "voicevox":
            voicevox(L, sentences, targets, tmp)
        else:
            kokoro(L, sentences, targets, models, tmp)
    print(f"audio: {len(targets)} files ({L['tts']})")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else ".")
