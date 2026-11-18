// 메일 받을 주소(/join/email/, 시안 design/kakao-login K17). 카카오 가입자가 메일 받기를 골랐을 때 한 번 나온다.
// 주소는 profiles.email 에 저장한다. 직접 적은 주소는 확인 전(mail_verified=false)이라, 동기화(tools/sync_members.py)가
// Buttondown 에 확인 메일이 가는 구독자로 넣는다. 저장하면 같은 자리에서 받은편지함 안내(K25, 다 찼으면 대기 문구)를 보인다.
(function () {
  "use strict";
  var A = window.dkhAuth;
  function $(id) { return document.getElementById(id); }
  var next = A.safeNext(new URLSearchParams(location.search).get("next") || "/");
  $("skip").href = next;
  $("sGo").href = next.replace(/#drill$/, "");
  function sent(c, addr) {
    $("sAddr").textContent = addr;
    $("mailForm").closest("section").hidden = true; $("sentBox").hidden = false;
    return c.from("mail_seats").select("taken, cap").eq("id", 1).maybeSingle().then(function (r) {
      var s = r && r.data;
      if (s && s.taken >= s.cap) { $("sWait").hidden = false; $("sLead").hidden = true; $("sTitle").textContent = "대기 명단에 올려 드렸어요"; }
    }, function () {});
  }
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
      }).then(function (r) {
        if (r && r.error) throw r.error;
        say("");
        return sent(c, v);
      });
    }).catch(function () {
      $("mailSave").disabled = false;
      say("저장하지 못했어요. 잠시 뒤에 다시 하거나 마이페이지에서 적어 주세요.", true);
    });
  });
})();
