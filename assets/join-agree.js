// 가입 동의(/join/agree/, 시안 design/kakao-login K33). 로그인 화면(/login/)에서 처음 만든 계정만 콜백이 이리로 보낸다.
// 동의하면 돌아갈 곳으로, 동의하지 않으면 방금 만든 계정을 지우고(delete_my_account) 로그아웃한다.
(function () {
  "use strict";
  var A = window.dkhAuth;
  function $(id) { return document.getElementById(id); }
  var next = A.safeNext(new URLSearchParams(location.search).get("next") || "/");
  var age = $("agreeAge"), priv = $("agreePriv"), c = null;
  function say(t, err) { var m = $("msg"); m.textContent = t; m.classList.toggle("err", !!err); m.hidden = !t; }
  function both() { return age.checked && priv.checked; }
  [age, priv].forEach(function (x) { x.addEventListener("change", function () { if (both()) { document.querySelector(".agree").classList.remove("need"); $("needMsg").hidden = true; } }); });
  if (!A.ready) return;
  A.client().then(function (client) { c = client; return c.auth.getSession(); }).then(function (r) {
    if (!(r && r.data && r.data.session)) location.replace("/login/?" + new URLSearchParams({ next: next }).toString());
  }).catch(function () { say("서버에 연결하지 못했어요. 잠시 뒤에 다시 열어 주세요.", true); });
  $("agreeGo").addEventListener("click", function () {
    if (!both()) { document.querySelector(".agree").classList.add("need"); $("needMsg").hidden = false; return; }
    location.replace(next);
  });
  $("agreeNo").addEventListener("click", function () {
    if (!c) return;
    $("agreeNo").disabled = true;
    c.rpc("delete_my_account").then(function (r) {
      if (r.error) throw r.error;
      try { localStorage.removeItem("dkh-me"); } catch (e) {}
      return c.auth.signOut({ scope: "local" });
    }).then(function () { location.replace(next.replace(/#drill$/, "")); },
      function () { $("agreeNo").disabled = false; say("계정을 지우지 못했어요. 잠시 뒤에 다시 해 주세요.", true); });
  });
})();
