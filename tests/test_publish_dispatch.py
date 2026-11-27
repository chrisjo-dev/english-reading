"""publish 를 한 번만 부르는지, 한 번에 받은 여러 날짜와 언어를 제대로 푸는지 확인한다.

publish 그룹의 대기 실행은 하나뿐이라 따로 여러 번 부르면 앞선 대기 실행이 알림 없이 취소된다
(2026-11-25 de 7편 중 5편 취소).

실행: python3 -m pytest -q tests/test_publish_dispatch.py
"""
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

WF = Path(__file__).resolve().parent.parent / ".github/workflows"


def pick_script():
    """publish.yml 의 'Pick language and day' 단계 run 블록을 꺼낸다(CI 에 PyYAML 이 없어 글자로 자른다)."""
    text = (WF / "publish.yml").read_text(encoding="utf-8")
    block = text.split("- name: Pick language and day", 1)[1].split("run: |\n", 1)[1]
    lines = []
    for line in block.splitlines():
        if line.strip() and not line.startswith("          "):
            break
        lines.append(line[10:])
    # 이 단계에서 ${{ }} 는 push 경로(github.event.*)에만 남는다. dispatch 경로 시험에는 쓰이지 않는다.
    return re.sub(r"\$\{\{[^}]*\}\}", "", "\n".join(lines))


def run_pick(lang, day):
    with tempfile.NamedTemporaryFile("r", suffix=".out") as out:
        env = dict(os.environ, IN_LANG=lang, IN_DAY=day, GITHUB_OUTPUT=out.name)
        r = subprocess.run(["bash", "-e", "-c", pick_script()], env=env, capture_output=True, text=True)
        got = dict(l.split("=", 1) for l in Path(out.name).read_text().splitlines() if "=" in l)
    return r.returncode, got.get("pairs")


class TestPickInputs(unittest.TestCase):
    def test_single_day_keeps_old_form(self):
        self.assertEqual(run_pick("en", "2026-11-25"), (0, "en:2026-11-25"))

    def test_many_days_one_lang(self):
        self.assertEqual(run_pick("de", "2026-10-30 2026-11-01"), (0, "de:2026-10-30 de:2026-11-01"))

    def test_mixed_langs(self):
        self.assertEqual(run_pick("en", "en:2026-11-25 ja:2026-11-25"), (0, "en:2026-11-25 ja:2026-11-25"))

    def test_rejects_bad_input(self):
        for bad in ("2026-11-2", "fr:2026-11-25", "en:2026-11-25;id", "$(id)"):
            code, _ = run_pick("en", bad)
            self.assertNotEqual(code, 0, bad)


class TestCallersDispatchOnce(unittest.TestCase):
    """de-audio, fallback 이 publish.yml 을 반복문 안에서 부르지 않아야 한다."""

    def _trigger_step(self, name):
        text = (WF / name).read_text(encoding="utf-8")
        return text.split("- name: Trigger publish", 1)[1].split("\n      - name:", 1)[0]

    def test_de_audio(self):
        step = self._trigger_step("de-audio.yml")
        self.assertEqual(step.count("gh workflow run publish.yml"), 1)
        self.assertNotIn("for day in", step)
        self.assertIn('day="$(echo $days)"', step, "모든 날짜를 넘겨야 한다")

    def test_fallback(self):
        step = self._trigger_step("fallback.yml")
        self.assertEqual(step.count("gh workflow run publish.yml"), 1)
        loop = step.split("for pair in", 1)[1].split("done", 1)[0]
        self.assertNotIn("gh workflow run publish.yml", loop)
        self.assertIn('rest="$rest $pair"', loop, "en, ja 쌍을 모두 모아야 한다")
        self.assertIn('-f day="${rest# }"', step, "모은 쌍을 모두 넘겨야 한다")


if __name__ == "__main__":
    unittest.main()
