"""사이트 반응을 DB에 보내는 브라우저 함수(api Worker /events, worker/events.js, 표 supabase/migrations/0006_site_events.sql).

vote.py(오늘 주제 반응)와 feedback.py(기능 건의, 버그 제보) 스크립트 앞에 붙인다. 두 번 붙어도 한 번만 정의한다.
익명 방문 번호(localStorage dkh-vid)만 실어 보낸다. sendBeacon(text/plain)이라 페이지를 떠나도 가고, CORS 사전 요청이 없다.
GA 이벤트는 그대로 두고 함께 보낸다.
"""
JS = (
    "window.dkhEvent=window.dkhEvent||function(o){try{"
    "var k='dkh-vid',v=localStorage.getItem(k);"
    "if(!/^[a-f0-9]{32}$/.test(v||'')){v=[].map.call(crypto.getRandomValues(new Uint8Array(16)),function(b){return('0'+b.toString(16)).slice(-2);}).join('');localStorage.setItem(k,v);}"
    "o.vid=v;navigator.sendBeacon('https://api.dokhaehanip.com/events',JSON.stringify(o));"
    "}catch(e){}};\n"
)
