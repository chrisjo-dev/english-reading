"""가입자 메일 설정을 Buttondown 구독자로 맞추는 결정(tools/sync_members.plan). 계획: supabase/PLAN-join-subscribe.md"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import sync_members as S  # noqa: E402


def prof(uid, email, on=True, verified=False, lang="en", level="b", wait=False, opt_at="2026-11-18T01:00:00Z", synced=None):
    return {"user_id": uid, "email": email, "mail_opt_in": on, "mail_verified": verified, "mail_lang": lang,
            "mail_level": level, "mail_wait": wait, "mail_opt_at": opt_at, "mail_synced_at": synced}


def sub(email, type_="regular", **meta):
    return {"email_address": email, "type": type_, "metadata": meta}


class PlanTest(unittest.TestCase):
    def test_google_goes_in_without_confirmation_kakao_with(self):
        ops, fix, taken = S.plan([prof("g", "g@x.com", verified=True, lang="ja", level="a"), prof("k", "k@x.com")], [])
        self.assertEqual(ops[0], ("create", "g@x.com", {"email_address": "g@x.com", "type": "regular",
                                                        "metadata": {"lang": "ja", "level": "a", "account": "1"}}, False))
        self.assertNotIn("type", ops[1][2])  # 확인 메일(unactivated)
        self.assertEqual(taken, 2)
        self.assertEqual(fix["g"], {"mail_wait": False, "mail_synced_at": True})

    def test_google_user_who_typed_another_address_still_confirms(self):
        # 마이페이지에서 주소를 바꾸면 mail_verified=false(0002 트리거): 로그인 방식이 아니라 확인 여부로 정한다
        ops, _, _ = S.plan([prof("g", "other@x.com", verified=False)], [])
        self.assertNotIn("type", ops[0][2])

    def test_cap_puts_the_rest_on_the_waitlist_in_order(self):
        legacy = [sub(f"old{i}@x.com") for i in range(99)]  # 기존 구독자도 자리를 쓴다
        ops, fix, taken = S.plan([prof("a", "a@x.com"), prof("b", "b@x.com")], legacy)
        self.assertEqual([o[1] for o in ops], ["a@x.com"])
        self.assertEqual(fix["b"], {"mail_wait": True})
        self.assertEqual(taken, 100)

    def test_waitlisted_gets_in_when_a_seat_opens(self):
        legacy = [sub(f"old{i}@x.com") for i in range(98)] + [sub("gone@x.com", "unsubscribed")]
        ops, fix, _ = S.plan([prof("b", "b@x.com", wait=True)], legacy)
        self.assertEqual(ops[0][0], "create")
        self.assertEqual(fix["b"]["mail_wait"], False)

    def test_existing_subscriber_gets_metadata_only_when_changed(self):
        same = sub("a@x.com", lang="en", level="b", account="1")
        ops, fix, _ = S.plan([prof("a", "a@x.com", verified=True)], [same])
        self.assertEqual(ops, [])
        self.assertEqual(fix, {})
        ops, _, _ = S.plan([prof("a", "a@x.com", verified=True, lang="de")], [same])
        self.assertEqual(ops, [("meta", "a@x.com", {"lang": "de", "level": "b", "account": "1"})])

    def test_legacy_subscriber_who_signs_up_is_linked_not_duplicated(self):
        ops, _, taken = S.plan([prof("a", "a@x.com")], [sub("A@x.com", lang="en")])
        self.assertEqual(ops, [("meta", "a@x.com", {"lang": "en", "level": "b", "account": "1"})])
        self.assertEqual(taken, 1)

    def test_confirmed_kakao_address_becomes_verified(self):
        _, fix, _ = S.plan([prof("k", "k@x.com")], [sub("k@x.com", lang="en", level="b", account="1")])
        self.assertEqual(fix["k"], {"mail_verified": True})

    def test_unsubscribe_from_mail_is_respected(self):
        ops, fix, _ = S.plan([prof("a", "a@x.com", opt_at="2026-11-01T00:00:00Z", synced="2026-11-02T00:00:00Z")],
                             [sub("a@x.com", "unsubscribed", account="1")])
        self.assertEqual(ops, [])
        self.assertEqual(fix["a"], {"mail_opt_in": False, "mail_wait": False, "mail_synced_at": True})

    def test_turning_back_on_after_unsubscribe_resubscribes(self):
        ops, _, _ = S.plan([prof("a", "a@x.com", opt_at="2026-11-03T00:00:00Z", synced="2026-11-02T00:00:00Z")],
                           [sub("a@x.com", "unsubscribed", account="1")])
        self.assertEqual(ops[0][0], "create")
        self.assertEqual(ops[0][2]["type"], "unactivated")  # 확인 전 주소는 확인 메일부터
        self.assertTrue(ops[0][3])  # collision add

    def test_complaints_and_bounces_are_never_resubscribed(self):
        for t in ("complained", "undeliverable", "blocked"):
            ops, fix, _ = S.plan([prof("a", "a@x.com", synced=None)], [sub("a@x.com", t)])
            self.assertEqual(ops, [])
            self.assertFalse(fix["a"]["mail_opt_in"])

    def test_turning_off_unsubscribes_only_account_subscribers(self):
        ops, _, taken = S.plan([prof("a", "a@x.com", on=False), prof("b", "b@x.com", on=False)],
                               [sub("a@x.com", account="1"), sub("b@x.com")])
        self.assertEqual(ops, [("unsub", "a@x.com")])  # 기존 구독자(b)는 그대로 둔다
        self.assertEqual(taken, 1)
        ops, _, _ = S.plan([prof("a", "a@x.com", on=False)], [sub("a@x.com", "unactivated", account="1")])
        self.assertEqual(ops, [("delete", "a@x.com")])  # 확인 전은 해지가 안 돼 지운다

    def test_shared_address_stays_while_any_account_wants_it(self):
        ops, _, _ = S.plan([prof("on", "s@x.com"), prof("off", "s@x.com", on=False)], [sub("s@x.com", account="1")])
        self.assertEqual([o for o in ops if o[0] in ("unsub", "delete")], [])
        ops, _, _ = S.plan([prof("on", "s@x.com"), prof("on2", "s@x.com")], [])
        self.assertEqual(len([o for o in ops if o[0] == "create"]), 1)

    def test_deleted_account_address_is_removed(self):
        ops, _, taken = S.plan([], [sub("gone@x.com", account="1"), sub("legacy@x.com")])
        self.assertEqual(ops, [("delete", "gone@x.com")])
        self.assertEqual(taken, 1)


if __name__ == "__main__":
    unittest.main()
