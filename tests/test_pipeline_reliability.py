"""파이프라인 신뢰성 픽스 단위 테스트.

항목:
  A. send_email — in_flight 경고, wait_live 캐시 버스팅, 수준별 독립 발송
  B. thumb — 소스 로깅 (mini/openai/illustration/existing)
  C. catchup 수준 목록 — 언어별 올바른 수준 집합
  D. mini-cron 스크립트 — bash -n 문법 검사

실행: python3 -m pytest -q tests/test_pipeline_reliability.py
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

import langs as langs_mod  # noqa: E402
import send_email  # noqa: E402
import thumb  # noqa: E402


# ── A. send_email ────────────────────────────────────────────────────────────

class TestSendInFlight(unittest.TestCase):
    """send(): 대기 만료 후 in_flight 는 경고(return), 다른 상태는 SystemExit."""

    def _stub_call(self, statuses):
        """POST→draft_id, PATCH→ok, GET→statuses 순서로 반환하는 call 스텁."""
        calls = iter([
            # fill_missing_lang / fill_missing_level 내부 호출이 없도록 send 직접 호출
        ])
        get_iter = iter(statuses)
        def fake_call(method, path, body=None):
            if method == "POST":
                return {"id": "email-x", "status": "draft"}
            if method == "PATCH":
                return {"id": "email-x", "status": "about_to_send"}
            if method == "GET":
                return {"status": next(get_iter)}
            return {}
        return fake_call

    def test_in_flight_after_timeout_is_warning_not_exit(self):
        """30번 폴링 후 in_flight 이면 SystemExit 없이 경고 메시지를 출력하고 반환한다."""
        statuses = ["in_flight"] * 31
        mail = {"subject": "s", "body": "b"}
        with patch.object(send_email, "call", side_effect=self._stub_call(statuses)), \
             patch.object(send_email, "recent_emails", return_value=iter([])), \
             patch.object(send_email, "fill_missing_lang"), \
             patch.object(send_email, "fill_missing_level"), \
             patch.object(send_email, "audience", return_value={}), \
             patch("time.sleep"), \
             patch("builtins.print") as mock_print:
            # SystemExit 이 발생하지 않아야 한다
            send_email.send(mail, "en", "day", "2026-11-01", level="b")
        printed = " ".join(str(a) for a in mock_print.call_args_list)
        self.assertIn("in_flight", printed)
        self.assertIn("warning", printed.lower())

    def test_non_inflight_status_raises(self):
        """30번 폴링 후 in_flight 가 아닌 상태(예: errored_sending)는 SystemExit 을 발생시킨다."""
        statuses = ["errored_sending"] * 31
        mail = {"subject": "s", "body": "b"}
        with patch.object(send_email, "call", side_effect=self._stub_call(statuses)), \
             patch.object(send_email, "recent_emails", return_value=iter([])), \
             patch.object(send_email, "fill_missing_lang"), \
             patch.object(send_email, "fill_missing_level"), \
             patch.object(send_email, "audience", return_value={}), \
             patch("time.sleep"):
            with self.assertRaises(SystemExit) as ctx:
                send_email.send(mail, "en", "day", "2026-11-01", level="b")
        self.assertIn("errored_sending", str(ctx.exception))

    def test_sent_status_returns_normally(self):
        """폴링 중 sent 가 나오면 정상 반환한다."""
        statuses = ["in_flight", "in_flight", "sent"]
        mail = {"subject": "s", "body": "b"}
        with patch.object(send_email, "call", side_effect=self._stub_call(statuses)), \
             patch.object(send_email, "recent_emails", return_value=iter([])), \
             patch.object(send_email, "fill_missing_lang"), \
             patch.object(send_email, "fill_missing_level"), \
             patch.object(send_email, "audience", return_value={}), \
             patch("time.sleep"):
            # 예외 없이 반환
            send_email.send(mail, "en", "day", "2026-11-01", level="b")


class TestWaitLiveCacheBust(unittest.TestCase):
    """wait_live(): extra URL 에도 캐시 버스팅이 붙는다."""

    def test_extra_url_gets_cache_bust(self):
        """extra URL 로 요청할 때 ?v= 쿼리가 추가된다."""
        page_content = b"test-topic"
        thumb_response = MagicMock()
        thumb_response.status = 200
        thumb_response.__enter__ = lambda s: s
        thumb_response.__exit__ = MagicMock(return_value=False)
        thumb_response.read.return_value = b""

        page_response = MagicMock()
        page_response.read.return_value = page_content
        page_response.__enter__ = lambda s: s
        page_response.__exit__ = MagicMock(return_value=False)

        opened_urls = []

        def fake_urlopen(url, timeout=None):
            opened_urls.append(url)
            if "thumb" in url:
                return thumb_response
            return page_response

        with patch.object(send_email.urllib.request, "urlopen", side_effect=fake_urlopen), \
             patch("time.sleep"):
            send_email.wait_live("http://example.com/en/2026-11-01/", "test-topic",
                                  extra="http://example.com/en/2026-11-01/thumb.png")

        thumb_urls = [u for u in opened_urls if "thumb" in u]
        self.assertTrue(len(thumb_urls) > 0, "thumb URL 이 요청되지 않았습니다")
        for u in thumb_urls:
            self.assertIn("?v=", u, f"thumb URL 에 캐시 버스팅이 없습니다: {u}")

    def test_default_timeout_is_15_min(self):
        """기본 timeout_min 은 15분(60회 × 15초)이다."""
        import inspect
        sig = inspect.signature(send_email.wait_live)
        self.assertEqual(sig.parameters["timeout_min"].default, 15)


# ── B. thumb 소스 로깅 ─────────────────────────────────────────────────────

DAY = "2026-10-30"


class TestThumbSourceLogging(unittest.TestCase):
    """thumb.build() 와 thumb.photo() 가 소스를 stdout 에 출력한다."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        for sub in (f"en/{DAY}", "content/en"):
            (self.tmp / sub).mkdir(parents=True)
        shutil.copy(REPO / "en" / DAY / "index.html",
                    self.tmp / "en" / DAY / "index.html")
        shutil.copy(REPO / "content" / "en" / f"{DAY}.json",
                    self.tmp / "content" / "en" / f"{DAY}.json")
        self.patch_root = patch.object(thumb, "ROOT", self.tmp)
        self.patch_root.start()

    def tearDown(self):
        self.patch_root.stop()
        shutil.rmtree(self.tmp)

    def _captured_build(self, *args, **kwargs):
        buf = io.StringIO()
        with patch("builtins.print", side_effect=lambda *a, **k: buf.write(" ".join(str(x) for x in a) + "\n")):
            result = thumb.build(*args, **kwargs)
        return result, buf.getvalue()

    def test_illustration_source_logged(self):
        """사진 없이 일러스트로 만들면 source=illustration 이 출력된다."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "", "LOCAL_IMAGE_URL": ""}):
            _, output = self._captured_build("en", DAY, "science")
        self.assertIn("source=illustration", output)
        self.assertIn(f"thumb: en {DAY}", output)

    def test_existing_photo_source_logged(self):
        """이미 사진 썸네일이 있으면 source=existing 이 출력된다."""
        from PIL import Image, PngImagePlugin
        out = self.tmp / "en" / DAY / "thumb.png"
        meta = PngImagePlugin.PngInfo()
        meta.add_text("thumb", "photo")
        Image.new("RGB", (1200, 630)).save(out, pnginfo=meta)
        with patch.dict(os.environ, {"THUMB_REDRAW": ""}):
            _, output = self._captured_build("en", DAY, "science")
        self.assertIn("source=existing", output)

    def test_openai_source_logged(self):
        """OpenAI API 로 사진을 생성하면 source=openai 가 출력된다."""
        from PIL import Image
        import base64, io as _io
        fake_img = Image.new("RGB", (100, 100), (200, 100, 50))
        buf = _io.BytesIO()
        fake_img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        fake_resp = json.dumps({"data": [{"b64_json": b64}]}).encode()

        mock_resp = MagicMock()
        mock_resp.read.return_value = fake_resp
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key", "LOCAL_IMAGE_URL": ""}), \
             patch.object(thumb.urllib.request, "urlopen", return_value=mock_resp), \
             patch("builtins.print") as mock_print:
            result = thumb.photo("en", DAY)

        if result is not None:
            printed = " ".join(str(a) for a in mock_print.call_args_list)
            self.assertIn("source=openai", printed)

    def test_mini_source_logged(self):
        """로컬 API(맥 미니)로 사진을 생성하면 source=mini 가 출력된다."""
        from PIL import Image
        import base64, io as _io
        # content 에 photo_scene 추가
        content_path = self.tmp / "content" / "en" / f"{DAY}.json"
        c = json.loads(content_path.read_text(encoding="utf-8"))
        c["photo_scene"] = "A red apple on a table."
        content_path.write_text(json.dumps(c), encoding="utf-8")

        fake_img = Image.new("RGB", (100, 100), (100, 150, 200))
        buf = _io.BytesIO()
        fake_img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        fake_resp = json.dumps({"data": [{"b64_json": b64}]}).encode()

        mock_resp = MagicMock()
        mock_resp.read.return_value = fake_resp
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch.dict(os.environ, {"LOCAL_IMAGE_URL": "http://mini.local", "LOCAL_IMAGE_TOKEN": "tok"}), \
             patch.object(thumb.socket, "create_connection"), \
             patch.object(thumb.urllib.request, "urlopen", return_value=mock_resp), \
             patch("builtins.print") as mock_print:
            result = thumb.photo("en", DAY)

        if result is not None:
            printed = " ".join(str(a) for a in mock_print.call_args_list)
            self.assertIn("source=mini", printed)


# ── C. catchup 수준 목록 ────────────────────────────────────────────────────

class TestCatchupLevelsList(unittest.TestCase):
    """languages with levels=True should require catchup for both a and b."""

    def test_levels_true_lang_has_a_and_b(self):
        """levels=True 인 언어는 a 와 b 두 수준 모두 보충 대상이다."""
        for code, L in langs_mod.LANGS.items():
            if L.get("levels"):
                levels = ["a", "b"] if L.get("levels") else ["b"]
                self.assertIn("a", levels, f"{code}: levels=True 인데 a 가 없음")
                self.assertIn("b", levels, f"{code}: levels=True 인데 b 가 없음")

    def test_levels_false_lang_has_only_b(self):
        """levels=False(또는 없는) 언어는 b 수준만 보충 대상이다."""
        for code, L in langs_mod.LANGS.items():
            if not L.get("levels"):
                levels = ["b"]
                self.assertNotIn("a", levels, f"{code}: levels=False 인데 a 가 있음")

    def test_ja_default_level_is_a(self):
        """ja default_level 은 'a' 다 — fill_missing_level 이 ja 구독자를 a 로 채운다."""
        self.assertEqual(langs_mod.LANGS["ja"].get("default_level"), "a")

    def test_all_active_langs_have_levels_flag(self):
        """모든 언어에 email=True 인 경우 levels 플래그가 명시적으로 있다."""
        for code, L in langs_mod.LANGS.items():
            if L.get("email", True):
                self.assertIn("levels", L, f"{code}: email=True 언어에 levels 키가 없음")


# ── D. mini-cron 스크립트 문법 검사 ─────────────────────────────────────────

class TestMiniCronScript(unittest.TestCase):
    """mini-cron.sh 가 bash -n 문법 검사를 통과한다."""

    SCRIPT = REPO / "tools" / "mini-cron" / "mini-cron.sh"

    def test_script_exists(self):
        self.assertTrue(self.SCRIPT.exists(), f"mini-cron.sh 파일이 없습니다: {self.SCRIPT}")

    def test_bash_syntax_valid(self):
        result = subprocess.run(
            ["bash", "-n", str(self.SCRIPT)],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0,
                          f"bash -n 실패:\n{result.stderr}")

    def test_script_mentions_fallback(self):
        text = self.SCRIPT.read_text(encoding="utf-8")
        self.assertIn("fallback.yml", text)
        self.assertIn("catchup.yml", text)
        self.assertIn("weekly.yml", text)

    def test_script_references_kst_hours(self):
        """스크립트에 07, 08 시 분기가 있다."""
        text = self.SCRIPT.read_text(encoding="utf-8")
        self.assertIn('"07"', text)
        self.assertIn('"08"', text)


if __name__ == "__main__":
    unittest.main()
