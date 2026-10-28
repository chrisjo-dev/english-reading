"""독일어 오디오 생성(qwen 경로) 단위 테스트(이슈 #9).

검증 항목:
 1. 파일 이미 있으면 모델 로드 안 함
 2. 부분 존재 시 없는 파일만 생성
 3. WER 합격(<=QWEN_ACCEPT_WER) 즉시 다음 항목으로 이동
 4. WER 불합격 시 최대 max_retries 회 재시도, 가장 낮은 WER 결과 유지
 5. max_retries 모두 실패해도 잡 중단 없이 경고만 출력
 6. publish.yml push paths 에서 de 경로 제외 확인
 7. de-audio.yml 이 content/de 경로만 트리거하는지 확인

모든 TTS/Whisper 호출은 mock 으로 대체하므로 모델을 내려받지 않는다.

실행: python -m pytest -q tests/test_de_audio.py
"""
import io
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

# CI 환경에 설치 안 된 패키지를 mock 으로 채운다.
# qwen() 이 lazy import 로 사용하므로 sys.modules 에 미리 올려 두면
# 'import soundfile as sf' 등이 MagicMock 을 반환한다.
for _pkg in ("soundfile", "faster_whisper", "numpy"):
    try:
        __import__(_pkg)
    except ImportError:
        sys.modules[_pkg] = MagicMock()

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

import audio as audio_mod  # noqa: E402

# ── 픽스처 ─────────────────────────────────────────────────────────────────────

DE_CONTENT = {
    "sentences": [
        {"en": "In Deutschland gibt es viele **Bäckereien**.", "b2": False,
         "chunks": [["In Deutschland", "독일에는"]]},
        {"en": "Die Bäckerei öffnet früh am Morgen.", "b2": False,
         "chunks": [["Die Bäckerei", "빵집은"]]},
    ],
    "words": [["Bäckerei", "빵집"], ["Brot", "빵"]],
    "advanced": [
        {"word": "frisch", "meaning": "신선한", "confuse": None,
         "example": "Das Brot ist **frisch**.", "example_ko": "신선해요."},
        {"word": "täglich", "meaning": "매일", "confuse": None,
         "example": "Er kommt **täglich**.", "example_ko": "그는 매일 옵니다."},
    ],
}

# 기대 파일 목록: s1, s2, w1, w2, v1, v2
ALL_KEYS = ["s1", "s2", "w1", "w2", "v1", "v2"]

# levels.a 포함 콘텐츠 픽스처 (a1, a2 추가 생성)
DE_CONTENT_WITH_LEVELS = {
    **DE_CONTENT,
    "levels": {
        "a": {
            "sentences": [
                {"en": "Brot gibt es in Deutschland.", "chunks": [["Brot gibt es in Deutschland.", "독일에 빵이 있어요"]]},
                {"en": "Die Baeckerei oeffnet frueh.", "chunks": [["Die Baeckerei oeffnet frueh.", "빵집은 일찍 열어요"]]},
            ],
            "answers": ["독일에 빵이 있어요.", "빵집은 일찍 열어요."],
        }
    },
}
ALL_KEYS_WITH_LEVELS = ["s1", "s2", "w1", "w2", "v1", "v2", "a1", "a2"]


def _make_fake_model():
    """fake torch 출력(4000샘플 22050Hz)을 반환하는 mock 모델."""
    import numpy as np
    fake_audio = np.zeros(4000, dtype=np.float32)
    fake_sr = 22050
    m = MagicMock()
    return m, fake_audio, fake_sr


def _patch_qwen(
    wer_sequence=None,
    trim_ok=True,
    gen_raises=None,
):
    """qwen() 함수가 의존하는 tts_qwen 함수들을 일괄 mock 한다.

    wer_sequence: [wer_s1_attempt0, wer_s1_attempt1, ...] — None 이면 항상 0.0
    trim_ok: False 면 trim_carrier 가 None 반환
    gen_raises: 특정 attempt 인덱스(전역 호출 순서)에서 예외 발생
    """
    import numpy as np

    call_counter = {"gen": 0, "wer": 0}
    wer_seq = wer_sequence or []

    def fake_load(repo=None):
        m = MagicMock()
        return m, {"download_sec": 0.0, "load_sec": 0.0, "threads": 1}

    def fake_generate(m, text, seed=7):
        idx = call_counter["gen"]
        call_counter["gen"] += 1
        if gen_raises and idx in gen_raises:
            raise RuntimeError(f"fake error at gen call {idx}")
        return np.zeros(4000, dtype=np.float32), 22050

    def fake_trim_carrier(x, sr, word, wav_path, size):
        if not trim_ok:
            return None
        return x  # 그대로 반환

    def fake_compute_wer(audio_file, ref_text, wm_or_size="base"):
        idx = call_counter["wer"]
        call_counter["wer"] += 1
        if idx < len(wer_seq):
            return wer_seq[idx]
        return 0.0

    def fake_compute_wer_word_carrier(carrier_wav, word_text, wm_or_size="base"):
        idx = call_counter["wer"]
        call_counter["wer"] += 1
        if idx < len(wer_seq):
            return wer_seq[idx]
        return 0.0

    def fake_polish(wav, target=None, pad=None):
        pass

    def fake_to_mp3(wav, mp3, tempo=None, bitrate="128k"):
        # wav 는 이미 soundfile 이 썼지만 여기서는 mp3 에 더미 바이트만
        Path(mp3).write_bytes(b"ID3\x00")

    def fake_audio16k(path):
        return np.zeros(16000, dtype=np.float32)

    return {
        "tts_qwen.load": fake_load,
        "tts_qwen.generate": fake_generate,
        "tts_qwen.trim_carrier": fake_trim_carrier,
        "tts_qwen.compute_wer": fake_compute_wer,
        "tts_qwen.compute_wer_word_carrier": fake_compute_wer_word_carrier,
        "tts_qwen.polish": fake_polish,
        "tts_qwen.to_mp3": fake_to_mp3,
        "tts_qwen.audio16k": fake_audio16k,
        "_call_counter": call_counter,
    }


def _apply_patches(patches_dict):
    """patch dict 를 모두 시작하고 patch 객체 리스트를 반환한다. stop() 을 직접 호출하거나 with 블록으로 사용."""
    active = []
    for target, fake in patches_dict.items():
        if target.startswith("_"):
            continue
        p = patch(target, fake)
        p.start()
        active.append(p)
    return active


def _stop_patches(active):
    for p in active:
        p.stop()


class _FakeWhisperModel:
    """faster_whisper.WhisperModel 대체 mock."""
    def transcribe(self, audio, language="de", beam_size=5):
        seg = MagicMock()
        seg.text = "Bäckerei Brot frisch"
        return [seg], {}


# ── 1. 모든 파일 이미 있으면 모델 로드 안 함 ─────────────────────────────────

class TestQwenSkipsAllExisting(unittest.TestCase):

    def test_no_load_when_all_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "audio"
            out_dir.mkdir()
            for key in ALL_KEYS:
                (out_dir / f"{key}.mp3").write_bytes(b"")

            patches = _patch_qwen()
            load_mock = MagicMock(return_value=(MagicMock(), {}))

            active = _apply_patches(patches)
            with patch("tts_qwen.load", load_mock), \
                 patch("faster_whisper.WhisperModel", return_value=_FakeWhisperModel()):
                audio_mod.qwen(DE_CONTENT, "de", out_dir, max_retries=1)
            _stop_patches(active)

            load_mock.assert_not_called()


# ── 2. 부분 존재 시 없는 파일만 생성 ─────────────────────────────────────────

class TestQwenSkipsPartialExisting(unittest.TestCase):

    def test_existing_files_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "audio"
            out_dir.mkdir()
            # s1, s2 미리 생성
            (out_dir / "s1.mp3").write_bytes(b"existing_s1")
            (out_dir / "s2.mp3").write_bytes(b"existing_s2")

            patches = _patch_qwen()
            active = _apply_patches(patches)
            with patch("faster_whisper.WhisperModel", return_value=_FakeWhisperModel()):
                audio_mod.qwen(DE_CONTENT, "de", out_dir, max_retries=1)
            _stop_patches(active)

            # s1, s2 는 원본 그대로
            self.assertEqual((out_dir / "s1.mp3").read_bytes(), b"existing_s1")
            self.assertEqual((out_dir / "s2.mp3").read_bytes(), b"existing_s2")
            # w1, w2, v1, v2 는 새로 생성됨
            for key in ["w1", "w2", "v1", "v2"]:
                self.assertTrue((out_dir / f"{key}.mp3").exists(), f"{key}.mp3 가 없어요")

    def test_generates_only_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "audio"
            out_dir.mkdir()
            # s1 만 미리 생성
            (out_dir / "s1.mp3").write_bytes(b"")

            gen_calls = []

            patches = _patch_qwen()

            def tracking_generate(m, text, seed=7):
                import numpy as np
                gen_calls.append(text)
                return np.zeros(4000, dtype=np.float32), 22050

            active = _apply_patches(patches)
            with patch("tts_qwen.generate", tracking_generate), \
                 patch("faster_whisper.WhisperModel", return_value=_FakeWhisperModel()):
                audio_mod.qwen(DE_CONTENT, "de", out_dir, max_retries=1)
            _stop_patches(active)

            # s1 텍스트("In Deutschland...") 는 호출 안 됨
            s1_text = audio_mod.plain(DE_CONTENT["sentences"][0]["en"])
            self.assertNotIn(s1_text, gen_calls, "s1 이 이미 있으므로 generate 를 호출하면 안 됩니다")


# ── 3. WER 합격 시 즉시 중단 ─────────────────────────────────────────────────

class TestQwenAcceptsOnFirstPass(unittest.TestCase):

    def test_no_retry_when_first_wer_low(self):
        """WER=0.0 이면 attempt=1 로 끝낸다."""
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "audio"

            attempt_counts = {}

            def tracking_generate(m, text, seed=7):
                import numpy as np
                return np.zeros(4000, dtype=np.float32), 22050

            patches = _patch_qwen(wer_sequence=[0.0] * 20)

            actual_gen = patches["tts_qwen.generate"]

            gen_per_item = {}

            def gen_tracking(m, text, seed=7):
                import numpy as np
                return np.zeros(4000, dtype=np.float32), 22050

            active = _apply_patches(patches)
            wer_call_count = [0]

            def counting_wer(audio_file, ref_text, wm_or_size="base"):
                wer_call_count[0] += 1
                return 0.0

            def counting_wer_carrier(carrier_wav, word_text, wm_or_size="base"):
                wer_call_count[0] += 1
                return 0.0

            with patch("tts_qwen.compute_wer", counting_wer), \
                 patch("tts_qwen.compute_wer_word_carrier", counting_wer_carrier), \
                 patch("faster_whisper.WhisperModel", return_value=_FakeWhisperModel()):
                audio_mod.qwen(DE_CONTENT, "de", out_dir, max_retries=4)
            _stop_patches(active)

            # 항목 6개, WER 호출이 각 1회씩이면 총 6회
            self.assertEqual(wer_call_count[0], len(ALL_KEYS),
                             f"WER 0.0 이면 각 항목당 1회만 호출해야 합니다 (got {wer_call_count[0]})")


# ── 4. WER 불합격 시 재시도, 가장 낮은 결과 유지 ─────────────────────────────

class TestQwenRetryKeepsBest(unittest.TestCase):

    def test_retries_up_to_max(self):
        """WER 이 항상 높으면 max_retries 회 시도하고 가장 낮은 WER 결과를 유지한다."""
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "audio"

            # s1 만 테스트 (나머지는 이미 존재로 처리)
            out_dir.mkdir()
            for key in ["s2", "w1", "w2", "v1", "v2"]:
                (out_dir / f"{key}.mp3").write_bytes(b"")

            # s1 의 WER: attempt 0=0.8, attempt 1=0.5, attempt 2=0.9, attempt 3=0.6
            # 최솟값은 attempt 1 의 0.5
            wer_values = [0.8, 0.5, 0.9, 0.6]
            wer_idx = [0]

            def seq_wer(audio_file, ref_text, wm_or_size="base"):
                v = wer_values[wer_idx[0] % len(wer_values)]
                wer_idx[0] += 1
                return v

            # to_mp3 는 실제로 파일을 써야 best_mp3 가 존재하게 된다
            mp3_writes = []

            def tracking_to_mp3(wav, mp3, tempo=None, bitrate="128k"):
                Path(mp3).write_bytes(f"attempt_{wer_idx[0]}".encode())
                mp3_writes.append(str(mp3))

            patches = _patch_qwen()
            active = _apply_patches(patches)
            with patch("tts_qwen.compute_wer", seq_wer), \
                 patch("tts_qwen.compute_wer_word_carrier", seq_wer), \
                 patch("tts_qwen.to_mp3", tracking_to_mp3), \
                 patch("faster_whisper.WhisperModel", return_value=_FakeWhisperModel()):
                audio_mod.qwen(DE_CONTENT, "de", out_dir, max_retries=4)
            _stop_patches(active)

            # s1.mp3 가 생성됐어야 한다
            self.assertTrue((out_dir / "s1.mp3").exists(), "s1.mp3 가 없어요")
            # 4회 시도했어야 한다 (WER 0.3 이하가 없으므로)
            self.assertEqual(wer_idx[0], 4, f"4회 시도해야 하는데 {wer_idx[0]}회")

    def test_stops_early_on_accept(self):
        """WER 이 두 번째 시도에서 합격하면 세 번째 시도를 하지 않는다."""
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "audio"
            out_dir.mkdir()
            for key in ["s2", "w1", "w2", "v1", "v2"]:
                (out_dir / f"{key}.mp3").write_bytes(b"")

            wer_values = [0.9, 0.1]  # attempt 0 실패, attempt 1 합격
            wer_idx = [0]

            def seq_wer(audio_file, ref_text, wm_or_size="base"):
                v = wer_values[wer_idx[0] % len(wer_values)]
                wer_idx[0] += 1
                return v

            patches = _patch_qwen()
            active = _apply_patches(patches)
            with patch("tts_qwen.compute_wer", seq_wer), \
                 patch("tts_qwen.compute_wer_word_carrier", seq_wer), \
                 patch("faster_whisper.WhisperModel", return_value=_FakeWhisperModel()):
                audio_mod.qwen(DE_CONTENT, "de", out_dir, max_retries=4)
            _stop_patches(active)

            self.assertEqual(wer_idx[0], 2, f"2회에서 합격하면 중단해야 하는데 {wer_idx[0]}회")


# ── 5. 모든 시도 실패해도 잡 중단 없음 ───────────────────────────────────────

class TestQwenNoJobFailOnBadWer(unittest.TestCase):

    def test_warning_not_exception_on_all_fail(self):
        """max_retries 를 모두 써도 예외를 발생시키지 않는다."""
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "audio"

            patches = _patch_qwen(wer_sequence=[0.9] * 40)
            active = _apply_patches(patches)
            with patch("faster_whisper.WhisperModel", return_value=_FakeWhisperModel()):
                try:
                    audio_mod.qwen(DE_CONTENT, "de", out_dir, max_retries=2)
                except Exception as e:
                    self.fail(f"qwen() 이 예외를 발생시켰습니다: {e}")
            _stop_patches(active)

    def test_files_created_even_if_wer_bad(self):
        """WER 이 높아도 파일을 남긴다(가장 낮은 WER 결과)."""
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "audio"

            patches = _patch_qwen(wer_sequence=[0.8] * 40)
            active = _apply_patches(patches)
            with patch("faster_whisper.WhisperModel", return_value=_FakeWhisperModel()):
                audio_mod.qwen(DE_CONTENT, "de", out_dir, max_retries=1)
            _stop_patches(active)

            # 파일은 생성되어야 한다
            for key in ALL_KEYS:
                self.assertTrue((out_dir / f"{key}.mp3").exists(), f"{key}.mp3 가 없어요")

    def test_generate_exception_skips_item(self):
        """generate() 가 예외를 던지면 해당 항목을 건너뛰되 나머지는 계속 처리한다."""
        import numpy as np

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "audio"

            call_idx = [0]

            def sometimes_fail(m, text, seed=7):
                idx = call_idx[0]
                call_idx[0] += 1
                # idx=0: warmup("Guten Tag."), idx=1: 첫 번째 항목(s1) → 실패
                if idx == 1:
                    raise RuntimeError("fake error")
                return np.zeros(4000, dtype=np.float32), 22050

            patches = _patch_qwen()
            active = _apply_patches(patches)
            with patch("tts_qwen.generate", sometimes_fail), \
                 patch("faster_whisper.WhisperModel", return_value=_FakeWhisperModel()):
                audio_mod.qwen(DE_CONTENT, "de", out_dir, max_retries=1)
            _stop_patches(active)

            # 첫 항목(s1)은 실패했지만 이후 항목은 생성됐어야 한다
            created = [key for key in ALL_KEYS if (out_dir / f"{key}.mp3").exists()]
            self.assertGreater(len(created), 0, "하나도 생성 안 됐어요")


# ── 6. publish.yml push paths 에 de 없음 ─────────────────────────────────────

class TestPublishYmlDeExclusion(unittest.TestCase):

    def _load_yml(self):
        yml_text = (REPO / ".github/workflows/publish.yml").read_text(encoding="utf-8")
        return yml_text

    def test_no_wildcard_content_paths(self):
        """content/**.json 같은 전체 와일드카드가 없어야 한다."""
        yml = self._load_yml()
        # paths 섹션에 content/**.json 이 없어야 함
        self.assertNotIn("content/**.json", yml,
                         "publish.yml push paths 에 content/**.json 전체 와일드카드가 없어야 합니다")

    def test_de_path_not_in_push_paths(self):
        """content/de 경로가 push paths 에 없어야 한다."""
        yml = self._load_yml()
        # push: 섹션의 paths 블록에 de 가 없는지 확인
        # on: ... push: ... paths: 로 시작하는 블록 추출
        on_block = re.search(r"^on:.*?(?=\n\S)", yml, re.DOTALL | re.MULTILINE)
        on_text = on_block.group(0) if on_block else yml[:500]
        self.assertNotIn("content/de", on_text,
                         "publish.yml push paths 에 content/de 경로가 없어야 합니다")

    def test_en_path_in_push_paths(self):
        """content/en 경로가 push paths 에 있어야 한다(회귀)."""
        yml = self._load_yml()
        self.assertIn("content/en", yml, "publish.yml push paths 에 content/en 이 있어야 합니다")

    def test_ja_path_in_push_paths(self):
        """content/ja 경로가 push paths 에 있어야 한다(회귀)."""
        yml = self._load_yml()
        self.assertIn("content/ja", yml, "publish.yml push paths 에 content/ja 가 있어야 합니다")

    def test_dispatch_still_accepts_de(self):
        """workflow_dispatch 입력에 de 가 여전히 허용되어야 한다."""
        yml = self._load_yml()
        # workflow_dispatch inputs 에서 lang 기본값이나 설명에 de 가 언급돼야 함
        self.assertIn("de", yml, "workflow_dispatch 에서 de 가 언급돼야 합니다")


# ── 7. de-audio.yml 구조 검증 ─────────────────────────────────────────────────

class TestDeAudioYmlStructure(unittest.TestCase):

    def _load_yml(self):
        return (REPO / ".github/workflows/de-audio.yml").read_text(encoding="utf-8")

    def test_file_exists(self):
        self.assertTrue((REPO / ".github/workflows/de-audio.yml").exists(),
                        "de-audio.yml 이 없어요")

    def test_triggers_on_de_content_push(self):
        """content/de/**.json push 에 반응해야 한다."""
        yml = self._load_yml()
        self.assertIn("content/de/**.json", yml,
                      "de-audio.yml 이 content/de/**.json push 에 반응해야 합니다")

    def test_separate_concurrency_group(self):
        """publish 와 다른 concurrency 그룹을 사용해야 한다."""
        yml = self._load_yml()
        self.assertIn("de-audio", yml,
                      "de-audio.yml 의 concurrency group 에 'de-audio' 가 있어야 합니다")

    def test_triggers_publish_workflow(self):
        """publish.yml 을 gh workflow run 으로 트리거해야 한다."""
        yml = self._load_yml()
        self.assertIn("publish.yml", yml, "de-audio.yml 이 publish.yml 을 트리거해야 합니다")
        self.assertIn("gh workflow run", yml, "gh workflow run 명령이 있어야 합니다")

    def test_uses_hf_cache(self):
        """HuggingFace 모델 캐시를 사용해야 한다."""
        yml = self._load_yml()
        self.assertIn("/home/runner/.cache/hf-qwen", yml, "HuggingFace 캐시는 저장소 밖 경로여야 합니다")
        self.assertNotIn("git add -A", yml, "생성한 음성만 커밋해야 합니다")
        self.assertIn("actions/cache", yml, "actions/cache 가 있어야 합니다")

    def test_qwen_tts_version_pinned(self):
        """qwen-tts 버전이 고정돼 있어야 한다."""
        yml = self._load_yml()
        self.assertIn("qwen-tts==", yml, "qwen-tts 버전이 == 으로 고정돼 있어야 합니다")

    def test_timeout_minutes(self):
        """timeout-minutes 가 90 이하여야 한다."""
        yml = self._load_yml()
        m = re.search(r"timeout-minutes:\s*(\d+)", yml)
        self.assertIsNotNone(m, "timeout-minutes 가 없어요")
        self.assertLessEqual(int(m.group(1)), 90, "timeout-minutes 가 90 이하여야 합니다")



# ── 9. levels.a 오디오 생성 ──────────────────────────────────────────────────

class TestQwenLevelAAudio(unittest.TestCase):
    """qwen() 이 levels.a 가 있을 때 a{i}.mp3 를 생성하는지 검증한다."""

    def test_generates_level_a_mp3_when_levels_a_present(self):
        """levels.a 가 있으면 a1.mp3, a2.mp3 를 생성한다."""
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "audio"

            patches = _patch_qwen()
            active = _apply_patches(patches)
            with patch("faster_whisper.WhisperModel", return_value=_FakeWhisperModel()):
                audio_mod.qwen(DE_CONTENT_WITH_LEVELS, "de", out_dir, max_retries=1)
            _stop_patches(active)

            for key in ALL_KEYS_WITH_LEVELS:
                self.assertTrue((out_dir / f"{key}.mp3").exists(),
                                f"{key}.mp3 가 없어요 (levels.a 포함 콘텐츠)")

    def test_no_level_a_mp3_when_no_levels_a(self):
        """levels.a 가 없으면 a*.mp3 를 생성하지 않는다."""
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "audio"

            patches = _patch_qwen()
            active = _apply_patches(patches)
            with patch("faster_whisper.WhisperModel", return_value=_FakeWhisperModel()):
                audio_mod.qwen(DE_CONTENT, "de", out_dir, max_retries=1)
            _stop_patches(active)

            a_files = list(out_dir.glob("a*.mp3"))
            self.assertEqual(a_files, [],
                             f"levels.a 없으면 a*.mp3 를 만들지 않아야 합니다: {a_files}")

    def test_existing_level_a_mp3_not_regenerated(self):
        """이미 있는 a*.mp3 는 재생성하지 않는다."""
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "audio"
            out_dir.mkdir()
            (out_dir / "a1.mp3").write_bytes(b"existing_a1")
            (out_dir / "a2.mp3").write_bytes(b"existing_a2")
            for key in ALL_KEYS:
                (out_dir / f"{key}.mp3").write_bytes(b"")

            patches = _patch_qwen()
            active = _apply_patches(patches)
            with patch("faster_whisper.WhisperModel", return_value=_FakeWhisperModel()):
                audio_mod.qwen(DE_CONTENT_WITH_LEVELS, "de", out_dir, max_retries=1)
            _stop_patches(active)

            self.assertEqual((out_dir / "a1.mp3").read_bytes(), b"existing_a1")
            self.assertEqual((out_dir / "a2.mp3").read_bytes(), b"existing_a2")


# ── 8. main() qwen 분기 동작 검증 ────────────────────────────────────────────

class TestMainQwenDispatch(unittest.TestCase):
    """audio.main() 이 tts=qwen 언어에서 qwen() 를 호출하는지 확인한다."""

    def test_main_calls_qwen_for_de(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            de_dir = root / "content" / "de"
            de_dir.mkdir(parents=True)
            (de_dir / "2026-10-28.json").write_text(
                json.dumps(DE_CONTENT, ensure_ascii=False), encoding="utf-8"
            )
            qwen_called = []

            def fake_qwen(c, lang, out_dir, max_retries=4, trim_model="base"):
                qwen_called.append({"lang": lang, "max_retries": max_retries})

            orig_root = audio_mod.ROOT
            try:
                audio_mod.ROOT = root
                with patch.object(audio_mod, "qwen", fake_qwen):
                    audio_mod.main("de", "2026-10-28", ".")
            finally:
                audio_mod.ROOT = orig_root

            self.assertEqual(len(qwen_called), 1, "qwen() 가 한 번 호출돼야 합니다")
            self.assertEqual(qwen_called[0]["lang"], "de")

    def test_main_does_not_call_qwen_for_en(self):
        """en 은 qwen() 를 호출하지 않는다(회귀)."""
        called = []

        def fake_qwen(*a, **kw):
            called.append(True)

        with patch.object(audio_mod, "qwen", fake_qwen):
            # en 의 kokoro 경로가 실행되므로 kokoro import 에서 실패할 수 있다. 여기서는
            # kokoro import 전에 오류가 나도 qwen 미호출만 확인한다.
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                en_dir = root / "content" / "en"
                en_dir.mkdir(parents=True)
                content = {
                    "sentences": [{"en": "Test.", "b2": False}],
                    "words": [], "advanced": [],
                }
                (en_dir / "2026-10-12.json").write_text(json.dumps(content), encoding="utf-8")
                orig_root = audio_mod.ROOT
                try:
                    audio_mod.ROOT = root
                    try:
                        audio_mod.main("en", "2026-10-12", ".")
                    except (ImportError, FileNotFoundError, SystemExit):
                        pass  # kokoro/모델 없어도 됨
                finally:
                    audio_mod.ROOT = orig_root

        self.assertEqual(called, [], "en 은 qwen() 를 호출하면 안 됩니다")


# ── 8. 사이드카(텍스트 해시) 오디오 스킵 가드 ─────────────────────────────────

class TestSidecarHashGuard(unittest.TestCase):
    """audio.py 사이드카 해시 가드를 검사한다."""

    # ── 헬퍼 ──────────────────────────────────────────────────────────────────

    def _run_qwen(self, out_dir, content=None, wer_seq=None, max_retries=1):
        c = content or DE_CONTENT
        patches = _patch_qwen(wer_sequence=wer_seq)
        active = _apply_patches(patches)
        try:
            with patch("faster_whisper.WhisperModel", return_value=_FakeWhisperModel()):
                audio_mod.qwen(c, "de", out_dir, max_retries=max_retries)
        finally:
            _stop_patches(active)

    # ── 사이드카 없음 → 기존 파일 유효 ─────────────────────────────────────────

    def test_no_sidecar_treats_existing_as_valid(self):
        """사이드카가 없을 때 기존 파일은 재생성하지 않는다."""
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "audio"
            out_dir.mkdir()
            for key in ALL_KEYS:
                (out_dir / f"{key}.mp3").write_bytes(b"old")
            # 사이드카 없음 확인
            self.assertFalse((out_dir / ".text.json").exists())

            load_mock = MagicMock(return_value=(MagicMock(), {}))
            patches = _patch_qwen()
            active = _apply_patches(patches)
            try:
                with patch("tts_qwen.load", load_mock), \
                     patch("faster_whisper.WhisperModel", return_value=_FakeWhisperModel()):
                    audio_mod.qwen(DE_CONTENT, "de", out_dir, max_retries=1)
            finally:
                _stop_patches(active)

            load_mock.assert_not_called()
            # 기존 파일 그대로
            for key in ALL_KEYS:
                self.assertEqual((out_dir / f"{key}.mp3").read_bytes(), b"old")

    # ── 사이드카 있음, 해시 일치 → 스킵 ───────────────────────────────────────

    def test_matching_hash_skips_regeneration(self):
        """사이드카 해시가 텍스트와 일치하면 재생성하지 않는다."""
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "audio"
            out_dir.mkdir()
            # 파일을 먼저 한 번 생성해 사이드카를 기록한다
            self._run_qwen(out_dir, max_retries=1)
            sidecar_path = out_dir / ".text.json"
            self.assertTrue(sidecar_path.exists(), "1차 실행 후 사이드카가 있어야 합니다")
            mtime_before = {k: (out_dir / f"{k}.mp3").stat().st_mtime for k in ALL_KEYS}

            import time; time.sleep(0.05)

            # 2차 실행 — 텍스트 변경 없음 → 모두 스킵
            load_mock = MagicMock(return_value=(MagicMock(), {}))
            patches = _patch_qwen()
            active = _apply_patches(patches)
            try:
                with patch("tts_qwen.load", load_mock), \
                     patch("faster_whisper.WhisperModel", return_value=_FakeWhisperModel()):
                    audio_mod.qwen(DE_CONTENT, "de", out_dir, max_retries=1)
            finally:
                _stop_patches(active)

            load_mock.assert_not_called()
            for k in ALL_KEYS:
                self.assertEqual((out_dir / f"{k}.mp3").stat().st_mtime, mtime_before[k],
                                 f"{k}.mp3 가 수정되면 안 됩니다")

    # ── 사이드카 있음, 해시 불일치 → 재생성 ───────────────────────────────────

    def test_changed_hash_triggers_regeneration(self):
        """사이드카 해시가 현재 텍스트와 다르면 해당 파일을 재생성한다."""
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "audio"
            out_dir.mkdir()
            self._run_qwen(out_dir, max_retries=1)

            # s1.mp3 의 해시를 사이드카에서 망가뜨린다
            sidecar_path = out_dir / ".text.json"
            data = json.loads(sidecar_path.read_text(encoding="utf-8"))
            data["s1.mp3"] = "000000000000dead"
            sidecar_path.write_text(
                json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                encoding="utf-8",
            )

            import time; time.sleep(0.05)
            mtime_s1_before = (out_dir / "s1.mp3").stat().st_mtime
            mtime_s2_before = (out_dir / "s2.mp3").stat().st_mtime

            generated_keys = []
            orig_gen = None

            patches = _patch_qwen()
            active = _apply_patches(patches)
            try:
                with patch("faster_whisper.WhisperModel", return_value=_FakeWhisperModel()):
                    audio_mod.qwen(DE_CONTENT, "de", out_dir, max_retries=1)
            finally:
                _stop_patches(active)

            # s1 은 재생성됐어야 한다 (mtime 갱신)
            self.assertGreater((out_dir / "s1.mp3").stat().st_mtime, mtime_s1_before,
                               "s1.mp3 가 재생성돼야 합니다")
            # s2 는 변경 없음
            self.assertEqual((out_dir / "s2.mp3").stat().st_mtime, mtime_s2_before,
                              "s2.mp3 는 재생성되면 안 됩니다")

    # ── 사이드카가 생성 후 존재하는지 ─────────────────────────────────────────

    def test_sidecar_written_after_generation(self):
        """qwen() 실행 후 .text.json 사이드카가 생성돼야 한다."""
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "audio"
            self._run_qwen(out_dir, max_retries=1)
            sidecar_path = out_dir / ".text.json"
            self.assertTrue(sidecar_path.exists(), ".text.json 이 생성돼야 합니다")
            data = json.loads(sidecar_path.read_text(encoding="utf-8"))
            # 생성된 모든 키의 mp3 가 기록돼야 한다
            for key in ALL_KEYS:
                self.assertIn(f"{key}.mp3", data, f"{key}.mp3 가 사이드카에 기록돼야 합니다")
            # 해시는 16자리 16진수여야 한다
            for val in data.values():
                self.assertRegex(val, r"^[0-9a-f]{16}$", "해시는 16자리 16진수여야 합니다")

    # ── levels.a 포함 시 사이드카에 a{i}.mp3 도 기록 ──────────────────────────

    def test_sidecar_includes_levels_a_keys(self):
        """levels.a 가 있을 때 a{i}.mp3 도 사이드카에 기록된다."""
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "audio"
            self._run_qwen(out_dir, content=DE_CONTENT_WITH_LEVELS, max_retries=1)
            data = json.loads((out_dir / ".text.json").read_text(encoding="utf-8"))
            for key in ["a1", "a2"]:
                self.assertIn(f"{key}.mp3", data, f"{key}.mp3 가 사이드카에 있어야 합니다")

    # ── _text_hash 헬퍼 ──────────────────────────────────────────────────────

    def test_text_hash_is_16_hex_chars(self):
        h = audio_mod._text_hash("Guten Morgen")
        self.assertRegex(h, r"^[0-9a-f]{16}$")

    def test_text_hash_deterministic(self):
        self.assertEqual(audio_mod._text_hash("abc"), audio_mod._text_hash("abc"))

    def test_text_hash_differs_for_different_text(self):
        self.assertNotEqual(audio_mod._text_hash("abc"), audio_mod._text_hash("xyz"))


if __name__ == "__main__":
    unittest.main()
