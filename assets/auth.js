// 독해한입 로그인(카카오, Google)과 단어 기록 동기화. 릴리랑 shared/api/supabase.js + entities/session/session.js 와 같은 방식.
// 다른 코드는 window.dkhAuth 만 쓴다: ready, hasSession, isMember, client, sync, streak, logEvent, joinUrl, safeNext, kakaoClientId.
// - 설정 값이 비어 있으면 ready=false: 로그인 기능이 없는 것처럼 동작한다(문제 풀기도 잠그지 않는다).
// - 여기에는 Project URL 과 anon(publishable) 키만 넣는다. 데이터는 RLS 가 막는다(supabase/migrations/0001_init.sql).
//   service role 키는 어떤 파일에도 넣지 않는다. 카카오 Client Secret 은 worker/ 의 비밀값에만 둔다.
// - kakaoClientId 는 카카오 REST API 키(인가 주소에 실리는 공개값)다.
// - 로그인 흔적이 없는 방문자는 supabase-js 를 받지 않는다(지문 페이지 성능).
(function () {
  "use strict";

  var CFG = window.DKH_AUTH_CONFIG || {
    supabaseUrl: "https://kfprgssvigujxphfmlth.supabase.co",
    supabaseAnonKey: "sb_publishable_cyzW-kfuGUNsm1mDeyKm1Q_dmlOxt9U",
    kakaoClientId: "620a2bf2ab9f1cf06a76b9c24ae84f4b",
    api: "https://api.dokhaehanip.com"
  };
  // 버전을 올리면 LIB_SRI 도 같이 바꾼다. 해시: curl -sL <LIB_URL> | openssl dgst -sha384 -binary | openssl base64 -A
  var LIB_URL = "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.117.3/dist/umd/supabase.js";
  var LIB_SRI = "sha384-BWcjm9OdFth9TbhCxZPdm+gAOUMAzQy9nmTs12ioXdCcbVnJaPMn+fMUoQCLt60R";
  var STORAGE_KEY = "dkh-auth";
  var DRILL_KEY = "drill:v1";
  var MAX_DAYS = 400;
  // supabase/migrations/0001_init.sql 의 dkh_event_name_ok 와 같은 목록
  var EVENTS = ["signup", "login", "logout", "delete_account", "gate_shown", "gate_join_click"];

  var url = typeof CFG.supabaseUrl === "string" ? CFG.supabaseUrl.replace(/\/+$/, "") : "";
  var key = typeof CFG.supabaseAnonKey === "string" ? CFG.supabaseAnonKey : "";
  var ready = /^https:\/\/[a-z0-9-]+\.supabase\.co$/.test(url) && key !== "" && isPublicKey(key);

  // 실수로 service role(secret) 키를 넣으면 쓰지 않는다
  function isPublicKey(k) {
    if (k.indexOf("sb_publishable_") === 0) return true;
    if (k.indexOf("sb_secret_") === 0) return bad();
    var part = k.split(".")[1];
    if (!part) return bad();
    try {
      var claims = JSON.parse(atob(part.replace(/-/g, "+").replace(/_/g, "/")));
      return claims.role === "anon" ? true : bad();
    } catch (e) { return bad(); }
    function bad() { console.error("dkhAuth: supabaseAnonKey 에는 anon 키만 넣어요."); return false; }
  }

  function get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function hasSession() { return ready && get(STORAGE_KEY) !== null; }

  var clientP = null, hooked = false, listeners = [];
  function client() {
    if (!ready) return Promise.resolve(null);
    if (!clientP) {
      clientP = new Promise(function (resolve, reject) {
        if (window.supabase && window.supabase.createClient) { resolve(make()); return; }
        var s = document.createElement("script");
        s.src = LIB_URL; s.integrity = LIB_SRI; s.crossOrigin = "anonymous"; s.referrerPolicy = "no-referrer"; s.async = true;
        s.onload = function () { resolve(make()); };
        s.onerror = function () { clientP = null; reject(new Error("supabase-js load failed")); };
        document.head.appendChild(s);
      });
    }
    return clientP.then(function (c) {
      if (c && !hooked) {
        hooked = true;
        c.auth.onAuthStateChange(function (_e, session) {
          listeners.slice().forEach(function (cb) { try { cb(!!session); } catch (e) { console.error(e); } });
        });
      }
      return c;
    });
  }
  function make() {
    return window.supabase.createClient(url, key, {
      auth: { flowType: "pkce", storageKey: STORAGE_KEY, persistSession: true, autoRefreshToken: true,
        detectSessionInUrl: false } // join/callback/ 에서 직접 교환한다
    });
  }

  function session() {
    if (!hasSession()) return Promise.resolve(null);
    return client().then(function (c) { return c.auth.getSession(); })
      .then(function (r) { return (r && r.data && r.data.session) || null; });
  }
  function isMember() { return session().then(function (s) { return !!s; }, function () { return false; }); }
  function onChange(cb) { if (typeof cb === "function") listeners.push(cb); }

  // 같은 주소의 경로만 허용(다른 사이트로 넘기는 next 막기). 끝에 #drill 하나만 붙일 수 있다
  function safeNext(v) {
    if (typeof v !== "string" || v.length > 100) return "/";
    if (!/^\/[A-Za-z0-9._\/-]*(#drill)?$/.test(v)) return "/";
    if (v.indexOf("//") !== -1 || v.indexOf("..") !== -1) return "/";
    return v;
  }
  function joinUrl(next, from) {
    var q = { next: safeNext(next || location.pathname) };
    if (from) q.from = from;
    return "/join/?" + new URLSearchParams(q).toString();
  }

  function logEvent(name, lang) {
    if (!ready || EVENTS.indexOf(name) === -1) return Promise.resolve(false);
    var l = typeof lang === "string" && /^[a-z]{2}$/.test(lang) ? lang : null;
    return session().then(function (s) {
      if (!s) return false;  // 비로그인 이벤트는 받지 않는다(supabase/migrations/0003). 통계는 GA 로 센다
      return client().then(function (c) {
        return c.from("events").insert({ user_id: s.user.id, name: name, lang: l }).then(function (r) { return !r.error; });
      });
    }).catch(function () { return false; });
  }

  // 단어 기록 합치기: 같은 단어는 나중에 고친(t) 쪽을 쓴다. t 가 없는 옛 기록끼리는 이 기기 것을 쓴다.
  // 공부한 날(days)은 둘을 합쳐 최근 MAX_DAYS 개만 둔다.
  function loadLocal() {
    try { var v = JSON.parse(get(DRILL_KEY)); if (v && v.items) return v; } catch (e) {}
    return { items: {} };
  }
  function merge(a, b) {
    var out = { items: {} }, k;
    a = a && a.items ? a : { items: {} };
    b = b && b.items ? b : { items: {} };
    for (k in b.items) out.items[k] = b.items[k];
    for (k in a.items) {
      var x = a.items[k], y = out.items[k];
      if (!y || (x.t || "") >= (y.t || "")) out.items[k] = x;
    }
    var seen = {}, days = [];
    (a.days || []).concat(b.days || []).forEach(function (d) {
      if (typeof d === "string" && /^\d{4}-\d{2}-\d{2}$/.test(d) && !seen[d]) { seen[d] = 1; days.push(d); }
    });
    out.days = days.sort().slice(-MAX_DAYS);
    return out;
  }
  // 서버 기록을 받아 이 기기 기록과 합친 뒤 양쪽에 같은 값을 둔다. 로그인 상태가 아니면 null.
  function sync() {
    return session().then(function (s) {
      if (!s) return null;
      return client().then(function (c) {
        var uid = s.user.id;
        return c.from("drill_state").select("data").eq("user_id", uid).maybeSingle().then(function (r) {
          if (r.error) throw r.error;
          var merged = merge(loadLocal(), r.data && r.data.data);
          try { localStorage.setItem(DRILL_KEY, JSON.stringify(merged)); } catch (e) {}
          return c.from("drill_state").upsert({ user_id: uid, data: merged, updated_at: new Date().toISOString() },
            { onConflict: "user_id" }).then(function (w) { if (w.error) throw w.error; return merged; });
        });
      });
    });
  }

  function pad(n) { return (n < 10 ? "0" : "") + n; }
  function ymd(d) { return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate()); }
  // 연속 학습일: 오늘(또는 아직 안 했으면 어제)부터 거꾸로 이어진 날 수. best 는 가장 길었던 연속.
  function streak(days) {
    var set = {}, best = 0, run = 0, prev = null;
    (days || []).slice().sort().forEach(function (d) {
      set[d] = 1;
      var cur = new Date(d + "T00:00:00");
      run = prev && Math.round((cur - prev) / 864e5) === 1 ? run + 1 : 1;
      best = Math.max(best, run); prev = cur;
    });
    var day = new Date(), n = 0;
    if (!set[ymd(day)]) day.setDate(day.getDate() - 1);
    while (set[ymd(day)]) { n++; day.setDate(day.getDate() - 1); }
    return { now: n, best: best };
  }

  window.dkhAuth = {
    ready: ready, hasSession: hasSession, isMember: isMember, onChange: onChange, client: client,
    sync: sync, merge: merge, streak: streak, logEvent: logEvent, joinUrl: joinUrl, safeNext: safeNext,
    kakaoClientId: typeof CFG.kakaoClientId === "string" ? CFG.kakaoClientId : "", api: CFG.api || "", drillKey: DRILL_KEY
  };
})();
