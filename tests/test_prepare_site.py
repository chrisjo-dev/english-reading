"""Pages artifact 허용 목록(tools/prepare_site.py)과 배포 워크플로 연결."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import langs  # noqa: E402
import prepare_site  # noqa: E402

PUBLIC = ["index.html", "CNAME", "404.html", ".nojekyll", "latest.json", "sitemap.xml", "robots.txt",
          "llms.txt", "rss.xml", "ads.txt", "favicon.ico", "icon-32.png", "apple-icon.png"]
PUBLIC_DIRS = ["_next/static", "assets/brand", "lily", "listen"]
PRIVATE = ["content/en/2026-01-01.json", "pool/en/001.json", "tools/publish.py", "tests/test_x.py",
           "landing/package.json", "docs/plan.md", "design/a.html", "founder/a.md", ".github/workflows/x.yml",
           "README.md", ".gitignore", "models/kokoro.onnx"]


class PrepareSiteTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "repo"
        files = PUBLIC + [d + "/x.txt" for d in PUBLIC_DIRS] + PRIVATE
        files += [f"{c}/2026-01-01/index.html" for c in langs.LANGS]
        for f in files:
            p = self.root / f
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("x", encoding="utf-8")
        self.out = prepare_site.prepare(self.root, Path(self.tmp.name) / "_site")

    def tearDown(self):
        self.tmp.cleanup()

    def test_public_files_copied(self):
        for f in PUBLIC + [d + "/x.txt" for d in PUBLIC_DIRS]:
            self.assertTrue((self.out / f).is_file(), f)

    def test_every_language_folder_copied(self):
        for c in langs.LANGS:
            self.assertTrue((self.out / c / "2026-01-01" / "index.html").is_file(), c)

    def test_private_paths_excluded(self):
        for f in PRIVATE:
            self.assertFalse((self.out / f).exists(), f)
        for top in ["content", "pool", "tools", "tests", "landing", "docs", "design", "founder", ".github", "models"]:
            self.assertFalse((self.out / top).exists(), top)

    def test_only_allowlisted_top_level(self):
        allowed = set(prepare_site.REQUIRED + prepare_site.FILES + prepare_site.dirs())
        self.assertLessEqual({p.name for p in self.out.iterdir()}, allowed)

    def test_missing_optional_skipped_and_rerun_replaces_out(self):
        (self.root / "rss.xml").unlink()
        (self.out / "stale.txt").write_text("old", encoding="utf-8")
        out = prepare_site.prepare(self.root, self.out)
        self.assertFalse((out / "rss.xml").exists())
        self.assertFalse((out / "stale.txt").exists())

    def test_missing_required_fails(self):
        (self.root / "CNAME").unlink()
        with self.assertRaises(SystemExit):
            prepare_site.prepare(self.root, Path(self.tmp.name) / "_site2")


class WorkflowWiringTest(unittest.TestCase):
    """메일이 걸린 워크플로는 push 뒤 같은 job 에서 배포하고, 배포 실패 때만 branch 빌드를 요청한다."""

    def test_deploy_before_email_with_fallback(self):
        for name in ["publish.yml", "weekly.yml", "backfill-word-audio.yml"]:
            text = (ROOT / ".github/workflows" / name).read_text(encoding="utf-8")
            with self.subTest(name):
                self.assertIn("id-token: write", text)
                self.assertIn("name: github-pages", text)
                i_push = text.index("git push")
                i_prep = text.index("python tools/prepare_site.py")
                i_deploy = text.index("actions/deploy-pages@")
                i_fb = text.index("pages/builds")
                self.assertLess(i_push, i_prep)
                self.assertLess(i_prep, i_deploy)
                self.assertLess(i_deploy, i_fb)
                self.assertEqual(text.count("pages/builds"), 1)
                self.assertIn("if: steps.deploy.outcome != 'success'", text)
                if "send_email.py" in text:
                    self.assertLess(i_fb, text.index("send_email.py"))

    def test_pages_workflow(self):
        text = (ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8")
        self.assertIn("group: pages", text)
        self.assertIn("python tools/prepare_site.py", text)
        self.assertIn("actions/deploy-pages@", text)


if __name__ == "__main__":
    unittest.main()
