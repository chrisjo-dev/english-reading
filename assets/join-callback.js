// 로그인 콜백(/join/callback/, 시안 K03 처리 중, K04 실패).
// 카카오: ?code= 를 api Worker(/kakao/token)에서 id_token 으로 바꾸고 signInWithIdToken. state 는 가입 화면이 남긴 값과 같아야 한다.
// Google: ?code= 를 Supabase exchangeCodeForSession 으로 바꾼다(PKCE 검증값은 supabase-js 가 저장해 둔 것).
// 세션이 생기면 이 기기의 단어 기록을 계정 기록과 합친다. 코드가 주소창과 기록에 남지 않게 바로 지운다.
// 이 페이지는 광고, 통계 스크립트를 부르지 않는다(코드가 담긴 주소가 밖으로 나가지 않게).
(function () {
  "use strict";
  var A = window.dkhAuth;
  var NEXT_KEY = "dkh-next", OIDC_KEY = "dkh-oidc";
  var NEXT_TTL = 60 * 60 * 1000, OIDC_TTL = 10 * 60 * 1000, NEW_USER_WINDOW = 60 * 60 * 1000;

  var q = new URLSearchParams(location.search);
  var code = q.get("code"), state = q.get("state"), failed = q.get("error") || q.get("error_description");
  history.replaceState(null, "", location.pathname);

  var saved = null, oidc = null;
  try { saved = JSON.parse(localStorage.getItem(NEXT_KEY) || "null"); localStorage.removeItem(NEXT_KEY); } catch (e) {}
  if (!saved || !(Date.now() - saved.at < NEXT_TTL)) saved = { next: "/", mail: false };
  var next = A.safeNext(saved.next);
  try { oidc = JSON.parse(sessionStorage.getItem(OIDC_KEY) || "null"); sessionStorage.removeItem(OIDC_KEY); } catch (e) {}

  function $(id) { return document.getElementById(id); }
  function fail(text) {
    $("spin").hidden = true; $("errIc").hidden = false;
    $("title").textContent = "로그인하지 못했어요";
    $("status").textContent = text;
    $("retryLink").href = "/join/?" + new URLSearchParams({ next: next }).toString();
    $("homeLink").href = next.replace(/#drill$/, "");
    $("retry").hidden = false;
  }
  function count() {
    try { var v = JSON.parse(localStorage.getItem(A.drillKey)); return v && v.items ? Object.keys(v.items).length : 0; } catch (e) { return 0; }
  }

  if (!A.ready) { fail("로그인은 아직 준비 중이에요."); return; }
  if (failed) { fail("동의 화면을 닫았거나 연결이 잠깐 끊겼어요. 이 기기의 기록은 그대로 남아 있어요."); return; }
  if (!code) {
    A.isMember().then(function (m) { if (m) location.replace(next); else fail("로그인 정보가 없어요. 다시 해 주세요."); });
    return;
  }
  if (!oidc || !(Date.now() - oidc.at < OIDC_TTL) || (oidc.p !== "kakao" && oidc.p !== "google") ||
      (oidc.p === "kakao" && (typeof oidc.state !== "string" || oidc.state !== state || typeof oidc.nonce !== "string"))) {
    fail("로그인 시간이 지났거나 다른 브라우저에서 열렸어요. 가입 화면에서 다시 해 주세요.");
    return;
  }

  var needEmail = false, mailDone = false;
  var n = count();
  if (n) $("status").textContent = "이 기기의 단어 기록 " + n + "개를 함께 옮기고 있어요.";

  function signIn(c) {
    if (oidc.p === "google") return c.auth.exchangeCodeForSession(code);
    return fetch(A.api + "/kakao/token", {
      method: "POST", credentials: "omit", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ code: code })
    }).then(function (r) { if (!r.ok) throw new Error("exchange " + r.status); return r.json(); })
      .then(function (t) {
        if (!t || typeof t.id_token !== "string") throw new Error("no id_token");
        return c.auth.signInWithIdToken({ provider: "kakao", token: t.id_token, nonce: oidc.nonce });
      });
  }

  A.client().then(function (c) {
    return signIn(c).then(function (r) {
      if (r.error || !r.data || !r.data.user) throw r.error || new Error("no session");
      var isNew = Date.now() - Date.parse(r.data.user.created_at) < NEW_USER_WINDOW;
      if (typeof gtag === "function") gtag("event", isNew ? "sign_up" : "login", { method: oidc.p });
      var uid = r.data.user.id;
      // 위 메뉴의 마이페이지 동그라미가 쓰는 닉네임(첫 글자)을 이 기기에 둔다
      var nick = c.from("profiles").select("nickname, email").eq("user_id", uid).maybeSingle().then(function (p) {
        try { localStorage.setItem("dkh-me", JSON.stringify({ n: (p.data && p.data.nickname) || "" })); } catch (e) {}
        // 가입 화면에서 메일 받기를 골랐으면 고른 언어, 수준과 함께 켠다(시안 K21).
        // 주소가 없으면(카카오) 주소 적는 화면(K17), 있으면(Google) 가입 완료 화면(K24)으로 보낸다.
        if (saved.mail === true) {
          if (!(p.data && p.data.email)) needEmail = true; else mailDone = true;
          return c.from("profiles").update({
            mail_opt_in: true,
            mail_lang: ["en", "ja", "de"].indexOf(saved.lang) >= 0 ? saved.lang : "en",
            mail_level: saved.level === "a" ? "a" : "b"
          }).eq("user_id", uid);
        }
      }, function () {});
      return Promise.all([A.logEvent(isNew ? "signup" : "login"), A.sync().catch(function () { return null; }), nick]);
    });
  }).then(function () {
    $("title").textContent = "로그인했어요";
    $("status").textContent = "이어서 공부하러 가요.";
    var nq = "?" + new URLSearchParams({ next: next }).toString();
    location.replace(needEmail ? "/join/email/" + nq : mailDone ? "/join/done/" + nq : next);
  }).catch(function () {
    fail("로그인을 마치지 못했어요. 이 기기의 기록은 그대로 남아 있어요.");
  });
})();
