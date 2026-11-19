"""로그인(카카오, Google)과 단어 기록 저장(시안 design/kakao-login). 페이지 생성, 잠금 마크업, 배포 허용 목록을 본다.
auth.js 의 합치기와 연속일 계산은 tests/auth.test.mjs(node --test)가 본다."""
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import drill  # noqa: E402
import prepare_site  # noqa: E402
import publish  # noqa: E402


class AccountPagesTest(unittest.TestCase):
    def test_generated_idempotent_and_committed(self):
        before = {f: (ROOT / f / "index.html").read_text(encoding="utf-8") for f in ("join", "join/callback", "me")}
        publish.rebuild_account_pages()
        for f, s in before.items():
            self.assertEqual((ROOT / f / "index.html").read_text(encoding="utf-8"), s, f)

    def test_login_page_has_no_consent_and_agree_page_does(self):
        # 로그인 화면(K32)은 버튼만, 처음인 계정은 콜백이 동의 화면(K33)으로 보낸다
        s = (ROOT / "login/index.html").read_text(encoding="utf-8")
        self.assertNotIn('id="agreeAge"', s)
        for needle in ('id="kakao"', 'id="google"', 'id="toJoin"', 'id="inApp"', "/assets/join.js?v="):
            self.assertIn(needle, s)
        a = (ROOT / "join/agree/index.html").read_text(encoding="utf-8")
        for needle in ('id="agreeAge"', 'id="agreePriv"', 'id="agreeGo"', 'id="agreeNo"', "/assets/join-agree.js?v="):
            self.assertIn(needle, a)
        cb = (ROOT / "assets/join-callback.js").read_text(encoding="utf-8")
        self.assertIn('saved.agreed === false && first', cb)
        self.assertIn("agreed: !login", (ROOT / "assets/join.js").read_text(encoding="utf-8"))

    def test_join_has_consents_and_two_providers(self):
        s = (ROOT / "join/index.html").read_text(encoding="utf-8")
        for needle in ('id="agreeAge"', 'id="agreePriv"', 'id="kakao" aria-disabled="true"', 'id="google" aria-disabled="true"', 'id="needMsg"', 'id="inApp"',
                       'href="/privacy/#account"', "/assets/auth.js?v=", "/assets/join.js?v=", 'name="robots" content="noindex"'):
            self.assertIn(needle, s)
        self.assertLess(s.index("/assets/auth.js"), s.index("/assets/join.js"))

    def test_callback_loads_no_third_party_scripts(self):
        # 콜백 주소에는 로그인 코드가 실려 오므로 광고, 통계, 외부 글꼴을 부르지 않는다
        s = (ROOT / "join/callback/index.html").read_text(encoding="utf-8")
        for bad in ("googletagmanager", "adsbygoogle", "clarity.ms", "cdnjs.cloudflare.com"):
            self.assertNotIn(bad, s)
        self.assertIn("/assets/join-callback.js?v=", s)

    def test_scripts_exist(self):
        for f in ("auth.js", "join.js", "join-callback.js", "me.js"):
            self.assertTrue((ROOT / "assets" / f).is_file(), f)
        auth = (ROOT / "assets/auth.js").read_text(encoding="utf-8")
        # 공개 키만 둔다. secret 키 모양은 저장소 어디에도 없어야 한다
        self.assertNotRegex(auth, r"sb_secret_[A-Za-z0-9]")
        self.assertIn("integrity", auth)
        events = re.search(r"var EVENTS = \[(.*?)\];", auth).group(1)
        sql = (ROOT / "supabase/migrations/0001_init.sql").read_text(encoding="utf-8")
        allowed = re.search(r"select n in \((.*?)\);", sql).group(1)
        self.assertEqual(re.findall(r"'(\w+)'", allowed), re.findall(r'"(\w+)"', events))

    def test_privacy_mentions_login(self):
        s = (ROOT / "privacy/index.html").read_text(encoding="utf-8")
        self.assertIn('id="account"', s)
        self.assertIn("Supabase", s)
        self.assertNotIn("회원 가입이 없고", s)

    def test_deployed_but_worker_and_schema_are_not(self):
        with tempfile.TemporaryDirectory() as d:
            out = prepare_site.prepare(out=Path(d) / "s")
            self.assertTrue((out / "join/index.html").is_file())
            self.assertTrue((out / "join/callback/index.html").is_file())
            self.assertTrue((out / "me/index.html").is_file())
            self.assertFalse((out / "worker").exists())
            self.assertFalse((out / "supabase").exists())


class DrillGateTest(unittest.TestCase):
    def test_card_has_gate_and_locks(self):
        h = drill.card_html("en", "2026-11-17", [{"w": "a"}, {"w": "b"}], 4)
        self.assertIn('id="dr-gate" hidden', h)
        self.assertEqual(h.count('class="dr-lk"'), 3)
        self.assertIn('data-login="kakao"', h)
        self.assertIn('data-login="google"', h)
        self.assertIn("카카오로 시작하고 2문제 풀기", h)

    def test_pages_load_auth_before_drill(self):
        p = ROOT / "en/2026-11-17/index.html"
        s = p.read_text(encoding="utf-8")
        self.assertIn(f'id="drill-js" data-v="{drill.VERSION}"', s)
        self.assertEqual(s.count('id="auth-js"'), 1)
        self.assertLess(s.index('id="auth-js"'), s.index('id="drill-js"'))
        # 다시 넣어도 하나만
        self.assertEqual(drill.apply(s.replace(f'data-v="{drill.VERSION}"', 'data-v="0"'), "en", "2026-11-17").count('id="auth-js"'), 1)

    def test_drill_js_gates_only_when_ready(self):
        js = (ROOT / "assets/drill.js").read_text(encoding="utf-8")
        self.assertIn("function locked() { return AUTH.ready && !AUTH.hasSession(); }", js)
        self.assertIn("rec.t = now", js)
        self.assertIn("db.days", js)


if __name__ == "__main__":
    unittest.main()


class HeaderMeTest(unittest.TestCase):
    """위 메뉴 로그인, 마이페이지 버튼(시안 design/kakao-login K15)."""

    def test_header_has_me_button(self):
        import gnb
        h = gnb.header_html("en")
        self.assertIn('id="gnb-me"', h)
        self.assertLess(h.index("gnb-mail"), h.index('id="gnb-me"'))
        self.assertIn("dkh-auth", gnb.SCRIPT)
        self.assertIn("'/me/'", gnb.SCRIPT)

    def test_refresh_idempotent_and_all_pages_have_it(self):
        import gnb
        for f in ("en/2026-11-18/index.html", "en/archive/index.html", "privacy/index.html", "me/index.html", "join/index.html"):
            s = (ROOT / f).read_text(encoding="utf-8")
            self.assertEqual(s.count('id="gnb-me"'), 1, f)
            self.assertEqual(gnb.refresh(s), s, f)

    def test_landing_has_me_button(self):
        self.assertIn('id="gnb-me"', (ROOT / "index.html").read_text(encoding="utf-8"))
        self.assertIn("function MeButton", (ROOT / "landing/src/components/Nav.tsx").read_text(encoding="utf-8"))

    def test_landing_me_markup_matches_gnb(self):
        # 첫 화면(Nav.tsx 빌드 결과)과 지문 페이지(gnb.ME_HTML)의 버튼이 같은 마크업이어야 같은 CSS 로 같게 보인다.
        # 주소와 읽기 이름표는 페이지마다 달라 뺀다. 저장값을 읽는 규칙이 같은지는 tests/contract.test.mjs 가 본다.
        import gnb
        from html.parser import HTMLParser

        def skeleton(h):
            out = []

            class P(HTMLParser):
                def handle_starttag(self, tag, attrs):
                    out.append(("<", tag, tuple(sorted((k, v or "") for k, v in attrs if k not in ("href", "aria-label")))))

                def handle_startendtag(self, tag, attrs):
                    self.handle_starttag(tag, attrs)
                    out.append((">", tag))

                def handle_endtag(self, tag):
                    out.append((">", tag))

                def handle_data(self, d):
                    if d.strip():
                        out.append(("t", d.strip()))

            P().feed(h)
            return out

        s = (ROOT / "index.html").read_text(encoding="utf-8")
        i = s.index('id="gnb-me"')
        landing = s[s.rindex("<a", 0, i):s.index("</a>", i) + 4]
        self.assertEqual(skeleton(landing), skeleton(gnb.ME_HTML))

    def test_date_pages_keep_patch_anchors(self):
        # drill, vote, publish 는 지난 지문 페이지에 CSS 와 카드를 '  .gnb {', </header>, </main> 앞뒤로 끼워 넣는다.
        # drill.apply 는 이 줄이 없으면 조용히 건너뛰므로(아카이브 같은 다른 페이지 때문), 날짜 페이지에서 사라지면 여기서 알린다.
        pages = [p for p in ROOT.glob("*/*/index.html") if re.fullmatch(r"[a-z]{2}/\d{4}-\d{2}-\d{2}", p.parent.relative_to(ROOT).as_posix())]
        self.assertGreater(len(pages), 100)
        for p in pages:
            s = p.read_text(encoding="utf-8")
            name = p.relative_to(ROOT).as_posix()
            self.assertEqual(s.count("  .gnb {"), 1, name)
            self.assertIn("</header>\n", s, name)
            self.assertIn("</main>", s, name)
            self.assertIn('id="drill-js"', s, name)

    def test_mypage_name(self):
        self.assertIn("<title>마이페이지 |", (ROOT / "me/index.html").read_text(encoding="utf-8"))


class MailOptInTest(unittest.TestCase):
    """아침 지문 메일 수신(선택, 시안 K16~K18)."""

    def test_join_has_optional_mail_checkbox(self):
        s = (ROOT / "join/index.html").read_text(encoding="utf-8")
        self.assertIn('id="agreeMail"', s)
        self.assertNotIn('id="agreeMail" checked', s)  # 기본은 꺼짐

    def test_email_page_and_me_mail_card(self):
        e = (ROOT / "join/email/index.html").read_text(encoding="utf-8")
        self.assertIn('id="mailForm"', e)
        self.assertIn("/assets/join-email.js?v=", e)
        m = (ROOT / "me/index.html").read_text(encoding="utf-8")
        for needle in ('id="mailTg"', 'role="switch"', 'id="mailPend"', 'id="mailEdit"'):
            self.assertIn(needle, m)

    def test_client_cannot_set_verified(self):
        sql = (ROOT / "supabase/migrations/0002_mail.sql").read_text(encoding="utf-8")
        self.assertIn("grant update (email, mail_opt_in) on public.profiles to authenticated;", sql)
        self.assertNotIn("mail_verified) on public.profiles to authenticated", sql)

    def test_privacy_mentions_mail(self):
        s = (ROOT / "privacy/index.html").read_text(encoding="utf-8")
        self.assertIn('id="mail"', s)
        self.assertIn("수신에 동의한 시각", s)


class NoAnonEventsTest(unittest.TestCase):
    def test_anon_events_closed(self):
        auth = (ROOT / "assets/auth.js").read_text(encoding="utf-8")
        self.assertNotIn("insertAnon", auth)
        sql = (ROOT / "supabase/migrations/0003_no_anon_events.sql").read_text(encoding="utf-8")
        self.assertIn("revoke insert on public.events from anon;", sql)
        self.assertIn("drop policy if exists events_insert_anon", sql)
