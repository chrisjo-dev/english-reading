"""예전 주소(read.wspace.ai.kr)의 학습 기록을 새 주소에서 받는 머리 스크립트.

localStorage 는 주소(origin)마다 따로라 새 주소에서는 예전 기록이 보이지 않는다. 예전 주소의 Cloudflare Worker
(tools/cf/read-redirect.js)가 기록을 base64url(JSON) 으로 묶어 `#mig=` 뒤에 붙여 보내면, 이 스크립트가
새 쪽에 아직 없는 키만 넣고 주소의 # 을 지운다. 다른 # 앵커(#level-a 등)는 건드리지 않는다.
수준 설정(read_level:<언어>)을 읽는 머리 스크립트보다 먼저 돌아야 해서 <meta charset> 바로 뒤에 둔다.

받는 키(Worker 의 KEYS, PREFIXES 와 같아야 한다):
  drill:v1, drill:pref(단어 반복), read_speed(재생 속도), read_level(예전 공용 수준 키), lily.justListen(릴리 듣기만),
  read_level:<언어>(언어별 수준), vote:<언어>/<날짜>(주제 반응)
랜딩(landing/src/lib/migrate.ts)도 같은 문자열을 쓴다(tests/test_migrate.py 가 확인).
"""
import re

KEYS = ["drill:v1", "drill:pref", "read_speed", "read_level", "lily.justListen"]
PREFIXES = ["read_level:", "vote:"]

# 큰따옴표와 역슬래시를 쓰지 않는다(랜딩 TS 문자열에 그대로 옮기기 위해)
JS = ("try{(function(){var h=location.hash;if(h.slice(0,5)!=='#mig=')return;"
      "var s=h.slice(5).replace(/-/g,'+').replace(/_/g,'/');while(s.length%4)s+='=';"
      "var b=atob(s),u=new Uint8Array(b.length);for(var j=0;j<b.length;j++)u[j]=b.charCodeAt(j);"
      "var d=JSON.parse(new TextDecoder().decode(u)),K=" + "[" + ",".join(f"'{k}'" for k in KEYS) + "]"
      ",P=" + "[" + ",".join(f"'{p}'" for p in PREFIXES) + "];"
      "for(var k in d){if(!Object.prototype.hasOwnProperty.call(d,k)||typeof d[k]!=='string')continue;"
      "var ok=K.indexOf(k)>=0;for(var i=0;i<P.length;i++)if(k.indexOf(P[i])===0)ok=true;"
      "if(ok&&localStorage.getItem(k)===null)localStorage.setItem(k,d[k]);}})()}catch(e){}"
      "try{if(location.hash.slice(0,5)==='#mig=')history.replaceState(null,'',location.pathname+location.search)}catch(e){}")
TAG = f'<script id="mig">{JS}</script>'
TAG_RE = re.compile(r'<script id="mig">.*?</script>', re.S)
CHARSET = '<meta charset="utf-8">'


def apply(page):
    """머리에 받는 스크립트를 넣는다. 이미 있으면 지금 문자열로 바꾼다(멱등)."""
    if TAG_RE.search(page):
        return TAG_RE.sub(lambda m: TAG, page, count=1)
    return page.replace(CHARSET, CHARSET + TAG, 1)
