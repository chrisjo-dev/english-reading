"""독해한입 자체 안내 페이지(소개, 개인정보처리방침, 연락처, 시안 design/own-pages O02, O05~O08).
하단 링크가 www.wspace.ai.kr 로 나가지 않는지, 새 페이지 생성과 구조화 데이터, 배포 목록, 사이트맵, 지난 페이지 하단 교체."""
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import langs  # noqa: E402
import prepare_site  # noqa: E402
import publish  # noqa: E402

LD = re.compile(r'<script type="application/ld\+json" id="ld">(.*?)</script>', re.S)
WSPACE_HREF = re.compile(r'href="https?://www\.wspace\.ai\.kr[^"]*"')
INFO = {"about": "AboutPage", "privacy": "WebPage", "contact": "ContactPage"}


def site_pages():
    """사이트에 올라가는 HTML 전부(랜딩 첫 화면, 지문, 목록, 복습, 안내, 손 페이지)."""
    out = [ROOT / "index.html", ROOT / "404.html"]
    for d in list(langs.LANGS) + ["lily", "listen"] + list(INFO):
        out += sorted((ROOT / d).rglob("index.html"))
    return out


class FooterTest(unittest.TestCase):
    def test_footer_links_own_pages(self):
        self.assertEqual(publish.FOOTER_HTML, '<footer class="site-footer"><a href="/about/">소개</a>'
                         '<a href="/privacy/">개인정보처리방침</a><a href="/contact/">연락처</a></footer>\n')
        self.assertNotIn("wspace", publish.FOOTER_HTML)

    def test_current_page_marked(self):
        self.assertIn('<a href="/privacy/" class="cur" aria-current="page">개인정보처리방침</a>', publish.footer_links("/privacy/"))

    def test_no_wspace_link_on_site(self):
        for p in site_pages():
            s = p.read_text(encoding="utf-8")
            self.assertEqual(WSPACE_HREF.findall(s), [], p)
            if "site-footer" in s and p.parent.name not in INFO:
                self.assertIn(publish.footer_links(), s, p)

    def test_landing_footer_links(self):
        src = (ROOT / "landing/src/components/Footer.tsx").read_text(encoding="utf-8")
        self.assertNotIn("wspace", src)
        for h, _ in publish.FOOTER_PAGES:
            self.assertIn(f'href: "{h}"', src)

    def test_old_footer_replaced_idempotent(self):
        """지난 페이지의 옛 wspace 하단을 새 하단으로 바꾸고, 두 번 돌려도 같다."""
        day = publish.days_of("en")[0]
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            (tmp / "en" / day).mkdir(parents=True)
            (tmp / "content" / "en").mkdir(parents=True)
            shutil.copy(ROOT / "content" / "en" / f"{day}.json", tmp / "content" / "en" / f"{day}.json")
            page = (ROOT / "en" / day / "index.html").read_text(encoding="utf-8")
            old = page.replace(publish.footer_links(), publish.OLD_FOOTER_LINKS, 1)
            self.assertIn(publish.OLD_FOOTER_LINKS, old)
            f = tmp / "en" / day / "index.html"
            f.write_text(old, encoding="utf-8")
            with mock.patch.object(publish, "ROOT", tmp):
                publish.patch_page("en", day)
                once = f.read_text(encoding="utf-8")
                publish.patch_page("en", day)
                twice = f.read_text(encoding="utf-8")
        self.assertNotIn("www.wspace.ai.kr", once)
        self.assertEqual(once.count('<footer class="site-footer">'), 1)
        self.assertIn(publish.footer_links(), once)
        self.assertEqual(once, twice)


class InfoPagesTest(unittest.TestCase):
    def build(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        with mock.patch.object(publish, "ROOT", Path(tmp.name)):
            publish.rebuild_info_pages()
            first = {d: (Path(tmp.name) / d / "index.html").read_text(encoding="utf-8") for d in INFO}
            publish.rebuild_info_pages()
            second = {d: (Path(tmp.name) / d / "index.html").read_text(encoding="utf-8") for d in INFO}
        return first, second

    def test_generated_idempotent_and_committed(self):
        first, second = self.build()
        self.assertEqual(first, second)
        for d in INFO:
            self.assertEqual(first[d], (ROOT / d / "index.html").read_text(encoding="utf-8"), d)

    def test_page_shape(self):
        pages, _ = self.build()
        for d, s in pages.items():
            url = f"{langs.SITE}/{d}/"
            self.assertIn(f'<link rel="canonical" href="{url}">', s)
            self.assertIn(f'<meta property="og:url" content="{url}">', s)
            self.assertIn('<header class="gnb">', s)
            self.assertIn('<script id="gnb-js">', s)
            self.assertIn('<script id="mig">', s)
            self.assertIn(f'<a href="/{d}/" class="cur" aria-current="page">', s)
            self.assertNotIn("Chris Jo", s)
            self.assertNotIn("\u00b7", s)  # 가운뎃점 금지
            # 언어 탭에 '지금 보는 중' 표시가 없다(안내 페이지는 언어 페이지가 아니다)
            self.assertNotIn('aria-current="page">영어', s)
        self.assertIn('class="fb"', pages["about"])
        self.assertIn('class="fb"', pages["privacy"])
        self.assertNotIn('<section class="fb"', pages["contact"])
        self.assertIn('data-fb="bug"', pages["contact"])
        self.assertIn('<script id="fb-js">', pages["contact"])
        self.assertIn("릴리 그림책 듣기 페이지의 '듣기만' 설정", pages["privacy"])
        for anchor in ("collect", "storage", "cookies", "retention", "ask"):
            self.assertIn(f'href="#{anchor}"', pages["privacy"])
            self.assertIn(f'id="{anchor}"', pages["privacy"])

    def test_json_ld(self):
        pages, _ = self.build()
        for d, s in pages.items():
            blocks = LD.findall(s)
            self.assertEqual(len(blocks), 1, d)
            graph = json.loads(blocks[0])["@graph"]
            types = [n["@type"] for n in graph]
            self.assertIn(INFO[d], types)
            self.assertIn("BreadcrumbList", types)
            self.assertNotIn("Person", types)
            self.assertNotIn("founder", blocks[0])
            page = next(n for n in graph if n["@type"] == INFO[d])
            self.assertEqual(page["@id"], f"{langs.SITE}/{d}/#page")
            self.assertEqual(page["isPartOf"], {"@id": f"{langs.SITE}/#website"})
            ids = {n["@id"] for n in graph if "@id" in n}
            self.assertIn(f"{langs.SITE}/#organization", ids)
            self.assertIn(f"{langs.SITE}/#website", ids)
            crumbs = next(n for n in graph if n["@type"] == "BreadcrumbList")["itemListElement"]
            self.assertEqual(crumbs[-1]["item"], f"{langs.SITE}/{d}/")

    def test_no_person_in_landing_ld(self):
        src = (ROOT / "landing/src/app/layout.tsx").read_text(encoding="utf-8")
        self.assertNotIn('"Person"', src)
        self.assertNotIn("founder:", src)
        self.assertNotIn("Chris Jo", (ROOT / "index.html").read_text(encoding="utf-8"))


class DeployTest(unittest.TestCase):
    def test_prepare_site_copies_info_pages(self):
        with tempfile.TemporaryDirectory() as t:
            out = prepare_site.prepare(ROOT, Path(t) / "_site")
            for d in INFO:
                self.assertTrue((out / d / "index.html").is_file(), d)

    def test_sitemap_and_llms(self):
        sm = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
        for d in INFO:
            self.assertIn(f"<loc>{langs.SITE}/{d}/</loc>", sm)
        llms = (ROOT / "llms.txt").read_text(encoding="utf-8")
        self.assertNotIn("wspace", llms)
        self.assertIn(f"({langs.SITE}/privacy/)", llms)
        self.assertIn(f"{langs.SITE}/about/", llms)


if __name__ == "__main__":
    unittest.main()
