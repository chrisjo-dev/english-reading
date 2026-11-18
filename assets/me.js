// 마이페이지(/me/, 시안 design/kakao-login K06): 닉네임, 연속 학습일과 최근 7일, 외운 단어, 오늘 복습, 로그아웃, 탈퇴.
// 숫자는 계정 기록과 이 기기 기록을 합친 값(dkhAuth.sync)으로 센다.
(function () {
  "use strict";
  var A = window.dkhAuth;
  var WD = ["일", "월", "화", "수", "목", "금", "토"];
  var LNAME = { en: "영어", ja: "일본어", de: "독일어" };
  function $(id) { return document.getElementById(id); }
  function pad(n) { return (n < 10 ? "0" : "") + n; }
  function ymd(d) { return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate()); }
  function show(id) { ["loading", "signedOut", "signedIn", "notReady"].forEach(function (x) { $(x).hidden = x !== id; }); }
  function say(text, err) { var m = $("msg"); m.textContent = text; m.classList.toggle("err", !!err); m.hidden = !text; }

  if (!A.ready) { show("notReady"); return; }
  if (!A.hasSession()) { show("signedOut"); return; }

  var c = null, uid = null, mail = {};
  A.client().then(function (client) {
    c = client;
    return c.auth.getSession();
  }).then(function (r) {
    var s = r && r.data && r.data.session;
    if (!s) { show("signedOut"); return; }
    var prov = (s.user.app_metadata && s.user.app_metadata.provider) === "google" ? "Google" : "카카오";
    return Promise.all([
      c.from("profiles").select("nickname, email, mail_opt_in, mail_verified").eq("user_id", s.user.id).maybeSingle(),
      A.sync().catch(function () { return null; }),
      fetch("/latest.json", { cache: "no-store" }).then(function (x) { return x.json(); }).catch(function () { return null; })
    ]).then(function (rs) {
      var nick = (rs[0].data && rs[0].data.nickname) || "독해한입 회원";
      $("nick").textContent = nick + "님";
      try { localStorage.setItem("dkh-me", JSON.stringify({ n: (rs[0].data && rs[0].data.nickname) || "" })); } catch (e) {}
      $("av").textContent = nick.charAt(0);
      $("who").textContent = prov + "로 로그인함";
      uid = s.user.id;
      mailPaint(rs[0].data || {});
      paint(rs[1] || JSON.parse(localStorage.getItem(A.drillKey) || '{"items":{}}'), rs[2]);
      show("signedIn");
    });
  }).catch(function () {
    $("loading").textContent = "기록을 불러오지 못했어요. 잠시 뒤에 다시 열어 주세요.";
  });

  function paint(db, latest) {
    var days = db.days || [], st = A.streak(days), set = {};
    days.forEach(function (d) { set[d] = 1; });
    $("streak").textContent = st.now ? "연속 " + st.now + "일째" : "오늘 첫 기록을 남겨 볼까요?";
    $("best").textContent = "최고 기록 " + st.best + "일";
    var wk = $("week"); wk.textContent = "";
    for (var i = 6; i >= 0; i--) {
      var d = new Date(); d.setDate(d.getDate() - i);
      var el = document.createElement("div");
      el.className = "wd" + (set[ymd(d)] ? " on" : "") + (i === 0 ? " today" : "");
      el.appendChild(document.createElement("i"));
      el.appendChild(document.createTextNode(WD[d.getDay()]));
      wk.appendChild(el);
    }
    var t = ymd(new Date()), words = 0, due = {}, dueN = 0, pages = {};
    Object.keys(db.items || {}).forEach(function (k) {
      var it = db.items[k]; words++; pages[it.l + "|" + it.d] = 1;
      if (it.due && it.due <= t) { dueN++; due[it.l] = (due[it.l] || 0) + 1; }
    });
    $("nWords").textContent = words; $("nDue").textContent = dueN; $("nPages").textContent = Object.keys(pages).length;
    // 복습은 언어별로 그 언어의 최신 지문 페이지에서 한다(복습 띠). 복습할 단어가 가장 많은 언어로 보낸다
    var go = $("dueGo"), lang = Object.keys(due).sort(function (a, b) { return due[b] - due[a]; })[0];
    var day = lang && latest && latest.langs && latest.langs[lang] && latest.langs[lang].latest;
    if (lang && day) { go.href = "/" + lang + "/" + day + "/#drill"; go.textContent = (LNAME[lang] || "") + " 오늘 복습 " + due[lang] + "개 풀기"; go.hidden = false; }
    else if (latest && latest.langs && latest.langs.en) { go.href = "/en/" + latest.langs.en.latest + "/#drill"; go.textContent = "오늘 지문 단어 외우러 가기"; go.hidden = false; }
  }

  // 아침 지문 메일(시안 K18): 주소, 켜고 끄기, 확인 대기 표시, 주소 바꾸기
  var RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
  function mailSay(t, err) { var m = $("mailMsg"); m.textContent = t; m.classList.toggle("err", !!err); m.hidden = !t; }
  function mailPaint(p) {
    mail = p;
    $("mailAddr").textContent = p.email || "받을 주소가 없어요";
    $("mailTg").setAttribute("aria-checked", String(!!p.mail_opt_in));
    $("mailPend").hidden = !(p.mail_opt_in && p.email && !p.mail_verified);
    $("mailEdit").textContent = p.email ? "주소 바꾸기" : "주소 적기";
  }
  function save(patch) {
    return c.from("profiles").update(patch).eq("user_id", uid).select("nickname, email, mail_opt_in, mail_verified").maybeSingle()
      .then(function (r) { if (r.error) throw r.error; mailPaint(r.data || mail); });
  }
  $("mailTg").addEventListener("click", function () {
    if (!uid) return;
    var on = !mail.mail_opt_in;
    if (on && !mail.email) { $("mailForm").hidden = false; $("mail").focus(); mailSay("받을 주소를 먼저 적어 주세요."); return; }
    $("mailTg").disabled = true;
    save({ mail_opt_in: on }).then(function () { mailSay(on ? "아침 지문 메일을 켰어요." : "아침 지문 메일을 껐어요."); },
      function () { mailSay("바꾸지 못했어요. 잠시 뒤에 다시 해 주세요.", true); })
      .then(function () { $("mailTg").disabled = false; });
  });
  $("mailEdit").addEventListener("click", function () { $("mailForm").hidden = false; $("mail").value = mail.email || ""; $("mail").focus(); });
  $("mailForm").addEventListener("submit", function (e) {
    e.preventDefault();
    var v = $("mail").value.trim();
    if (!RE.test(v) || v.length > 254) { mailSay("이메일 주소를 다시 확인해 주세요.", true); return; }
    save({ email: v, mail_opt_in: true }).then(function () { $("mailForm").hidden = true; mailSay("저장했어요."); },
      function () { mailSay("저장하지 못했어요. 잠시 뒤에 다시 해 주세요.", true); });
  });

  $("logout").addEventListener("click", function () {
    A.logEvent("logout").then(function () { try { localStorage.removeItem("dkh-me"); } catch (e) {} return c.auth.signOut(); }).then(function () { location.replace("/"); },
      function () { say("로그아웃하지 못했어요. 다시 눌러 주세요.", true); });
  });
  $("del").addEventListener("click", function () {
    if (!confirm("탈퇴하면 계정과 저장된 단어 기록이 바로 지워지고 되돌릴 수 없어요. 이 기기에 남은 기록은 그대로예요. 탈퇴할까요?")) return;
    c.rpc("delete_my_account").then(function (r) {
      if (r.error) throw r.error;
      try { localStorage.removeItem("dkh-me"); } catch (e) {}
      return c.auth.signOut({ scope: "local" });
    }).then(function () { alert("탈퇴했어요. 그동안 고마웠어요."); location.replace("/"); },
      function () { say("탈퇴하지 못했어요. 잠시 뒤에 다시 하거나 연락처로 알려 주세요.", true); });
  });
})();
