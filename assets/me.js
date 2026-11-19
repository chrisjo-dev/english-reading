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

  // 지문 페이지나 가입 화면에서 "아침 메일 받기"로 왔으면(?mail=1&lang=&level=) 고른 설정으로 메일을 켠다.
  // 로그인이 풀렸으면 로그인 링크에 같은 설정을 실어 가입 화면으로 넘긴다.
  var Q = new URLSearchParams(location.search), want = null;
  if (Q.get("mail") === "1") {
    want = { mail_lang: ["en", "ja", "de"].indexOf(Q.get("lang")) >= 0 ? Q.get("lang") : "en", mail_level: Q.get("level") === "a" ? "a" : "b" };
    try { history.replaceState(null, "", location.pathname + location.hash); } catch (e) {}
  }
  function signedOut() {
    if (want) $("signedOut").querySelector("a.btn").href = "/join/?" + new URLSearchParams({ mail: "1", lang: want.mail_lang, level: want.mail_level, next: "/me/" }).toString();
    show("signedOut");
  }

  if (!A.ready) { show("notReady"); return; }
  if (!A.hasSession()) { signedOut(); return; }

  var c = null, uid = null, mail = {}, db = null, latest = null;
  function localDb() { try { return JSON.parse(localStorage.getItem(A.drillKey)) || { items: {} }; } catch (e) { return { items: {} }; } }
  function head(nick, prov) {
    nick = nick || "독해한입 회원";
    $("nick").textContent = nick + "님";
    $("av").textContent = nick.charAt(0);
    $("who").textContent = (prov === "google" ? "Google" : "카카오") + "로 로그인함";
  }
  function repaint() { paint(db || localDb(), latest); }

  // 1) 기다리지 않는다: 이 기기에 있는 값(닉네임 dkh-me, 로그인 정보 dkh-auth, 단어 기록 drill:v1)으로 바로 그린다
  var me0 = {}, ses0 = null;
  try { me0 = JSON.parse(localStorage.getItem("dkh-me")) || {}; } catch (e) {}
  try { ses0 = JSON.parse(localStorage.getItem("dkh-auth")); } catch (e) {}
  head(me0.n, ses0 && ses0.user && ses0.user.app_metadata && ses0.user.app_metadata.provider);
  $("mailTg").disabled = true;  // 메일 설정은 서버 값이 와야 정확하다
  $("mailEdit").disabled = true;
  repaint();
  show("signedIn");

  // 2) 서버 값이 오면 조용히 바꾼다(닉네임과 메일 설정, 다른 기기 기록을 합친 숫자, 오늘 지문 링크)
  fetch("/latest.json", { cache: "no-store" }).then(function (x) { return x.json(); }).then(function (d) { latest = d; repaint(); }, function () {});
  A.client().then(function (client) {
    c = client;
    return c.auth.getSession();
  }).then(function (r) {
    var s = r && r.data && r.data.session;
    if (!s) { signedOut(); return; }
    uid = s.user.id;
    var prov = s.user.app_metadata && s.user.app_metadata.provider;
    c.from("profiles").select("nickname, email, mail_opt_in, mail_verified, mail_lang, mail_level, mail_wait").eq("user_id", uid).maybeSingle().then(function (p) {
      var row = p.data || {};
      head(row.nickname, prov);
      try { localStorage.setItem("dkh-me", JSON.stringify({ n: row.nickname || "" })); } catch (e) {}
      mailPaint(row);
      $("mailTg").disabled = false; $("mailEdit").disabled = false;
      if (want) turnOn(row);
    }, function () { mailSay("메일 설정을 불러오지 못했어요. 잠시 뒤에 다시 열어 주세요.", true); });
    A.sync().then(function (merged) { if (merged) { db = merged; repaint(); } }, function () {});
  }).catch(function () {
    mailSay("서버에 연결하지 못했어요. 이 기기의 기록만 보여 드려요.", true);
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

  // 아침 지문 메일(시안 K18, K26): 주소, 켜고 끄기, 확인 대기와 대기 명단 표시, 받을 언어와 수준, 주소 바꾸기
  var RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
  function mailSay(t, err) { var m = $("mailMsg"); m.textContent = t; m.classList.toggle("err", !!err); m.hidden = !t; }
  function mailPaint(p) {
    mail = p;
    $("mailAddr").textContent = p.email || "받을 주소가 없어요";
    $("mailTg").setAttribute("aria-checked", String(!!p.mail_opt_in));
    $("mailWait").hidden = !(p.mail_opt_in && p.mail_wait);
    $("mailPend").hidden = !(p.mail_opt_in && p.email && !p.mail_verified && !p.mail_wait);
    var L = RANGE[p.mail_lang] ? p.mail_lang : "en";
    [].forEach.call($("pickLang").children, function (b) { b.setAttribute("aria-pressed", String(b.dataset.v === L)); });
    [].forEach.call($("pickLevel").children, function (b) { b.setAttribute("aria-pressed", String(b.dataset.v === (p.mail_level === "a" ? "a" : "b"))); });
    $("rangeA").textContent = RANGE[L][0]; $("rangeB").textContent = RANGE[L][1];
    $("mailEdit").textContent = p.email ? "주소 바꾸기" : "주소 적기";
  }
  function save(patch) {
    return c.from("profiles").update(patch).eq("user_id", uid).select("nickname, email, mail_opt_in, mail_verified, mail_lang, mail_level, mail_wait").maybeSingle()
      .then(function (r) { if (r.error || !r.data) throw r.error || new Error("profile not updated"); mailPaint(r.data); });
  }
  function turnOn(row) {
    if (row.mail_opt_in) {
      mailSay(row.mail_lang === want.mail_lang && row.mail_level === want.mail_level ? "이미 이 설정으로 아침 메일을 받고 있어요."
        : "이미 아침 메일을 받고 있어요. 받을 언어와 수준은 아래에서 바꿀 수 있어요.");
      return;
    }
    if (!row.email) {  // 주소가 없으면(카카오) 언어, 수준만 저장하고 주소를 받는다. 주소를 저장하면 메일이 켜진다.
      save(want).then(null, function () {});
      $("mailForm").hidden = false; $("mail").focus(); mailSay("받을 주소를 적으면 아침 메일이 켜져요.");
      return;
    }
    save({ mail_opt_in: true, mail_lang: want.mail_lang, mail_level: want.mail_level })
      .then(function () { mailSay("아침 지문 메일을 켰어요."); }, function () { mailSay("메일을 켜지 못했어요. 아래 스위치로 다시 켜 주세요.", true); });
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
  var RANGE = { en: ["A2~B1", "B1~B2"], ja: ["N4~N5", "N3"], de: ["A2~B1", "B1~B2"] };
  function pick(field) {
    return function (e) {
      var b = e.target.closest("button");
      if (!b || !uid || b.getAttribute("aria-pressed") === "true") return;
      var patch = {}; patch[field] = b.dataset.v;
      save(patch).then(function () { mailSay("받을 메일을 바꿨어요. 다음 날 아침 메일부터 적용돼요."); },
        function () { mailSay("바꾸지 못했어요. 잠시 뒤에 다시 해 주세요.", true); });
    };
  }
  $("pickLang").addEventListener("click", pick("mail_lang"));
  $("pickLevel").addEventListener("click", pick("mail_level"));
  $("mailEdit").addEventListener("click", function () { $("mailForm").hidden = false; $("mail").value = mail.email || ""; $("mail").focus(); });
  $("mailForm").addEventListener("submit", function (e) {
    e.preventDefault();
    var v = $("mail").value.trim();
    if (!RE.test(v) || v.length > 254) { mailSay("이메일 주소를 다시 확인해 주세요.", true); return; }
    save({ email: v, mail_opt_in: true }).then(function () { $("mailForm").hidden = true; mailSay("저장했어요. 영어 확인 메일의 버튼을 누르면 시작돼요."); },
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
