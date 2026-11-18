// 메일 받을 주소(/join/email/, 시안 design/kakao-login K17). 카카오 가입자가 메일 받기를 골랐을 때 한 번 나온다.
// 주소는 profiles.email 에 저장한다. 직접 적은 주소는 확인 전(mail_verified=false)이라 발송 서비스가 확인 메일부터 보낸다.
(function () {
  "use strict";
  var A = window.dkhAuth;
  function $(id) { return document.getElementById(id); }
  var next = A.safeNext(new URLSearchParams(location.search).get("next") || "/");
  $("skip").href = next;
  function say(t, err) { var m = $("msg"); m.textContent = t; m.classList.toggle("err", !!err); m.hidden = !t; }
  var RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
  $("mailForm").addEventListener("submit", function (e) {
    e.preventDefault();
    var v = $("mail").value.trim();
    if (!RE.test(v) || v.length > 254) { say("이메일 주소를 다시 확인해 주세요.", true); return; }
    $("mailSave").disabled = true; say("저장하고 있어요.");
    A.client().then(function (c) {
      return c.auth.getSession().then(function (r) {
        var s = r && r.data && r.data.session;
        if (!s) throw new Error("no session");
        return c.from("profiles").update({ email: v, mail_opt_in: true }).eq("user_id", s.user.id);
      });
    }).then(function (r) {
      if (r && r.error) throw r.error;
      say("저장했어요. 이어서 공부하러 가요.");
      location.replace(next);
    }).catch(function () {
      $("mailSave").disabled = false;
      say("저장하지 못했어요. 잠시 뒤에 다시 하거나 마이페이지에서 적어 주세요.", true);
    });
  });
})();
