"""SEO, GEO 1차, 2차(이슈 #25): 지문 제목, JSON-LD, 목록 canonical, 사이트맵, llms.txt, rss.xml, 도메인 상수,
목록과 복습 JSON-LD, RSS 자동 발견, robots.txt Content-Signal, 다른 이름 목록."""
import json
import re
import shutil
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import langs  # noqa: E402
import publish  # noqa: E402
import weekly  # noqa: E402

LD = re.compile(r'<script type="application/ld\+json" id="ld">(.*?)</script>', re.S)


def ld_of(page):
    blocks = LD.findall(page)
    assert len(blocks) == 1, f"JSON-LD 블록 수 {len(blocks)}"
    return json.loads(blocks[0])


def undefined_ids(data):
    """{"@id": ...} 만 있는 참조 중 같은 그래프 안에 정의(다른 속성이 있는 노드)가 없는 것."""
    defined, refs = set(), set()

    def walk(x):
        if isinstance(x, dict):
            if "@id" in x:
                (refs if set(x) == {"@id"} else defined).add(x["@id"])
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(data)
    return refs - defined


RSS_LINK = '<link rel="alternate" type="application/rss+xml" title="독해한입" href="/rss.xml">'


class ReadingPageTest(unittest.TestCase):
    """지난 페이지 모양(예전 제목, JSON-LD 없음)에서 patch_page 를 두 번 돌린다."""

    def patched(self, lang, day, content=None):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        (tmp / lang / day).mkdir(parents=True)
        for f in ("photo.jpg", "thumb.png"):
            if (ROOT / lang / day / f).exists():
                shutil.copy(ROOT / lang / day / f, tmp / lang / day / f)
        page = (ROOT / lang / day / "index.html").read_text(encoding="utf-8")
        page = LD.sub("", page).replace(' fetchpriority="high"', "")
        page = re.sub(r"<title>[^<]*</title>", f"<title>{langs.LANGS[lang]['name']} 읽기, 11월 12일 | 독해한입</title>", page, count=1)
        (tmp / lang / day / "index.html").write_text(page, encoding="utf-8")
        c = content if content is not None else json.loads((ROOT / "content" / lang / f"{day}.json").read_text(encoding="utf-8"))
        (tmp / "content" / lang).mkdir(parents=True)
        (tmp / "content" / lang / f"{day}.json").write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
        with mock.patch.object(publish, "ROOT", tmp):
            publish.patch_page(lang, day)
            once = (tmp / lang / day / "index.html").read_text(encoding="utf-8")
            publish.patch_page(lang, day)
            twice = (tmp / lang / day / "index.html").read_text(encoding="utf-8")
        self.assertEqual(once, twice, "patch_page 를 두 번 돌리면 결과가 같아야 한다")
        return once, c

    def test_title_has_topic_level_and_year(self):
        page, c = self.patched("en", "2026-11-12")
        title = f"{c['title_ko']}: 영어 독해 B1~B2, 2026년 11월 12일 | 독해한입"
        self.assertIn(f"<title>{title}</title>", page)
        self.assertIn(f'<meta property="og:title" content="{title}">', page)
        self.assertEqual(page.count("<title>"), 1)

    def test_ja_title_uses_jlpt_level_and_preconnects_fonts(self):
        page, _ = self.patched("ja", "2026-11-12")
        self.assertRegex(page, r"<title>[^<]+ 일본어 독해 JLPT N3, 2026년 11월 12일 \| 독해한입</title>")
        self.assertIn('<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>', page)
        self.assertEqual(page.count('rel="preconnect" href="https://cdnjs.cloudflare.com"'), 1)

    def test_old_ja_page_keeps_its_own_level(self):
        """2026-10-29 전 일본어 지문은 본문이 N4~N5 였다. 지금 기준(N3)으로 잘못 적지 않는다."""
        page, _ = self.patched("ja", "2026-10-20")
        self.assertRegex(page, r"<title>[^<]+ 일본어 독해 JLPT N4~N5, 2026년 10월 20일 \| 독해한입</title>")
        self.assertEqual(ld_of(page)["@graph"][0]["educationalLevel"], "JLPT N4~N5")

    def test_jsonld_article_learning_resource_breadcrumb(self):
        page, c = self.patched("en", "2026-11-12")
        g = ld_of(page)["@graph"]
        art = next(n for n in g if "Article" in n["@type"])
        self.assertEqual(art["@type"], ["Article", "LearningResource"])
        url = f"{langs.SITE}/en/2026-11-12/"
        self.assertEqual(art["url"], url)
        self.assertEqual(art["headline"], c["title_ko"])
        self.assertEqual(art["datePublished"], "2026-11-12")
        self.assertEqual(art["inLanguage"], "en")
        self.assertIn("CEFR B1~B2", art["educationalLevel"])
        self.assertEqual(art["keywords"], c["keywords"])
        self.assertEqual(art["isBasedOn"]["url"], c["source"]["url"])
        self.assertEqual(art["publisher"], {"@id": f"{langs.SITE}/#organization"})
        self.assertNotIn("alternateName", json.dumps(art), "별칭은 Organization 노드에만 둔다")
        org = next(n for n in g if n["@type"] == "Organization")
        self.assertEqual(org["@id"], f"{langs.SITE}/#organization")
        self.assertEqual(org["alternateName"], langs.ALT_NAMES)
        self.assertEqual(org["sameAs"], langs.SAME_AS)
        self.assertEqual(org["logo"]["url"], f"{langs.SITE}/assets/brand/icon-512.png")
        self.assertEqual(next(n for n in g if n["@type"] == "WebSite")["@id"], f"{langs.SITE}/#website")
        self.assertEqual(undefined_ids(ld_of(page)), set())
        crumbs = next(n for n in g if n["@type"] == "BreadcrumbList")["itemListElement"]
        self.assertEqual([i["item"] for i in crumbs], [f"{langs.SITE}/", f"{langs.SITE}/en/", url])

    def test_no_source_means_no_is_based_on(self):
        c = json.loads((ROOT / "content" / "de" / "2026-11-12.json").read_text(encoding="utf-8"))
        c["source"] = None
        page, _ = self.patched("de", "2026-11-12", c)
        art = ld_of(page)["@graph"][0]
        self.assertNotIn("isBasedOn", art)
        self.assertEqual(art["inLanguage"], "de")

    def test_rss_alternate_link_once(self):
        page, _ = self.patched("ja", "2026-10-20")
        self.assertEqual(page.count('type="application/rss+xml"'), 1)
        self.assertIn(RSS_LINK, page)

    def test_hero_photo_loads_first(self):
        page, _ = self.patched("en", "2026-11-12")
        if (ROOT / "en" / "2026-11-12" / "photo.jpg").exists():
            self.assertEqual(page.count('fetchpriority="high"'), 1)


class GeneratedPagesTest(unittest.TestCase):
    """저장소에 재생성된 실제 페이지."""

    def test_every_reading_page_has_valid_jsonld(self):
        for code in langs.LANGS:
            for day in publish.days_of(code):
                page = (ROOT / code / day / "index.html").read_text(encoding="utf-8")
                art = ld_of(page)["@graph"][0]
                self.assertEqual(art["datePublished"], day, f"{code}/{day}")

    def test_no_nul_bytes(self):
        """drill CSS 의 "\\00a0" 이 파이썬에서 NUL 로 바뀌어 페이지에 들어갔던 버그(R1)."""
        files = [ROOT / "index.html"] + [p for code in langs.LANGS for p in (ROOT / code).rglob("*.html")]
        bad = [str(p.relative_to(ROOT)) for p in files if b"\x00" in p.read_bytes()]
        self.assertEqual(bad, [])

    def test_jsonld_ids_resolve_and_rss_link(self):
        for code in langs.LANGS:
            pages = [ROOT / code / d / "index.html" for d in publish.days_of(code)]
            pages += [ROOT / code / "index.html", ROOT / code / "archive" / "index.html"]
            for f in pages:
                page = f.read_text(encoding="utf-8")
                self.assertEqual(undefined_ids(ld_of(page)), set(), str(f))
                self.assertEqual(page.count(RSS_LINK), 1, str(f))
            for f in (ROOT / code / "review").glob("*/index.html"):
                self.assertEqual(undefined_ids(ld_of(f.read_text(encoding="utf-8"))), set(), str(f))

    def test_list_page_collection_itemlist(self):
        for code in langs.LANGS:
            days = publish.days_of(code)
            for f in (ROOT / code / "index.html", ROOT / code / "archive" / "index.html"):
                g = ld_of(f.read_text(encoding="utf-8"))["@graph"]
                cp = next(n for n in g if n["@type"] == "CollectionPage")
                self.assertEqual(cp["url"], f"{langs.SITE}/{code}/", "archive 도 canonical(언어 첫 화면)과 같은 url")
                urls = [i["url"] for i in cp["mainEntity"]["itemListElement"]]
                self.assertEqual(urls, [f"{langs.SITE}/{code}/{d}/" for d in days[:publish.LIST_LD_SIZE]])
                self.assertEqual(cp["mainEntity"]["numberOfItems"], len(urls))
                self.assertEqual([n["@type"] for n in g].count("BreadcrumbList"), 1)

    def test_review_pages(self):
        descs = {}
        for code in langs.LANGS:
            for f in sorted((ROOT / code / "review").glob("*/index.html")):
                page = f.read_text(encoding="utf-8")
                self.assertIn('<meta property="og:type" content="website">', page)
                desc = re.search(r'<meta name="description" content="([^"]*)">', page).group(1)
                self.assertIn(langs.LANGS[code]["name"], desc)
                self.assertNotIn(desc, descs, f"{f} 와 {descs.get(desc)} 의 설명이 같다")
                descs[desc] = f
                g = ld_of(page)["@graph"]
                terms = next(n for n in g if n["@type"] == "DefinedTermSet")
                n = sum(len(x["words"]) for x in weekly.collect(code, f.parent.name))
                self.assertEqual(len(terms["hasDefinedTerm"]), n)
                self.assertFalse([t["name"] for t in terms["hasDefinedTerm"] if "{" in t["name"] or "|" in t["name"]], "후리가나 표기는 걷어낸다")
                self.assertIn("BreadcrumbList", [n["@type"] for n in g])

    def test_archive_canonical_points_to_lang_home(self):
        for code in langs.LANGS:
            page = (ROOT / code / "archive" / "index.html").read_text(encoding="utf-8")
            self.assertIn(f'<link rel="canonical" href="{langs.SITE}/{code}/">', page)
            self.assertIn(f'<meta property="og:url" content="{langs.SITE}/{code}/">', page)
            self.assertIn('<meta property="og:type" content="website">', page)
            self.assertIn('<meta property="og:description"', page)


class FeedsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        for code, day in (("en", "2026-11-12"), ("en", "2026-11-11"), ("ja", "2026-11-12")):
            (self.tmp / code / day).mkdir(parents=True)
            shutil.copy(ROOT / code / day / "index.html", self.tmp / code / day / "index.html")
            (self.tmp / "content" / code).mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / "content" / code / f"{day}.json", self.tmp / "content" / code / f"{day}.json")
        (self.tmp / "index.html").write_text('<meta property="og:image" content="https://x/en/2026-11-07/thumb.png">', encoding="utf-8")
        with mock.patch.object(publish, "ROOT", self.tmp):
            publish.write_sitemap()
        self.read = lambda f: (self.tmp / f).read_text(encoding="utf-8")

    def test_sitemap_root_lastmod_is_landing_build_day_and_no_archive(self):
        sm = self.read("sitemap.xml")
        self.assertIn(f"<loc>{langs.SITE}/</loc><lastmod>2026-11-07</lastmod>", sm)
        self.assertNotIn("/archive/", sm)

    def test_rss(self):
        root = ET.fromstring(self.read("rss.xml"))
        items = root.findall("./channel/item")
        self.assertEqual(len(items), 3)
        self.assertEqual(items[0].findtext("link"), f"{langs.SITE}/en/2026-11-12/")
        self.assertEqual(items[1].findtext("link"), f"{langs.SITE}/ja/2026-11-12/")
        self.assertIn("2026년 11월 12일", items[0].findtext("title"))
        self.assertFalse(items[0].findtext("title").endswith("| 독해한입"), "피드 안에서는 사이트 이름을 반복하지 않는다")
        self.assertEqual(items[0].findtext("pubDate"), "Thu, 12 Nov 2026 07:00:00 +0900")
        robots = self.read("robots.txt")
        self.assertIn(f"Sitemap: {langs.SITE}/rss.xml", robots)
        self.assertIn("User-agent: *\nContent-Signal: search=yes, ai-input=yes, ai-train=yes\n", robots)

    def test_llms_txt(self):
        t = self.read("llms.txt")
        self.assertTrue(t.startswith("# 독해한입\n"))
        self.assertIn("\n- 다른 표기: 한입독해, 독해 한입, Dokhaehanip\n", t)
        self.assertNotIn("검색됨", t)
        self.assertIn("마지막 갱신 2026-11-12", t)
        self.assertIn("AI가 초안을 쓰고 자동 검사", t)
        self.assertIn(f"]({langs.SITE}/en/2026-11-12/)", t)
        self.assertIn(f"]({langs.SITE}/ja/2026-11-12/)", t)


class SiteConstantTest(unittest.TestCase):
    def test_domain_only_in_langs(self):
        hits = [p.name for p in (ROOT / "tools").glob("*.py") if f'"{langs.SITE}"' in p.read_text(encoding="utf-8")]
        self.assertEqual(hits, ["langs.py"])
        tsx = [p for p in (ROOT / "landing" / "src").rglob("*.ts*") if langs.SITE in p.read_text(encoding="utf-8")]
        self.assertEqual([p.name for p in tsx], ["site.ts"])

    def test_landing_names_match_langs(self):
        """다른 이름, sameAs 는 tools/langs.py 와 landing/src/lib/site.ts 가 같은 값이어야 한다."""
        site = (ROOT / "landing" / "src" / "lib" / "site.ts").read_text(encoding="utf-8")
        for name, want in (("ALT_NAMES", langs.ALT_NAMES), ("SAME_AS", langs.SAME_AS)):
            m = re.search(rf"export const {name} = (\[.*?\]);", site)
            self.assertEqual(json.loads(m.group(1)), want, name)
        src = (ROOT / "landing" / "src" / "app" / "layout.tsx").read_text(encoding="utf-8")
        self.assertIn('publisher: { "@id": `${SITE}/#organization` }', src)
        self.assertIn("alternateName: ALT_NAMES,", src)
        self.assertIn("sameAs: SAME_AS,", src)

    def test_landing_built_with_same_as(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        for u in langs.SAME_AS:
            self.assertIn(u, page)


if __name__ == "__main__":
    unittest.main()
