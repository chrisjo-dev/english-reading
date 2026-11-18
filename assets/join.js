// 가입 화면(/join/, 시안 design/kakao-login K02): 필수 동의 두 개 뒤 카카오 또는 Google 로그인.
// 카카오: 인가는 여기서 직접 시작하고(닉네임만, OpenID Connect), 콜백이 api Worker 로 id_token 을 받아 signInWithIdToken 한다.
//   Supabase 의 카카오 OAuth 는 이메일과 프로필 사진을 늘 함께 요청해서 쓰지 않는다(릴리랑과 같은 이유).
// Google: Supabase OAuth(PKCE)로 보내고, 콜백에서 exchangeCodeForSession 한다.
// 돌아올 곳(next)은 콜백까지 localStorage 로, 어느 쪽으로 갔는지와 state, nonce 는 sessionStorage 로 넘긴다.
// 리디렉트 주소는 언제나 정확히 <이 주소>/join/callback/ 하나(쿼리 없음). 카카오 콘솔과 Supabase 의 허용 주소와 같아야 한다.
(function () {
  "use strict";
  var A = window.dkhAuth;
  var NEXT_KEY = "dkh-next", OIDC_KEY = "dkh-oidc";
  var AUTHORIZE = "https://kauth.kakao.com/oauth/authorize";
  var CALLBACK = location.origin + "/join/callback/";
  function $(id) { return document.getElementById(id); }
  var age = $("agreeAge"), priv = $("agreePriv"), mailOpt = $("agreeMail"), kakao = $("kakao"), google = $("google"), msg = $("msg");
  var q = new URLSearchParams(location.search);
  var next = A.safeNext(q.get("next") || "/");
  var from = q.get("from") || "";
  var busy = false;
  // 받을 메일(시안 K21): 랜딩이나 지문 페이지에서 고른 언어와 수준을 채운다. 메일은 가입한 사람만 받는다.
  var LANGS = { en: ["A2~B1", "B1~B2"], ja: ["N4~N5", "N3"], de: ["A2~B1", "B1~B2"] };
  var mailLang = LANGS[q.get("lang")] ? q.get("lang") : "en";
  var mailLevel = q.get("level") === "a" ? "a" : "b";
  function paintPick() {
    [].forEach.call($("pickLang").children, function (b) { b.setAttribute("aria-pressed", String(b.dataset.v === mailLang)); });
    [].forEach.call($("pickLevel").children, function (b) { b.setAttribute("aria-pressed", String(b.dataset.v === mailLevel)); });
    $("rangeA").textContent = LANGS[mailLang][0]; $("rangeB").textContent = LANGS[mailLang][1];
    $("mailPick").hidden = !mailOpt.checked;
  }
  $("pickLang").addEventListener("click", function (e) { var b = e.target.closest("button"); if (b) { mailLang = b.dataset.v; paintPick(); } });
  $("pickLevel").addEventListener("click", function (e) { var b = e.target.closest("button"); if (b) { mailLevel = b.dataset.v; paintPick(); } });
  mailOpt.addEventListener("change", paintPick);
  if (q.get("mail") === "1") {
    mailOpt.checked = true;
    $("jStep").innerHTML = '아침 메일 받기 <span class="seat">선착순 100명 무료</span>';
    $("jTitle").textContent = "가입하면 매일 아침 지문이 와요";
    $("mailLabel").textContent = "매일 아침 지문 메일을 받을래요";
    $("perk3").style.display = "none";  // .perk 의 display:flex 가 hidden 을 이긴다
  }
  paintPick();

  function say(text, err) { msg.textContent = text; msg.classList.toggle("err", !!err); msg.hidden = !text; }
  function ok() { return A.ready && age.checked && priv.checked && !busy; }
  function update() {
    kakao.disabled = !(ok() && A.kakaoClientId);
    google.disabled = !ok();
  }
  function remember(p) {
    try { localStorage.setItem(NEXT_KEY, JSON.stringify({ next: next, mail: !!(mailOpt && mailOpt.checked), lang: mailLang, level: mailLevel, at: Date.now() })); } catch (e) {}
    try { sessionStorage.setItem(OIDC_KEY, JSON.stringify(p)); } catch (e) {}
  }
  function hex(buf) { return Array.prototype.map.call(new Uint8Array(buf), function (x) { return ("0" + x.toString(16)).slice(-2); }).join(""); }
  function random() { var b = new Uint8Array(32); crypto.getRandomValues(b); return hex(b); }
  // 카카오에는 sha256(nonce) 를, Supabase 에는 원래 nonce 를 준다(Supabase 가 해시해서 id_token 의 nonce 와 비교)
  function sha256hex(s) { return crypto.subtle.digest("SHA-256", new TextEncoder().encode(s)).then(hex); }
  function ga(name, p) { if (typeof gtag === "function") gtag("event", name, p); }

  if (!A.ready) { $("notReady").hidden = false; $("joinBox").hidden = true; return; }

  A.isMember().then(function (m) {
    if (!m) return;
    $("already").hidden = false; $("alreadyNext").href = next;
  });

  [age, priv].forEach(function (x) { x.addEventListener("change", update); });
  update();
  ga("login_view", { from: from || "direct" });

  kakao.addEventListener("click", function () {
    if (kakao.disabled) return;
    busy = true; update(); say("카카오로 이동하고 있어요.");
    ga("login_start", { provider: "kakao", from: from || "direct" });
    var state = random(), nonce = random();
    sha256hex(nonce).then(function (hashed) {
      remember({ p: "kakao", state: state, nonce: nonce, at: Date.now() });
      location.assign(AUTHORIZE + "?" + new URLSearchParams({
        client_id: A.kakaoClientId, redirect_uri: CALLBACK, response_type: "code",
        scope: "openid profile_nickname", state: state, nonce: hashed
      }).toString());
    }).catch(function () { busy = false; update(); say("카카오 로그인을 시작하지 못했어요. 잠시 뒤에 다시 해 주세요.", true); });
  });

  google.addEventListener("click", function () {
    if (google.disabled) return;
    busy = true; update(); say("Google로 이동하고 있어요.");
    ga("login_start", { provider: "google", from: from || "direct" });
    remember({ p: "google", at: Date.now() });
    A.client().then(function (c) {
      return c.auth.signInWithOAuth({ provider: "google", options: { redirectTo: CALLBACK, queryParams: { prompt: "select_account" } } });
    }).then(function (r) {
      if (r && r.error) throw r.error;
    }).catch(function () { busy = false; update(); say("Google 로그인을 시작하지 못했어요. 잠시 뒤에 다시 해 주세요.", true); });
  });
})();
