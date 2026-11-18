// 가입 완료(/join/done/, 시안 design/kakao-login K24, 다 찼으면 K24b). Google 가입자가 메일 받기를 골랐을 때 온다.
// 받을 메일(언어, 수준, 주소)은 profiles 에서 읽는다. 선착순 자리(mail_seats)가 찼거나 대기 중(mail_wait)이면 대기 명단 문구.
(function () {
  "use strict";
  var A = window.dkhAuth;
  function $(id) { return document.getElementById(id); }
  var NAME = { en: "영어", ja: "일본어", de: "독일어" };
  var RANGE = { en: ["A2~B1", "B1~B2"], ja: ["N4~N5", "N3"], de: ["A2~B1", "B1~B2"] };
  var next = A.safeNext(new URLSearchParams(location.search).get("next") || "/");
  $("dGo").href = next.replace(/#drill$/, "");
  if (!A.ready) return;
  A.client().then(function (c) {
    return c.auth.getSession().then(function (r) {
      var s = r && r.data && r.data.session;
      if (!s) { location.replace("/join/?" + new URLSearchParams({ next: next }).toString()); return; }
      return Promise.all([
        c.from("profiles").select("email, mail_lang, mail_level, mail_wait").eq("user_id", s.user.id).maybeSingle(),
        c.from("mail_seats").select("taken, cap").eq("id", 1).maybeSingle()
      ]).then(function (rs) {
        var p = (rs[0] && rs[0].data) || {}, seats = rs[1] && rs[1].data;
        var lang = NAME[p.mail_lang] ? p.mail_lang : "en", lv = p.mail_level === "a" ? 0 : 1;
        $("dWhat").textContent = NAME[lang] + " " + (lv ? "중급" : "기초") + " (" + RANGE[lang][lv] + ")";
        $("dAddr").textContent = p.email || "";
        $("dLead").textContent = "매일 07:00 전후에 오늘의 " + NAME[lang] + " 지문 한 편을 보내 드려요.";
        if (p.mail_wait || (seats && seats.taken >= seats.cap)) {
          $("dTitle").textContent = "대기 명단에 올려 드렸어요";
          $("dWait").hidden = false; $("dLead").hidden = true;
          $("dNote").textContent = "그동안 사이트에서 매일 새 지문을 읽고 단어를 외울 수 있어요.";
        }
      });
    });
  }).catch(function () {});
})();
