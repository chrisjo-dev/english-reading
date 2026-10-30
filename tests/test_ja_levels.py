"""일본어 수준 나누기(중급 N3 본문 + 기초 N4~N5 levels.a) 테스트.

실행: python3 -m pytest -q tests/test_ja_levels.py
"""
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
import build_email  # noqa: E402
import check_content as cc  # noqa: E402
import langs  # noqa: E402
import publish  # noqa: E402
import render as rnd  # noqa: E402
import send_email  # noqa: E402

# 중급(N3) 본문 6문장과 기초(N4~N5) 6문장. 후리가나 {漢字|かな} 와 **강조** 를 섞는다.
MAIN = [
    "{駅前|えきまえ}の**{本屋|ほんや}**は、{来月|らいげつ}から{夜|よる}10{時|じ}まで{開|あ}いていることになりました。",
    "{仕事|しごと}の{帰|かえ}りに{寄|よ}る{人|ひと}が{増|ふ}えたので、{店|みせ}の{人|ひと}たちが{話|はな}し{合|あ}って{決|き}めたそうです。",
    "{店|みせ}の{奥|おく}には、{静|しず}かに{本|ほん}を{読|よ}めるように、{小|ちい}さな{机|つくえ}が{置|お}かれています。",
    "{本|ほん}を{買|か}わなくても、コーヒーを{一杯|いっぱい}{頼|たの}めば、そこで{一時間|いちじかん}ほど{休|やす}むことができます。",
    "{店長|てんちょう}によると、{若|わか}い{人|ひと}だけでなく、{近|ちか}くに{住|す}むお{年寄|としよ}りもよく{来|く}るそうです。",
    "{町|まち}の{人|ひと}たちが{集|あつ}まれる{場所|ばしょ}として、これからも{大切|たいせつ}にしていきたいと{話|はな}していました。",
]
BASIC = [
    "{駅|えき}の{前|まえ}の**{本屋|ほんや}**は、{来月|らいげつ}から{夜|よる}10{時|じ}まで{開|あ}きます。",
    "{仕事|しごと}の{後|あと}で{来|く}る{人|ひと}が{多|おお}いです。",
    "{店|みせ}の{奥|おく}に{小|ちい}さい{机|つくえ}があります。",
    "コーヒーを{飲|の}んで、{少|すこ}し{休|やす}むことができます。",
    "お{年寄|としよ}りもよく{来|き}ます。",
    "みんなが{集|あつ}まる{場所|ばしょ}です。",
]


def make_ja(day="2026-10-29", with_levels=True, sentences=None):
    sents = sentences or MAIN
    c = {
        "date": day, "category": "culture", "topic": "동네 서점", "title_ko": "밤늦게까지 여는 동네 서점",
        "headline": "{夜|よる}も{開|あ}いている{本屋|ほんや}",
        "chips": [f"{len(sents)}문장", "N3 위주", "N3 문법 1문장", "약 4분"],
        "sentences": [{"en": s, "b2": i == 0} for i, s in enumerate(sents)],
        "words": [["{本屋|ほんや}", "서점"]] * 5,
        "points": [{"title": "ことになる", "body": "`{開|あ}いていることになりました`는 정해졌다는 뜻이에요."}],
        "answers": ["해석입니다."] * len(sents),
        "advanced": [{"word": "{営業|えいぎょう}", "meaning": "영업", "confuse": None,
                      "example": "**{営業|えいぎょう}**します。", "example_ko": "영업합니다."}] * 6,
        "source": None, "example": True,
    }
    if with_levels:
        c["levels"] = {"a": {"sentences": [{"en": s} for s in BASIC[:len(sents)]],
                             "answers": ["기초 해석입니다."] * len(sents)}}
    return c


def write(root, kind, name, c):
    d = root / kind / "ja"
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"{name}.json"
    f.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
    return f


class LangsFlagTest(unittest.TestCase):
    def test_ja_flags(self):
        L = langs.LANGS["ja"]
        self.assertTrue(L["levels"])
        self.assertEqual(L["level"], "JLPT N3")
        self.assertEqual(L["hard_badge"], "N3")
        self.assertEqual(L["level_a_label"], "기초 N4~N5")
        self.assertEqual(L["default_level"], "a")
        self.assertFalse(L["chunks"])

    def test_other_langs_default_level_b(self):
        self.assertEqual(send_email.default_level("en"), "b")
        self.assertEqual(send_email.default_level("de"), "b")
        self.assertEqual(send_email.default_level(None), "b")
        self.assertEqual(send_email.default_level("ja"), "a")


class CheckContentJaTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def level_errs(self, f):
        return [e for e in cc.check(f)[0] if "levels" in e]

    def test_required_from_cutoff(self):
        f = write(self.root, "content", "2026-10-29", make_ja(with_levels=False))
        self.assertTrue(self.level_errs(f))

    def test_not_required_before_cutoff(self):
        f = write(self.root, "content", "2026-10-28", make_ja("2026-10-28", with_levels=False))
        self.assertEqual(self.level_errs(f), [])

    def test_pool_always_required(self):
        f = write(self.root, "pool", "011-test", make_ja(with_levels=False))
        self.assertTrue(self.level_errs(f))

    def test_valid_levels_without_chunks_ok(self):
        """일본어는 chunks 를 쓰지 않으므로 levels.a 에 chunks 가 없어도 오류가 아니다."""
        f = write(self.root, "content", "2026-10-29", make_ja())
        errs, warns = cc.check(f)
        self.assertEqual(errs, [])
        self.assertEqual(warns, [])

    def test_count_mismatch_error(self):
        c = make_ja()
        c["levels"]["a"]["sentences"].pop()
        f = write(self.root, "content", "2026-10-29", c)
        self.assertTrue(any("개수" in e for e in self.level_errs(f)))

    def test_short_main_warns(self):
        """N4~N5 길이(20자 안팎)의 본문을 그대로 쓰면 경고한다."""
        f = write(self.root, "content", "2026-10-29", make_ja(sentences=BASIC))
        warns = cc.check(f)[1]
        self.assertTrue(any("N3" in w for w in warns), warns)

    def test_short_main_no_warning_before_cutoff(self):
        f = write(self.root, "content", "2026-10-28", make_ja("2026-10-28", sentences=BASIC, with_levels=False))
        self.assertFalse(any("N3" in w for w in cc.check(f)[1]))


class RenderJaLevelsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        write(self.tmp, "content", "2026-10-29", make_ja())
        orig = rnd.ROOT
        try:
            rnd.ROOT = self.tmp
            out, _, _ = rnd.render("ja", "2026-10-29")
            self.page = out.read_text(encoding="utf-8")
        finally:
            rnd.ROOT = orig

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_basic_sentences_have_ruby(self):
        en_a = re.findall(r'<div class="en-a">(.*?)</div>', self.page)
        self.assertEqual(len(en_a), 6)
        self.assertIn("<ruby>駅<rp>(</rp><rt>えき</rt><rp>)</rp></ruby>", en_a[0])
        self.assertIn("<b><ruby>本屋", en_a[0])
        for s in en_a:
            self.assertNotIn("{", s)
            self.assertNotIn("|", s)

    def test_chips_and_badge(self):
        self.assertIn('<span class="chip easy">기초 N4~N5</span>', self.page)
        self.assertIn('<span class="badge">N3</span>', self.page)
        # 기초 읽기 시간: 글자 수 기준(후리가나 읽기 뺀 95자 ÷ 60 → 약 2분)
        self.assertRegex(self.page, r'(?s)chips-a">.*?<span class="chip">약 2분</span>')

    def test_level_switch_and_font(self):
        self.assertIn('id="to-level-a"', self.page)
        self.assertIn(".en, .en-a, .adv .ex", self.page)
        self.assertNotIn("chunks-a", re.sub(r"<style>.*?</style>|<script>.*?</script>", "", self.page, flags=re.S))


class SendEmailJaTest(unittest.TestCase):
    def sub(self, meta, sub_type="regular", sid="s1"):
        return {"id": sid, "type": sub_type, "metadata": meta}

    def test_fill_missing_level_ja_gets_a(self):
        subs = [self.sub({"lang": "ja"}, sid="j1"), self.sub({"lang": "en"}, sid="e1"),
                self.sub({"lang": "de"}, sid="d1"), self.sub({"lang": "ja", "level": "b"}, sid="j2")]
        with patch.object(send_email, "subscribers", return_value=iter(subs)), \
             patch.object(send_email, "call") as call:
            send_email.fill_missing_level()
        self.assertEqual(call.call_args_list, [
            unittest.mock.call("PATCH", "/subscribers/j1", {"metadata": {"lang": "ja", "level": "a"}}),
            unittest.mock.call("PATCH", "/subscribers/e1", {"metadata": {"lang": "en", "level": "b"}}),
            unittest.mock.call("PATCH", "/subscribers/d1", {"metadata": {"lang": "de", "level": "b"}}),
        ])

    def test_audience_ja(self):
        b = send_email.audience("ja", "b")["filters"]
        a = send_email.audience("ja", "a")["filters"]
        lang_rule = {"field": "subscriber.metadata.lang", "operator": "equals", "value": "ja"}
        self.assertEqual(b, [lang_rule, {"field": "subscriber.metadata.level", "operator": "not_equals", "value": "a"}])
        self.assertEqual(a, [lang_rule, {"field": "subscriber.metadata.level", "operator": "equals", "value": "a"}])

    def test_wants_ja_matches_audience(self):
        empty, lv_a, lv_b = self.sub({"lang": "ja"}), self.sub({"lang": "ja", "level": "a"}), self.sub({"lang": "ja", "level": "b"})
        # 수준이 빈 일본어 구독자는 기본값 a 로 본다(fill_missing_level 과 같은 기준)
        self.assertTrue(send_email.wants(empty, "ja", "a"))
        self.assertFalse(send_email.wants(empty, "ja", "b"))
        self.assertTrue(send_email.wants(lv_a, "ja", "a"))
        self.assertFalse(send_email.wants(lv_a, "ja", "b"))
        self.assertTrue(send_email.wants(lv_b, "ja", "b"))
        self.assertFalse(send_email.wants(lv_b, "ja", "a"))
        self.assertFalse(send_email.wants(lv_a, "en", "a"))

    def test_en_empty_level_still_b(self):
        self.assertTrue(send_email.wants(self.sub({}), "en", "b"))


class BuildEmailJaTest(unittest.TestCase):
    def test_marks_email_ruby(self):
        out = build_email._marks_email("**{本屋|ほんや}**は{夜|よる}も<開>")
        self.assertEqual(out, "<b><ruby>本屋<rp>(</rp><rt>ほんや</rt><rp>)</rp></ruby></b>は"
                              "<ruby>夜<rp>(</rp><rt>よる</rt><rp>)</rp></ruby>も&lt;開&gt;")

    def test_level_a_email(self):
        day = "test-ja-levels-a"
        path = REPO / "content" / "ja" / f"{day}.json"
        path.write_text(json.dumps(make_ja(), ensure_ascii=False), encoding="utf-8")
        parsed = {"date": "10월 29일 목요일", "topic": "동네 서점", "headline": "",
                  "chips": ["6문장", "N3 위주", "N3 문법 1문장", "약 4분"],
                  "chips_a": ["6문장", "기초 N4~N5", "약 1분"],
                  "sentences": ["main"], "words": [("w", "m")], "source": None}
        try:
            with patch.object(build_email, "parse", return_value=parsed):
                mail = build_email.build("ja", day, "a")
                mail_b = build_email.build("ja", day, "b")
        finally:
            path.unlink(missing_ok=True)
        self.assertIn("?level=a", mail["body"])
        self.assertIn("<ruby>駅<rp>(</rp><rt>えき</rt>", mail["body"])
        self.assertNotIn("{", re.sub(r"\{\{ unsubscribe_url \}\}", "", mail["body"]).split("<table", 1)[1].split("STEP 2")[0])
        self.assertIn("기초 N4~N5", mail["body"])
        self.assertNotIn("N3 위주", mail["body"])
        self.assertIn("매일 아침 기초 N4~N5 일본어 지문을", mail["body"])
        self.assertIn("매일 아침 JLPT N3 일본어 지문을", mail_b["body"])


class PatchOldJaPageTest(unittest.TestCase):
    """수준 선택이 없던 지난 일본어 페이지(data-v="2")의 구독 칸이 수준 선택 카드로 바뀌고, 본문은 그대로다."""

    def test_old_page_card_replaced(self):
        src = REPO / "ja" / "2026-10-20" / "index.html"
        if not src.exists():
            self.skipTest("ja/2026-10-20 페이지 없음")
        tmp = Path(tempfile.mkdtemp())
        try:
            (tmp / "ja" / "2026-10-20").mkdir(parents=True)
            dst = tmp / "ja" / "2026-10-20" / "index.html"
            before = src.read_text(encoding="utf-8")
            dst.write_text(before, encoding="utf-8")
            orig = publish.ROOT
            try:
                publish.ROOT = tmp
                publish.patch_page("ja", "2026-10-20")
                after = dst.read_text(encoding="utf-8")
                publish.patch_page("ja", "2026-10-20")
                again = dst.read_text(encoding="utf-8")
            finally:
                publish.ROOT = orig
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertEqual(after, again, "두 번 실행해도 같아야 합니다")
        self.assertEqual(len(re.findall(r'<input[^>]+name="metadata__level"', after)), 2)
        self.assertEqual(after.count('class="card sub"'), 1)
        def strip(p):
            # 구독 카드와 rebrand patch 가 바꾸는 요소(제목/OG/파비콘/GNB 브랜드)를 제외하고 비교한다.
            p = re.sub(r'<section class="card sub".*?</section>', "", p, flags=re.S)
            p = re.sub(r'<title>[^<]*</title>', "<title/>", p)
            p = re.sub(r'<meta property="og:(?:title|site_name)" content="[^"]*"', '<meta property="og:brand" content=""', p)
            p = re.sub(r'<link rel="icon"[^>]*/?>', "", p)
            p = re.sub(r'(<a class="brand" href="/">).*?(</a>)', r'\1\2', p, flags=re.S)
            p = re.sub(r'/\* gnb-narrow \*/[^\n]*\n?', '', p)
            # GNB 브랜드 img CSS 규칙 주입 (inline style → CSS) 도 rebrand patch 범위
            p = re.sub(r'  \.gnb \.brand img \{ vertical-align: middle; \}\n', '', p)
            return p
        self.assertEqual(strip(before), strip(after), "구독 칸 밖 콘텐츠는 바뀌지 않아야 합니다")


if __name__ == "__main__":
    unittest.main()
