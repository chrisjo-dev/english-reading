"""도메인 전환(read.wspace.ai.kr -> dokhaehanip.com) 학습 기록 받기 스크립트와 주소 확인.

python -m pytest -q tests/test_migrate.py
"""
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import langs  # noqa: E402
import migrate  # noqa: E402


def pages():
    out = [ROOT / "index.html"]
    for code in langs.LANGS:
        out += sorted((ROOT / code).glob("20*/index.html"))
        out += [p for p in (ROOT / code / "index.html", ROOT / code / "archive" / "index.html") if p.exists()]
        out += sorted((ROOT / code / "review").glob("*/index.html"))
    return out


class MigrateScript(unittest.TestCase):
    def test_site(self):
        self.assertEqual(langs.SITE, "https://dokhaehanip.com")
        self.assertEqual((ROOT / "CNAME").read_text().strip(), "dokhaehanip.com")
        self.assertIn('export const SITE = "https://dokhaehanip.com";', (ROOT / "landing/src/lib/site.ts").read_text())

    def test_keys_in_js(self):
        for k in migrate.KEYS + migrate.PREFIXES:
            self.assertIn(f"'{k}'", migrate.JS)
        self.assertIn("#mig=", migrate.JS)
        self.assertIn("localStorage.getItem(k)===null", migrate.JS)  # 새 쪽에 이미 있는 키는 덮지 않는다
        self.assertIn("history.replaceState", migrate.JS)
        self.assertNotIn('"', migrate.JS)  # 랜딩 TS 문자열에 그대로 옮긴다

    def test_apply_idempotent(self):
        page = '<!doctype html>\n<head>\n<meta charset="utf-8">\n<title>t</title>'
        once = migrate.apply(page)
        self.assertEqual(once.count('id="mig"'), 1)
        self.assertTrue(once.index('id="mig"') > once.index("<meta charset"))
        self.assertEqual(migrate.apply(once), once)
        stale = once.replace(migrate.JS, "old()")
        self.assertEqual(migrate.apply(stale), once)  # 예전 문자열은 지금 문자열로 바뀐다

    def test_landing_same_js(self):
        ts = (ROOT / "landing/src/lib/migrate.ts").read_text()
        self.assertIn(f'export const MIGRATE_JS = "{migrate.JS}";', ts)

    def test_all_pages_have_script(self):
        ps = pages()
        self.assertGreater(len(ps), 50)
        for p in ps:
            s = p.read_text(encoding="utf-8")
            self.assertEqual(s.count(migrate.TAG), 1, p)
            # 수준을 읽는 머리 스크립트보다 먼저 돈다
            lv = s.find("localStorage.getItem('read_level")
            if lv >= 0:
                self.assertLess(s.index(migrate.TAG), lv, p)
        self.assertIn(migrate.TAG, (ROOT / "tools/template.html").read_text(encoding="utf-8"))

    def test_no_old_domain_in_generated(self):
        for p in pages() + [ROOT / f for f in ("sitemap.xml", "rss.xml", "llms.txt", "robots.txt")]:
            self.assertNotIn("read.wspace.ai.kr", p.read_text(encoding="utf-8").replace(migrate.JS, ""), p)

    def test_page_urls(self):
        s = (ROOT / "en/2026-10-04/index.html").read_text(encoding="utf-8")
        self.assertIn('<link rel="canonical" href="https://dokhaehanip.com/en/2026-10-04/">', s)
        self.assertIn('<meta property="og:url" content="https://dokhaehanip.com/en/2026-10-04/">', s)
        self.assertIn('"@id":"https://dokhaehanip.com/en/2026-10-04/#reading"', s)
        # 하단 링크는 독해한입 자체 안내 페이지(design/own-pages O02)
        self.assertIn('<a href="/privacy/">개인정보처리방침</a>', s)

    @unittest.skipUnless(shutil.which("node"), "node 없음")
    def test_roundtrip_node(self):
        """Worker 쪽 인코딩(UTF-8 -> base64url)을 받는 스크립트가 그대로 되돌리는지 Node 로 확인."""
        data = {"drill:v1": '{"w":{"猫":1,"Straße":2,"단어":3}}', "read_level:ja": "a", "vote:en/2026-11-01": "up",
                "read_speed": "0.9", "other": "x"}
        js = r"""
const data = JSON.parse(process.argv[1]); const JS = process.argv[2];
const b = new TextEncoder().encode(JSON.stringify(data)); let s = '';
for (const x of b) s += String.fromCharCode(x);
const enc = btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
const store = new Map([['read_speed', '1.2']]);
const g = { location: { hash: '#mig=' + enc, pathname: '/en/2026-11-01/', search: '?level=a' },
  localStorage: { getItem: k => store.has(k) ? store.get(k) : null, setItem: (k, v) => store.set(k, String(v)) },
  history: { replaceState: (a, b, u) => { g.replaced = u; } }, atob, TextDecoder, Uint8Array, JSON, Object };
new Function(...Object.keys(g), JS)(...Object.values(g));
console.log(JSON.stringify({ store: Object.fromEntries(store), replaced: g.replaced }));
"""
        import json
        r = subprocess.run(["node", "-e", js, json.dumps(data, ensure_ascii=False), migrate.JS],
                           capture_output=True, text=True, check=True)
        out = json.loads(r.stdout)
        self.assertEqual(out["store"]["drill:v1"], data["drill:v1"])
        self.assertEqual(out["store"]["read_level:ja"], "a")
        self.assertEqual(out["store"]["vote:en/2026-11-01"], "up")
        self.assertEqual(out["store"]["read_speed"], "1.2")  # 이미 있던 값은 그대로
        self.assertNotIn("other", out["store"])  # 정해진 키만 받는다
        self.assertEqual(out["replaced"], "/en/2026-11-01/?level=a")

    @unittest.skipUnless(shutil.which("node"), "node 없음")
    def test_other_hash_untouched(self):
        js = r"""
const g = { location: { hash: '#level-a', pathname: '/en/', search: '' }, localStorage: { getItem: () => null, setItem: () => { throw 1; } },
  history: { replaceState: () => { g.replaced = true; } }, atob, TextDecoder, Uint8Array, JSON, Object };
new Function(...Object.keys(g), process.argv[1])(...Object.values(g));
console.log(g.replaced ? 'replaced' : 'kept');
"""
        r = subprocess.run(["node", "-e", js, migrate.JS], capture_output=True, text=True, check=True)
        self.assertEqual(r.stdout.strip(), "kept")

    def test_worker_keys_match(self):
        w = (ROOT / "tools/cf/read-redirect.js").read_text()
        keys = re.search(r"export const KEYS = (\[.*?\]);", w).group(1)
        prefixes = re.search(r"export const PREFIXES = (\[.*?\]);", w).group(1)
        import json
        self.assertEqual(json.loads(keys), migrate.KEYS)
        self.assertEqual(json.loads(prefixes), migrate.PREFIXES)


if __name__ == "__main__":
    unittest.main()
