"""content/<언어>/YYYY-MM-DD.json 의 문장마다 음성을 만들어 <언어>/YYYY-MM-DD/audio/s1.mp3 … 로 저장한다.

사용: python3 tools/audio.py en 2026-10-12 [Kokoro 모델 폴더]
- 영어(tts=kokoro): pip install kokoro-onnx soundfile, 모델 파일 kokoro-v1.0.int8.onnx 와 voices-v1.0.bin
- 일본어(tts=voicevox): VOICEVOX 엔진이 VOICEVOX_URL(기본 http://localhost:50021)에서 돌고 있어야 한다
- 독일어(tts=qwen): pip install qwen-tts==0.1.1 faster-whisper soundfile torch(cpu), ffmpeg/sox
  모든 레벨(문장 s{i}, 단어 w{i}, 고급어휘 v{i})을 한 번의 모델 로드로 생성한다.
  이미 파일이 있으면 건너뛰고, 생성 후 faster-whisper base 로 WER 검증해 최대 QWEN_MAX_RETRIES 회 재시도한다.
  형식: 44.1 kHz mono mp3 128 kbps.
- 공통: ffmpeg
이미 문장 수만큼 mp3 가 있으면 다시 만들지 않는다.
"""
import json
import os
import re
import shutil
import urllib.parse
import urllib.request
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import langs  # noqa: E402

# ---------- Qwen3-TTS(독일어) 설정 ----------
# 재시도 시드 순서: 벤치마크에서 ~30% 항목이 seed=7 에서 실패, 이 시드들은 통과율이 높다.
QWEN_SEEDS = [7, 11, 12, 13, 17, 19, 23, 29]
# WER 이 이 값 이하면 합격으로 간주하고 재시도를 중단한다.
QWEN_ACCEPT_WER = 0.3


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


def qwen(c, lang, out_dir, max_retries=4, trim_model="base"):
    """Qwen3-TTS(독일어)로 하루치 오디오를 모두 생성한다.

    - 문장 s{i}.mp3, 단어 w{i}.mp3, 고급 어휘 v{i}.mp3 를 out_dir 에 저장한다.
    - 이미 파일이 있으면 건너뛴다.
    - 각 항목을 faster-whisper base 로 WER 검증하고 합격(WER <= QWEN_ACCEPT_WER) 때까지
      QWEN_SEEDS 순서로 재시도한다(최대 max_retries 회).
    - max_retries 를 모두 써도 실패하면 가장 WER 이 낮은 결과를 저장하고 ::warning:: 을 출력한다.
      잡 전체를 실패시키지 않는다.
    """
    out_dir = Path(out_dir)

    # 생성할 항목 목록 구성 (heavy import 전에 skip 여부를 먼저 확인한다)
    items = []
    for i, s in enumerate(c.get("sentences", []), 1):
        items.append({"key": f"s{i}", "kind": "sentence",
                      "text": plain(s["en"]), "target": out_dir / f"s{i}.mp3"})
    for i, w in enumerate(c.get("words", []), 1):
        items.append({"key": f"w{i}", "kind": "word",
                      "text": plain_word_tts(w[0], lang), "target": out_dir / f"w{i}.mp3"})
    for i, a in enumerate(c.get("advanced", []), 1):
        items.append({"key": f"v{i}", "kind": "word",
                      "text": plain_word_tts(a["word"], lang), "target": out_dir / f"v{i}.mp3"})

    # level a 문장 오디오: a{i}.mp3 (levels.a 가 있을 때만)
    levels_a = (c.get("levels") or {}).get("a")
    if levels_a:
        for i, s in enumerate(levels_a.get("sentences", []), 1):
            items.append({"key": f"a{i}", "kind": "sentence",
                          "text": plain(s["en"]), "target": out_dir / f"a{i}.mp3"})

    pending = [it for it in items if not it["target"].exists()]
    if not pending:
        print(f"qwen audio: 모든 파일 이미 존재 ({len(items)}개)")
        return

    print(f"qwen audio: {len(pending)}개 생성 예정 (총 {len(items)}개)")
    out_dir.mkdir(parents=True, exist_ok=True)

    # 생성이 필요한 경우에만 heavy import
    import tts_qwen as qw
    import soundfile as sf
    from faster_whisper import WhisperModel

    # 모델과 Whisper 를 한 번만 로드
    m, model_info = qw.load()
    print("qwen model:", json.dumps(model_info))
    qw.generate(m, "Guten Tag.")  # warmup: 첫 호출 비용을 미리 흡수

    wm = WhisperModel(trim_model, device="cpu", compute_type="int8")

    warn_list = []
    with tempfile.TemporaryDirectory() as _tmp:
        tmp = Path(_tmp)
        for it in pending:
            key, text, kind = it["key"], it["text"], it["kind"]
            best_mp3 = None
            best_wer = 2.0

            for attempt in range(max_retries):
                seed = QWEN_SEEDS[attempt % len(QWEN_SEEDS)]
                wav = tmp / f"{key}_a{attempt}.wav"
                carrier_wav = tmp / f"{key}_c{attempt}.wav"
                mp3 = tmp / f"{key}_a{attempt}.mp3"
                try:
                    if kind == "word":
                        # 캐리어 안에서 생성하고, Whisper 로 캐리어 맥락 검증 후 트림
                        x, sr = qw.generate(m, qw.CARRIER.format(text), seed=seed)
                        sf.write(str(carrier_wav), x, sr)
                        wer = qw.compute_wer_word_carrier(carrier_wav, text, wm)
                        y = qw.trim_carrier(x, sr, text, carrier_wav, trim_model)
                        if y is None:
                            # 트림 실패: 단어 단독 생성, WER 소폭 패널티
                            y, sr = qw.generate(m, text, seed=seed)
                            wer = max(wer, 0.35)
                        sf.write(str(wav), y, sr)
                    else:
                        x, sr = qw.generate(m, text, seed=seed)
                        sf.write(str(wav), x, sr)
                        wer = qw.compute_wer(wav, text, wm)

                    qw.polish(wav)
                    qw.to_mp3(wav, mp3)

                    print(f"{key} attempt={attempt + 1} seed={seed} WER={wer:.2f}")

                    if wer < best_wer:
                        best_wer = wer
                        best_mp3 = tmp / f"{key}_best.mp3"
                        shutil.copy2(str(mp3), str(best_mp3))

                    if wer <= QWEN_ACCEPT_WER:
                        break
                except Exception as e:  # noqa: BLE001
                    print(f"::warning::de audio {key} attempt {attempt + 1} 오류: {e}")

            if best_mp3 and best_mp3.exists():
                if best_wer > QWEN_ACCEPT_WER:
                    warn_list.append(f"{key}(WER={best_wer:.2f})")
                shutil.copy2(str(best_mp3), str(it["target"]))
                print(f"ok {key} -> {it['target'].name} (WER={best_wer:.2f})")
            else:
                warn_list.append(f"{key}(생성실패)")
                print(f"::warning::de audio {key} 생성 실패, 건너뜀")

    if warn_list:
        print(f"::warning::de audio 검증 경고 ({len(warn_list)}건): {', '.join(warn_list)}")
    print(f"qwen audio: 완료 ({len(pending)}개 처리)")


def main(lang, day, models, level="b"):
    L = langs.get(lang)
    c = json.loads((ROOT / "content" / lang / f"{day}.json").read_text(encoding="utf-8"))
    out = ROOT / lang / day / "audio"

    # qwen(독일어): 모든 레벨을 한 번의 모델 로드로 생성. 이미 있는 파일은 건너뜀.
    if L["tts"] == "qwen":
        qwen(c, lang, out, max_retries=int(os.environ.get("QWEN_MAX_RETRIES", "4")))
        return

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
    engine = L["tts"]
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        if engine == "voicevox":
            voicevox(L, sentences, targets, tmp)
        elif engine == "kokoro":
            kokoro(L, sentences, targets, models, tmp)
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
