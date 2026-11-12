"""SEO 3차 화면(이슈 #25, 시안 design/seo-ui): 맨 위 요약(S03 B), 날짜 연도(S04), AI 초안 표기(S06 A, 링크 없이),
다른 날 지문 카드(S10 A), 랜딩 FAQ 이름 문항(S13)."""
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
import build_email  # noqa: E402
import check_content  # noqa: E402
import publish  # noqa: E402
import render  # noqa: E402

LD = re.compile(r'<script type="application/ld\+json" id="ld">(.*?)</script>', re.S)
SUMMARY = ("오래 물에 담근 손가락이 쪼글쪼글해지는 까닭을 다룬 B1~B2 영어 지문이에요. 주름은 물을 빨아들여서가 아니라 "
           "신경계가 피부 아래 혈관을 좁혀서 생겨요.")
MADE = '<p class="made">AI 도구로 초안을 쓰고 자동 검사를 거쳐 올린 학습용 글이에요.</p>'
DAYS = ("2026-11-10", "2026-11-11", "2026-11-12")


class Site:
    """임시 사이트 폴더. 실제 content JSON 과 이미지를 복사하고, render 와 publish 의 ROOT 를 그쪽으로 돌린다(실제 파일은 건드리지 않는다)."""

    def __init__(self, case, lang="en", days=DAYS, content=None, photos=True):
        self.tmp = Path(tempfile.mkdtemp())
        case.addCleanup(shutil.rmtree, self.tmp)
        self.lang = lang
        (self.tmp / "content" / lang).mkdir(parents=True)
        for d in days:
            c = json.loads((ROOT / "content" / lang / f"{d}.json").read_text(encoding="utf-8"))
            c.update((content or {}).get(d, {}))
            (self.tmp / "content" / lang / f"{d}.json").write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
            (self.tmp / lang / d).mkdir(parents=True)
            for f in ("thumb.png",) + (("photo.jpg", "thumb-sq.jpg") if photos else ()):
                if (ROOT / lang / d / f).exists():
                    shutil.copy(ROOT / lang / d / f, self.tmp / lang / d / f)
        for target in (render, publish):
            p = mock.patch.object(target, "ROOT", self.tmp)
            p.start()
            case.addCleanup(p.stop)

    def build(self, day):
        """새 지문 발행 순서 그대로: render 다음 patch_page."""
        render.render(self.lang, day)
        publish.patch_page(self.lang, day)
        return self.page(day)

    def page(self, day):
        return (self.tmp / self.lang / day / "index.html").read_text(encoding="utf-8")


def top_card(page):
    return re.search(r'<div class="top">(.*?)\n  </div>\n\n  <section class="card" id="passage">', page, re.S).group(1)


class SummaryTest(unittest.TestCase):
    def test_summary_shown_below_chips_and_in_jsonld(self):
        site = Site(self, days=("2026-11-12",), content={"2026-11-12": {"summary_ko": SUMMARY}})
        top = top_card(site.build("2026-11-12"))
        self.assertEqual(top.count('class="sum-b"'), 1)
        self.assertIn(f'<p class="sum-b">{SUMMARY}</p>', top)
        # 칩 아래, 소개 문단 위(시안 S03 B)
        self.assertLess(top.index('<div class="chips chips-a">'), top.index('class="sum-b"'))
        self.assertLess(top.index('class="sum-b"'), top.index('<p class="intro">'))
        art = json.loads(LD.search(site.page("2026-11-12")).group(1))["@graph"][0]
        self.assertEqual(art["abstract"], SUMMARY)

    def test_no_summary_shows_nothing(self):
        site = Site(self, days=("2026-11-12",))
        page = site.build("2026-11-12")
        self.assertNotIn('class="sum-b"', page)
        art = json.loads(LD.search(page).group(1))["@graph"][0]
        self.assertNotIn("abstract", art)

    def test_intro_names_source_medium(self):
        site = Site(self, days=("2026-11-12",))
        self.assertIn('<p class="intro">매일 아침 새로 올라오는 B1~B2 영어 읽기예요. 출처: Live Science(2013년 1월 9일 기사). 듣고, 해석하고',
                      site.build("2026-11-12"))

    def test_source_phrase_forms(self):
        p = lambda t: publish.source_phrase({"source": {"title": t, "url": "https://x"}})
        self.assertEqual(p("A (Live Science, 2013-01-09)"), " 출처: Live Science(2013년 1월 9일 기사).")
        self.assertEqual(p("10月は休暇 (厚生労働省)"), " 출처: 厚生労働省.")
        self.assertEqual(p("七五三 (意外に知らない「ニッポン入門」, nippon.com)"), " 출처: nippon.com.")
        self.assertEqual(p("제목만 있는 출처"), "")
        self.assertEqual(publish.source_phrase({"source": None}), "")

    def test_no_source_day_intro_unchanged(self):
        site = Site(self, days=("2026-11-08",))
        self.assertIn('<p class="intro">매일 아침 새로 올라오는 B1~B2 영어 읽기예요. 듣고, 해석하고', site.build("2026-11-08"))

    def test_check_content_summary_rules(self):
        self.assertEqual(check_content.check_summary({}), [])
        self.assertEqual(check_content.check_summary({"summary_ko": SUMMARY}), [])
        self.assertTrue(check_content.check_summary({"summary_ko": "짧아요."}))
        self.assertTrue(check_content.check_summary({"summary_ko": "가" * 201}))
        self.assertTrue(check_content.check_summary({"summary_ko": ["목록"]}))
        self.assertTrue(check_content.check_summary({"summary_ko": "   "}))
        self.assertTrue(check_content.check_summary({"summary_ko": "This summary is written only in English and is long enough to pass."}))
        self.assertTrue(check_content.check_summary({"summary_ko": SUMMARY.replace("신경계가", "**신경계**가")}))

    def test_check_content_rejects_middle_dot_in_summary(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        c = json.loads((ROOT / "content" / "en" / "2026-11-12.json").read_text(encoding="utf-8"))
        c["summary_ko"] = SUMMARY.replace("물을 빨아들여서가", "물\u00b7땀을 빨아들여서가")
        (tmp / "content" / "en").mkdir(parents=True)
        f = tmp / "content" / "en" / "2026-11-12.json"
        f.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
        errors, _ = check_content.check(f)
        self.assertTrue(any("summary_ko" in e and "가운뎃점" in e for e in errors), errors)


class DateYearTest(unittest.TestCase):
    def test_new_page_date_has_year_and_time_tag(self):
        site = Site(self, days=("2026-11-12",))
        page = site.build("2026-11-12")
        self.assertIn('<time class="date" datetime="2026-11-12">2026년 11월 12일 목요일 <span class="cat cat-science">과학</span></time>', page)
        self.assertNotIn('<div class="date">', page)
        self.assertIn("  .date { display: block; font-size: 14px;", page)
        # 사진 배너는 날짜 바로 위
        self.assertIn('<div class="hero"><img src="photo.jpg" width="1200" height="630" alt="" fetchpriority="high"></div>\n    <time class="date"', page)

    def test_old_page_div_date_becomes_time_and_is_idempotent(self):
        site = Site(self, days=("2026-11-12",))
        page = site.build("2026-11-12")
        old = (page.replace('<time class="date" datetime="2026-11-12">2026년 11월 12일 목요일', '<div class="date">11월 12일 목요일')
               .replace('<span class="cat cat-science">과학</span></time>', '<span class="cat cat-science">과학</span></div>', 1)
               .replace("  .date { display: block; font-size: 14px;", "  .date { font-size: 14px;"))
        self.assertIn('<div class="date">11월 12일 목요일 <span class="cat cat-science">과학</span></div>', old)
        (site.tmp / "en" / "2026-11-12" / "index.html").write_text(old, encoding="utf-8")
        publish.patch_page("en", "2026-11-12")
        once = site.page("2026-11-12")
        publish.patch_page("en", "2026-11-12")
        self.assertEqual(once, site.page("2026-11-12"))
        self.assertEqual(once, page)

    def test_archive_label_has_year(self):
        self.assertEqual(publish.label("2026-11-12"), "2026년 11월 12일 목요일")
        self.assertIn("11월 12일", publish.entry("en", "2026-11-12")["q"])  # "11월 12일" 로도 찾힌다

    def test_email_date_stays_without_year(self):
        if not (ROOT / "en" / "2026-11-12" / "index.html").exists():
            self.skipTest("렌더 HTML 없음")
        self.assertEqual(build_email.parse("en", "2026-11-12")["date"], "11월 12일 목요일")


class MadeLineTest(unittest.TestCase):
    def test_one_gray_line_right_below_source(self):
        site = Site(self, days=("2026-11-12",))
        page = site.build("2026-11-12")
        self.assertEqual(page.count('class="made"'), 1)
        self.assertRegex(page, r'<p class="src">출처: <a [^>]*>[^<]*</a></p>\n    ' + re.escape(MADE))
        self.assertNotIn("만드는 방식", page)
        self.assertNotIn("/how/", page)
        self.assertEqual(page.count("  .made {"), 1)

    def test_no_source_day_also_has_line(self):
        site = Site(self, days=("2026-11-08",))
        page = site.build("2026-11-08")
        self.assertRegex(page, r'<p class="src">[^<]*</p>\n    ' + re.escape(MADE))

    def test_old_page_without_line_gets_it_once(self):
        site = Site(self, days=("2026-11-12",))
        page = site.build("2026-11-12")
        old = page.replace("    " + MADE + "\n", "").replace("  .made { font-size: 13px; color: var(--muted); margin: 4px 0 0; line-height: 1.6; }\n", "")
        self.assertNotIn("made", old.replace("made by", ""))
        (site.tmp / "en" / "2026-11-12" / "index.html").write_text(old, encoding="utf-8")
        publish.patch_page("en", "2026-11-12")
        once = site.page("2026-11-12")
        publish.patch_page("en", "2026-11-12")
        self.assertEqual(once, site.page("2026-11-12"))
        self.assertEqual(once.count('class="made"'), 1)
        self.assertEqual(once.count("  .made {"), 1)


def pn(page):
    m = re.findall(r'<nav class="card pn" aria-label="이전, 다음 지문">.*?</nav>', page, re.S)
    assert len(m) == 1, f"다른 날 지문 카드 수 {len(m)}"
    return m[0]


class PrevNextTest(unittest.TestCase):
    def built(self, **kw):
        site = Site(self, **kw)
        for d in DAYS:
            render.render("en", d)
        for d in DAYS:
            publish.patch_page("en", d)
        return site

    def test_middle_day_links_both_sides(self):
        site = self.built()
        nav = pn(site.page("2026-11-11"))
        self.assertIn('<a class="pn-i" href="../2026-11-10/"><img src="../2026-11-10/thumb-sq.jpg" width="76" height="76" alt="" loading="lazy" decoding="async">', nav)
        self.assertIn('<span class="pn-d">이전 지문 <b>2026년 11월 10일 화요일</b></span>', nav)
        self.assertIn('<span class="pn-d">다음 지문 <b>2026년 11월 12일 목요일</b></span><span class="pn-n">물속에서 쪼글쪼글해지는 손가락</span>'
                      '<span class="cat cat-science">과학</span>', nav)
        self.assertIn('<a class="pn-all" href="../archive/">영어 지난 지문 전체 보기', nav)
        self.assertNotIn("pn-wait", nav)
        # 이웃 사진은 모두 늦게 읽는다(첫 화면 사진 성능에 끼어들지 않게)
        imgs = re.findall(r"<img [^>]*>", nav)
        self.assertEqual(len(imgs), 2)
        self.assertTrue(all('loading="lazy"' in i for i in imgs))

    def test_latest_day_next_is_wait_note(self):
        site = self.built()
        nav = pn(site.page("2026-11-12"))
        self.assertIn('이전 지문 <b>2026년 11월 11일 수요일</b></span><span class="pn-n">빈 땅에 새로 생긴 동네 공원</span>', nav)
        self.assertIn('<div class="pn-i pn-wait">', nav)
        self.assertIn("내일 아침에 새 영어 지문이 올라와요", nav)
        self.assertEqual(nav.count("<a class=\"pn-i\""), 1)

    def test_first_day_has_no_prev(self):
        site = self.built()
        nav = pn(site.page("2026-11-10"))
        self.assertNotIn("이전 지문", nav)
        self.assertIn("다음 지문 <b>2026년 11월 11일 수요일</b>", nav)

    def test_card_sits_right_above_subscribe_card(self):
        site = self.built()
        page = site.page("2026-11-11")
        self.assertRegex(page, r'</nav>\n  <section class="card sub" id="subscribe"')
        self.assertEqual(page.count("/* pn-css */"), 1)

    def test_day_without_photo_uses_illustration(self):
        site = self.built(photos=False)
        nav = pn(site.page("2026-11-11"))
        self.assertIn('<img src="../2026-11-10/thumb.png" width="76" height="76" alt="" loading="lazy" decoding="async">', nav)

    def test_publishing_new_day_updates_previous_page(self):
        site = Site(self)
        for d in DAYS[:2]:
            render.render("en", d)
            publish.patch_page("en", d)
        self.assertIn("내일 아침에 새 영어 지문이 올라와요", pn(site.page("2026-11-11")))
        render.render("en", "2026-11-12")
        with mock.patch.object(publish.thumb, "build"), mock.patch.object(publish, "rebuild_lists"), \
                mock.patch.object(publish, "rebuild_root"):
            publish.publish_day("en", "2026-11-12")
        nav = pn(site.page("2026-11-11"))
        self.assertNotIn("pn-wait", nav)
        self.assertIn('<a class="pn-i" href="../2026-11-12/">', nav)
        self.assertIn("내일 아침에 새 영어 지문이 올라와요", pn(site.page("2026-11-12")))

    def test_patch_page_idempotent_with_card(self):
        site = self.built()
        once = site.page("2026-11-11")
        publish.patch_page("en", "2026-11-11")
        self.assertEqual(once, site.page("2026-11-11"))


class FaqTest(unittest.TestCase):
    Q = "독해한입과 한입독해는 같은 서비스인가요?"
    A = ("네, 같은 서비스예요. 정식 이름은 독해한입이고, 외국어 독해를 하루 한입 크기로 나눠 읽는다는 뜻이에요. "
         "한입독해, 독해 한입, 영문 Dokhaehanip으로 부르셔도 모두 dokhaehanip.com 의 같은 사이트예요.")

    def test_faq_source_has_question(self):
        src = (ROOT / "landing" / "src" / "lib" / "faq.ts").read_text(encoding="utf-8")
        self.assertIn(f'q: "{self.Q}"', src)
        self.assertIn(f'a: "{self.A}"', src)
        self.assertNotIn("\u00b7", src)

    def test_built_landing_shows_question_and_faqpage(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        ld = re.search(r'<script type="application/ld\+json">(.*?)</script>', page, re.S)
        self.assertIsNotNone(ld)
        graph = json.loads(ld.group(1))["@graph"]
        faq = next(n for n in graph if n.get("@type") == "FAQPage")
        self.assertEqual(len(faq["mainEntity"]), 7)
        self.assertEqual(faq["mainEntity"][-1]["name"], self.Q)
        self.assertEqual(faq["mainEntity"][-1]["acceptedAnswer"]["text"], self.A)
        self.assertIn(self.Q, page)
        self.assertRegex(page, r"7(<!-- -->)?개 질문")


if __name__ == "__main__":
    unittest.main()
