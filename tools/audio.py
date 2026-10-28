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


def plain_word_tts(text, lang):
    """단어를 TTS에 넘길 수 있게 가공한다.
    ** 와 괄호 주석을 제거하고, 일본어는 {漢字|かな}를 가나 읽기로, 영어는 한자로 바꾼다."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\s*\([^)]*\)", "", text)
    if lang == "ja":
        text = re.sub(r"\{([^{}|]+)\|([^{}|]+)\}", r"\2", text)
    else:
        text = re.sub(r"\{([^{}|]+)\|([^{}|]+)\}", r"\1", text)
    return text.strip()


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


def main(lang, day, models, level="b"):
    L = langs.get(lang)
    c = json.loads((ROOT / "content" / lang / f"{day}.json").read_text(encoding="utf-8"))
    out = ROOT / lang / day / "audio"
    if level == "a":
        levels_a = (c.get("levels") or {}).get("a")
        if not levels_a:
            print(f"levels.a 없음, level a 오디오 건너뜀 ({lang} {day})")
            return
        sentences = [plain(s["en"]) for s in levels_a["sentences"]]
        targets = [out / f"a{i}.mp3" for i in range(1, len(sentences) + 1)]
    elif level == "w":
        # 주요 단어 발음: audio/w{i}.mp3
        words_list = c.get("words", [])
        if not words_list:
            print(f"words 없음, word 오디오 건너뜀 ({lang} {day})")
            return
        sentences = [plain_word_tts(w[0], lang) for w in words_list]
        targets = [out / f"w{i}.mp3" for i in range(1, len(sentences) + 1)]
    elif level == "v":
        # 한 단계 위 어휘 발음: audio/v{i}.mp3
        adv_list = c.get("advanced", [])
        if not adv_list:
            print(f"advanced 없음, adv 오디오 건너뜀 ({lang} {day})")
            return
        sentences = [plain_word_tts(a["word"], lang) for a in adv_list]
        targets = [out / f"v{i}.mp3" for i in range(1, len(sentences) + 1)]
    else:
        sentences = [plain(s["en"]) for s in c["sentences"]]
        targets = [out / f"s{i}.mp3" for i in range(1, len(sentences) + 1)]
    if all(t.exists() for t in targets):
        print(f"audio level {level} already exists")
        return
    out.mkdir(parents=True, exist_ok=True)
    engine = L["tts"]
    with tempfile.TemporaryDirectory() as tmp:
        if engine == "voicevox":
            voicevox(L, sentences, targets, tmp)
        elif engine == "kokoro":
            kokoro(L, sentences, targets, models, tmp)
        elif engine == "qwen":
            # TTS 경로 미확정(GitHub Actions CPU vs Mac). Phase 1 이후 구현.
            # 페이지는 브라우저 내장 SpeechSynthesis de-DE 폴백으로 동작한다.
            raise NotImplementedError(
                f"Qwen3-TTS 엔진은 아직 구현되지 않았습니다 ({lang} {day}). "
                "음성 파일이 없으면 페이지는 SpeechSynthesis de-DE 폴백으로 동작합니다. "
                "TTS 경로(GitHub Actions CPU vs Mac)가 확정되면 이 분기를 구현하세요."
            )
        else:
            raise NotImplementedError(f"알 수 없는 TTS 엔진: {engine!r}")
    print(f"audio level {level}: {len(targets)} files ({engine})")


if __name__ == "__main__":
    # 사용: python3 tools/audio.py en 2026-10-12 [models] [--level a|b]
    import argparse as _ap
    _p = _ap.ArgumentParser()
    _p.add_argument("lang")
    _p.add_argument("day")
    _p.add_argument("models", nargs="?", default=".")
    _p.add_argument("--level", default="b", choices=["a", "b", "w", "v"])
    _a = _p.parse_args()
    main(_a.lang, _a.day, _a.models, _a.level)
