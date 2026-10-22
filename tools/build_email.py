"""날짜 페이지(<언어>/YYYY-MM-DD/index.html)에서 뉴스레터 메일 제목과 본문 HTML을 만든다.

사용: python3 tools/build_email.py en 2026-10-12 > /tmp/email.json
출력: {"subject": ..., "body": ...}  (body는 Buttondown에 그대로 넣는 HTML)
"""
import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import langs  # noqa: E402

SITE = "https://read.wspace.ai.kr"
BLUE, INK, SUB, MUTED, BG, HL = "#3182f6", "#191f28", "#4e5968", "#8b95a1", "#f2f4f6", "#fff3c4"
FONT = "-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo','Noto Sans KR','Malgun Gothic','Hiragino Sans','Noto Sans JP',sans-serif"


def grab(pattern, text, flags=re.S):
    m = re.search(pattern, text, flags)
    if not m:
        raise SystemExit(f"페이지에서 찾지 못함: {pattern}")
    return m.group(1).strip()


def parse(lang, day):
    page = (Path(__file__).resolve().parent.parent / lang / day / "index.html").read_text(encoding="utf-8")
    passage = grab(r'<section class="card" id="passage">(.*?)</section>', page)
    words_sec = grab(r'<h2>주요 단어</h2>(.*?)</section>', page)
    src = re.search(r'<p class="src">출처: <a href="([^"]+)"[^>]*>(.*?)</a></p>', page, re.S)
    return {
        "date": grab(r'<div class="date">(.*?)</div>', page),
        "topic": html.unescape(grab(r'<h1>.*?<em>(.*?)</em>', page)),
        "headline": (re.search(r'<p class="headline"[^>]*>(.*?)</p>', page, re.S) or [None, ""])[1],
        "chips": [html.unescape(c) for c in re.findall(r'<span class="chip[^"]*">(.*?)</span>', page)],
        "sentences": re.findall(r'<div class="en">(.*?)</div>', passage, re.S),
        "words": re.findall(r'<span class="w">(.*?)</span><span class="m">(.*?)</span>', words_sec),
        "source": (src.group(1), src.group(2)) if src else None,
    }


def sentence_html(raw):
    # 페이지의 <b> 강조와 B2 배지를 메일 클라이언트용 인라인 스타일로 바꾼다.
    raw = re.sub(r'<b>(.*?)</b>', rf'<span style="background:{HL};font-weight:600;">\1</span>', raw)
    return re.sub(
        r'<span class="badge">(.*?)</span>',
        r'<span style="display:inline-block;font-size:11px;font-weight:700;padding:1px 6px;border-radius:6px;'
        r'background:#ffeeee;color:#f04452;margin-left:6px;">\1</span>',
        raw,
    )


def _marks_email(s):
    """**bold** -> <b>, 이스케이프 없이 적용 (이미 html.escape 된 문자열에 사용하지 않음)."""
    import html as _html
    s = _html.escape(s, quote=False)
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)


def build(lang, day, level="b"):
    L = langs.get(lang)
    d = parse(lang, day)
    url_base = f"{SITE}/{lang}/{day}/"  # 썸네일 등 에셋용 기본 URL (쿼리 없음)
    if level == "a":
        content_path = Path(__file__).resolve().parent.parent / "content" / lang / f"{day}.json"
        content = json.loads(content_path.read_text(encoding="utf-8"))
        levels_a = (content.get("levels") or {}).get("a")
        if not levels_a:
            return None  # 기초 콘텐츠 없음
        d["sentences"] = [_marks_email(s["en"]) for s in levels_a["sentences"]]
        url = url_base + "?level=a"  # 기초 이메일: ?level=a 파라미터
    else:
        url = url_base  # 중급 이메일: 쿼리 없음(페이지 기본값 b), Phase 2 이전과 바이트 동일
    chips = "".join(
        f'<span style="display:inline-block;font-size:13px;font-weight:600;padding:4px 9px;border-radius:8px;'
        f'margin:0 4px 4px 0;background:{"#e8f3ff" if i == 0 else BG};color:{BLUE if i == 0 else SUB};">{html.escape(c)}</span>'
        for i, c in enumerate(d["chips"])
    )
    rows = "".join(
        f'<tr><td valign="top" style="width:28px;padding:10px 0;font-size:13px;font-weight:700;color:{MUTED};">{i}</td>'
        f'<td style="padding:10px 0;font-size:17px;line-height:1.7;color:{INK};">{sentence_html(s)}</td></tr>'
        for i, s in enumerate(d["sentences"], 1)
    )
    words = "".join(
        f'<tr><td style="padding:8px 0;font-size:16px;font-weight:700;color:{INK};border-top:1px solid {BG};">{w}</td>'
        f'<td align="right" style="padding:8px 0;font-size:15px;color:{SUB};border-top:1px solid {BG};">{m}</td></tr>'
        for w, m in d["words"]
    )
    source = ""
    if d["source"]:
        href, title = d["source"]
        source = (f'<p style="margin:16px 0 0;font-size:13px;color:{MUTED};">출처: '
                  f'<a href="{href}" style="color:{SUB};">{title}</a></p>')
    card = f"background:#ffffff;border-radius:20px;padding:22px 20px;"
    label = f"margin:0 0 4px;font-size:13px;font-weight:700;color:{BLUE};"
    h2 = f"margin:0 0 12px;font-size:19px;font-weight:700;color:{INK};"

    body = f"""<!-- buttondown-editor-mode: plaintext -->
<div style="background:{BG};padding:16px 0;font-family:{FONT};word-break:keep-all;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;margin:0 auto;">
<tr><td style="padding:0 0 12px;"><a href="{url}"><img src="{url_base}thumb.png" width="560" alt="오늘은 {html.escape(d["topic"])} 이야기예요"
  style="display:block;width:100%;max-width:560px;height:auto;border:0;border-radius:20px;"></a></td></tr>
<tr><td style="{card}">
  <p style="margin:0;font-size:14px;font-weight:600;color:{MUTED};">{d["date"]}</p>
  <h1 style="margin:6px 0 12px;font-size:24px;line-height:1.35;font-weight:800;color:{INK};">오늘은 <span style="color:{BLUE};">{html.escape(d["topic"])}</span> 이야기예요</h1>
  {f'<p style="margin:-6px 0 12px;font-size:16px;font-weight:600;color:{SUB};">{d["headline"]}</p>' if d.get("headline") else ""}
  {chips}
</td></tr>
<tr><td style="height:12px;"></td></tr>
<tr><td style="{card}">
  <p style="{label}">STEP 1</p>
  <h2 style="{h2}">오늘의 지문</h2>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">{rows}</table>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:18px;"><tr>
    <td align="center" style="background:{BLUE};border-radius:14px;">
      <a href="{url}" style="display:block;padding:16px 12px;font-size:16px;font-weight:700;color:#ffffff;text-decoration:none;">음성 듣고 해석 쓰러 가기</a>
    </td></tr></table>
  <p style="margin:10px 0 0;font-size:13px;color:{MUTED};text-align:center;">문장별 음성, 0.8배속, 모범 해석은 웹에서 볼 수 있어요.</p>
  {source}
</td></tr>
<tr><td style="height:12px;"></td></tr>
<tr><td style="{card}">
  <p style="{label}">STEP 2</p>
  <h2 style="{h2}">주요 단어</h2>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">{words}</table>
</td></tr>
<tr><td style="padding:16px 8px 0;font-size:13px;color:{MUTED};text-align:center;">
  <a href="{SITE}/{lang}/archive/" style="color:{SUB};">지난 지문 모아 보기</a>
  <p style="margin:12px 0 0;font-size:12px;line-height:1.6;color:{MUTED};">매일 아침 {L["level"]} {L["name"]} 지문을 보내 드려요.<br>
  더 받지 않으려면 <a href="{{{{ unsubscribe_url }}}}" style="color:{MUTED};">수신거부</a>를 눌러 주세요.</p>
</td></tr>
</table>
</div>"""
    return {"subject": f"오늘은 {d['topic']} 이야기예요 | {L['site']}", "body": body}


if __name__ == "__main__":
    result = build(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "b")
    if result is None:
        print("기초 콘텐츠 없음, 건너뜀", file=sys.stderr)
        sys.exit(0)
    json.dump(result, sys.stdout, ensure_ascii=False)
