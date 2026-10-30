"""날짜 페이지의 썸네일(<언어>/YYYY-MM-DD/thumb.png, 1200x630)을 만든다. 시안: design/article-thumb T11~T13.

사용: python3 tools/thumb.py en 2026-10-12 [분야] [--photo 사진파일]
분야: science, tech, society, future, culture, space (생략하면 요일별 기본 분야)
메일 상단, 날짜 페이지 상단, 링크 미리보기(OG)에 같은 이미지를 쓴다.

OPENAI_API_KEY 가 있으면 기사에 맞는 사진을 OpenAI 이미지 API(gpt-image-1-mini, low)로 만들어 전체에 깔고
왼쪽 아래에 분야, 제목, 날짜를 올린다. 키가 없거나 생성이 실패하면 예전처럼 분야 일러스트로 만든다(발행은 멈추지 않는다).
사진 썸네일은 PNG 메타데이터(thumb=photo)로 표시해 두고, 다시 만들 때는 새로 그리지 않고 그대로 둔다(THUMB_REDRAW=1 이면 다시 그린다).
"""
import base64
import datetime as dt
import io
import json
import math
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, PngImagePlugin

sys.path.insert(0, str(Path(__file__).resolve().parent))
import langs  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FONTS = Path(__file__).resolve().parent / "fonts"
S = 2  # 2배로 그린 뒤 줄여서 가장자리를 부드럽게 한다.
W, H = 1200 * S, 630 * S
INK, SUB, BG = (25, 31, 40), (78, 89, 104), (242, 244, 246)

# 요일별 분야(예약 작업 지침과 같다): 월 과학, 화 기술, 수 사회, 목 미래, 금 과학, 토 일상·문화, 일 우주·미래
WEEKDAY = ["science", "tech", "society", "future", "science", "culture", "space"]
CATS = {
    "science": ("과학", (49, 130, 246), (232, 243, 255)),
    "tech": ("기술", (107, 92, 246), (240, 238, 255)),
    "society": ("사회", (240, 112, 64), (255, 240, 233)),
    "future": ("미래", (18, 172, 124), (230, 248, 241)),
    "culture": ("일상과 문화", (232, 154, 20), (255, 245, 224)),
    "space": ("우주", (61, 76, 196), (234, 236, 252)),
}
DAYS = "월화수목금토일"


def font(weight, size):
    return ImageFont.truetype(str(FONTS / f"Pretendard-{weight}.otf"), size * S)


def tint(c, k):
    """색을 흰색 쪽으로 k(0~1)만큼 옅게 한다."""
    return tuple(round(v + (255 - v) * k) for v in c)


def ring(img, box, color, width, angle):
    """기울어진 타원 궤도를 그린다."""
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).ellipse(box, outline=color, width=width)
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    img.alpha_composite(layer.rotate(angle, center=(cx, cy), resample=Image.BICUBIC))


def draw_science(img, d, cx, cy, c):
    # 플라스크: 목, 둥근 몸통, 안의 액체와 거품
    d.rounded_rectangle((cx - 44 * S, cy - 220 * S, cx + 44 * S, cy - 40 * S), 14 * S, fill=tint(c, .35))
    d.rounded_rectangle((cx - 70 * S, cy - 236 * S, cx + 70 * S, cy - 204 * S), 14 * S, fill=c)
    d.ellipse((cx - 170 * S, cy - 90 * S, cx + 170 * S, cy + 250 * S), fill=tint(c, .35))
    d.chord((cx - 170 * S, cy - 90 * S, cx + 170 * S, cy + 250 * S), 10, 170, fill=c)
    for x, y, r in ((-60, 150, 22), (40, 110, 16), (70, 180, 12), (-10, 40, 14), (20, -20, 10), (-20, -110, 8)):
        d.ellipse((cx + (x - r) * S, cy + (y - r) * S, cx + (x + r) * S, cy + (y + r) * S), fill=(255, 255, 255))


def draw_tech(img, d, cx, cy, c):
    r = 150 * S
    for i in range(-2, 3):
        o = i * 56 * S
        for x0, y0, x1, y1 in ((cx + o - 12 * S, cy - r - 60 * S, cx + o + 12 * S, cy - r),
                               (cx + o - 12 * S, cy + r, cx + o + 12 * S, cy + r + 60 * S),
                               (cx - r - 60 * S, cy + o - 12 * S, cx - r, cy + o + 12 * S),
                               (cx + r, cy + o - 12 * S, cx + r + 60 * S, cy + o + 12 * S)):
            d.rounded_rectangle((x0, y0, x1, y1), 10 * S, fill=tint(c, .35))
    d.rounded_rectangle((cx - r, cy - r, cx + r, cy + r), 44 * S, fill=c)
    d.rounded_rectangle((cx - 78 * S, cy - 78 * S, cx + 78 * S, cy + 78 * S), 24 * S, fill=tint(c, .25))
    d.rounded_rectangle((cx - 40 * S, cy - 40 * S, cx + 40 * S, cy + 40 * S), 12 * S, fill=tint(c, .7))


def draw_society(img, d, cx, cy, c):
    for dx, k, s in ((-150, .45, .82), (150, .45, .82), (0, 0, 1.0)):
        x, hr, br = cx + dx * S, 62 * S * s, 120 * S * s
        top = cy - 40 * S * s
        d.ellipse((x - hr, top - 2.4 * hr, x + hr, top - .4 * hr), fill=tint(c, k), outline=(255, 255, 255), width=8 * S)
        d.pieslice((x - br, top, x + br, top + 2 * br), 180, 360, fill=tint(c, k), outline=(255, 255, 255), width=8 * S)


def draw_future(img, d, cx, cy, c):
    # 전구: 둥근 유리, 받침, 안쪽 빛
    d.ellipse((cx - 150 * S, cy - 210 * S, cx + 150 * S, cy + 90 * S), fill=c)
    d.polygon([(cx - 92 * S, cy + 40 * S), (cx + 92 * S, cy + 40 * S), (cx + 62 * S, cy + 130 * S), (cx - 62 * S, cy + 130 * S)], fill=c)
    for i in range(3):
        y = cy + (140 + i * 36) * S
        d.rounded_rectangle((cx - 64 * S, y, cx + 64 * S, y + 24 * S), 12 * S, fill=tint(c, .3 + i * .15))
    d.ellipse((cx - 90 * S, cy - 160 * S, cx - 30 * S, cy - 100 * S), fill=tint(c, .55))
    d.arc((cx - 46 * S, cy - 56 * S, cx + 46 * S, cy + 36 * S), 180, 360, fill=tint(c, .75), width=12 * S)
    for x in (-40, 40):
        d.line([(cx + x * S, cy - 10 * S), (cx + x * S, cy + 70 * S)], fill=tint(c, .75), width=12 * S)
    for x, y, r in ((cx - 220 * S, cy - 150 * S, 34), (cx + 215 * S, cy - 40 * S, 26), (cx + 170 * S, cy - 210 * S, 18)):
        r *= S
        d.polygon([(x, y - r), (x + r * .3, y - r * .3), (x + r, y), (x + r * .3, y + r * .3),
                   (x, y + r), (x - r * .3, y + r * .3), (x - r, y), (x - r * .3, y - r * .3)], fill=tint(c, .3))


def draw_culture(img, d, cx, cy, c):
    w, h = 180 * S, 230 * S
    d.polygon([(cx, cy - h / 2 + 20 * S), (cx - w, cy - h / 2), (cx - w, cy + h / 2), (cx, cy + h / 2 + 20 * S)], fill=c)
    d.polygon([(cx, cy - h / 2 + 20 * S), (cx + w, cy - h / 2), (cx + w, cy + h / 2), (cx, cy + h / 2 + 20 * S)], fill=tint(c, .2))
    for i in range(4):
        y = cy - 60 * S + i * 42 * S
        d.line([(cx - w + 36 * S, y - 4 * S), (cx - 36 * S, y + 4 * S)], fill=tint(c, .6), width=10 * S)
        d.line([(cx + 36 * S, y + 4 * S), (cx + w - 36 * S, y - 4 * S)], fill=tint(c, .7), width=10 * S)
    d.line([(cx, cy - h / 2 + 20 * S), (cx, cy + h / 2 + 20 * S)], fill=(255, 255, 255), width=8 * S)


def draw_space(img, d, cx, cy, c):
    r = 130 * S
    ring(img, (cx - 250 * S, cy - 64 * S, cx + 250 * S, cy + 64 * S), tint(c, .45) + (255,), 22 * S, 18)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=c)
    d.ellipse((cx - 70 * S, cy - 80 * S, cx - 20 * S, cy - 30 * S), fill=tint(c, .3))
    d.ellipse((cx + 30 * S, cy + 20 * S, cx + 80 * S, cy + 70 * S), fill=tint(c, .2))
    # 앞쪽 고리: 행성 아래쪽 반만 다시 그려 행성을 감싸는 것처럼 보이게 한다.
    front = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(front).arc((cx - 250 * S, cy - 64 * S, cx + 250 * S, cy + 64 * S), 0, 180, fill=tint(c, .45) + (255,), width=22 * S)
    img.alpha_composite(front.rotate(18, center=(cx, cy), resample=Image.BICUBIC))
    for x, y, s in ((-230, -170, 16), (220, -190, 12), (250, 170, 18), (-200, 190, 10)):
        d.ellipse((cx + x * S - s * S, cy + y * S - s * S, cx + x * S + s * S, cy + y * S + s * S), fill=tint(c, .35))


DRAW = {"science": draw_science, "tech": draw_tech, "society": draw_society,
        "future": draw_future, "culture": draw_culture, "space": draw_space}


def fit(d, text, weight, size, max_w):
    while size > 40:
        f = font(weight, size)
        if d.textlength(text, font=f) <= max_w:
            return f
        size -= 4
    return font(weight, size)


PHOTO_MODEL = "gpt-image-1-mini"
PHOTO_STYLE = ("Editorial magazine photograph used as a news article thumbnail. Natural light, realistic, shallow depth of field, "
               "calm and clean composition with one clear subject, landscape framing with some empty space on the left. "
               "Absolutely no text, letters, numbers, logos or watermarks anywhere in the image.")


def _plain(s):
    return re.sub(r"\{([^|{}]+)\|[^{}]+\}", r"\1", s).replace("**", "")


def photo_prompt(lang, day):
    d = json.loads((ROOT / "content" / lang / f"{day}.json").read_text(encoding="utf-8"))
    lead = " ".join(_plain(s["en"]) for s in d.get("sentences", [])[:3])
    return (f"{PHOTO_STYLE}\nArticle topic (Korean): {d.get('topic', '')}. Article title (Korean): {d.get('title_ko', '')}. "
            f"Headline: {_plain(d.get('headline', ''))}. Opening sentences: {lead}\n"
            "Photograph the single most recognizable real-world scene or object from this article.")


def photo(lang, day):
    """기사에 맞는 사진(PIL 이미지). 키가 없거나 실패하면 None. 키와 응답 본문은 출력하지 않는다."""
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key or not (ROOT / "content" / lang / f"{day}.json").exists():
        return None
    body = json.dumps(dict(model=PHOTO_MODEL, prompt=photo_prompt(lang, day), size="1536x1024", quality="low", n=1)).encode()
    req = urllib.request.Request("https://api.openai.com/v1/images/generations", body,
                                 {"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        r = json.loads(urllib.request.urlopen(req, timeout=180).read())
        return Image.open(io.BytesIO(base64.b64decode(r["data"][0]["b64_json"]))).convert("RGB")
    except urllib.error.HTTPError as e:
        print(f"thumb: 사진 생성 실패 HTTP {e.code}, 일러스트로 만든다", file=sys.stderr)
    except Exception as e:  # 네트워크, 응답 형식 오류
        print(f"thumb: 사진 생성 실패 {type(e).__name__}, 일러스트로 만든다", file=sys.stderr)
    return None


def _wrap(d, text, f, max_w):
    """띄어쓰기 단위로 max_w 안에 줄을 나눈다(최대 2줄, 넘치면 마지막 줄을 …로 줄인다)."""
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur); cur = w
    lines.append(cur)
    if len(lines) > 2:
        last = " ".join(lines[1:])
        while d.textlength(last + "…", font=f) > max_w and len(last) > 1:
            last = last[:-1]
        lines = [lines[0], last.rstrip() + "…"]
    return lines


def compose(lang, day, cat, topic, pic):
    """사진을 1200x630 전체에 깔고(가운데 기준으로 잘라) 왼쪽을 어둡게 눌러 흰 글씨를 올린다."""
    date = dt.date.fromisoformat(day)
    label, color, _ = CATS[cat]
    k = max(W / pic.width, H / pic.height)
    pic = pic.resize((math.ceil(pic.width * k), math.ceil(pic.height * k)), Image.LANCZOS)
    x0, y0 = (pic.width - W) // 2, (pic.height - H) // 2
    img = pic.crop((x0, y0, x0 + W, y0 + H)).convert("RGBA")
    # 왼쪽 어둡게: 0~48% 는 .78→.45, 48~78% 는 .45→0 (시안의 linear-gradient 와 같다)
    shade = Image.new("L", (W, 1))
    for x in range(W):
        t = x / W
        a = .78 - (.78 - .45) * t / .48 if t < .48 else (.45 * (1 - (t - .48) / .30) if t < .78 else 0)
        shade.putpixel((x, 0), round(255 * a))
    dark = Image.new("RGBA", (W, H), (10, 14, 22, 255))
    dark.putalpha(shade.resize((W, H)))
    img.alpha_composite(dark)
    d = ImageDraw.Draw(img)
    x, white, soft = 80 * S, (255, 255, 255), (255, 255, 255, 219)
    d.text((x, 92 * S), langs.get(lang)["site"], font=font("SemiBold", 30), fill=soft)
    tf = font("ExtraBold", 44)
    lines = _wrap(d, topic, tf, 640 * S)
    date_y = 630 * S - 76 * S - 38 * S          # 날짜 줄(32px) 위끝
    title_y = date_y - 22 * S - len(lines) * 58 * S
    chip_y = title_y - 22 * S - 50 * S
    chip = font("SemiBold", 26)
    cw = d.textlength(label, font=chip)
    d.rounded_rectangle((x, chip_y, x + cw + 36 * S, chip_y + 50 * S), 14 * S, fill=color)
    d.text((x + 18 * S, chip_y + 25 * S), label, font=chip, fill=white, anchor="lm")
    for i, line in enumerate(lines):
        d.text((x, title_y + i * 58 * S), line, font=tf, fill=white)
    d.text((x, date_y), f"{date.month}월 {date.day}일 {DAYS[date.weekday()]}요일", font=font("SemiBold", 32), fill=soft)
    return img


def is_photo(path):
    try:
        return Image.open(path).info.get("thumb") == "photo"
    except Exception:
        return False


def build(lang, day, cat=None, pic=None):
    date = dt.date.fromisoformat(day)
    cat = cat or WEEKDAY[date.weekday()]
    label, color, soft = CATS[cat]
    page = (ROOT / lang / day / "index.html").read_text(encoding="utf-8")
    topic = re.search(r"<h1>.*?<em>(.*?)</em>", page, re.S).group(1).strip()
    out = ROOT / lang / day / "thumb.png"
    if pic is None and is_photo(out) and os.environ.get("THUMB_REDRAW") != "1":
        return out  # 이미 사진 썸네일이면 다시 만들지 않는다(같은 날 다시 발행해도 비용이 들지 않고 그림도 그대로)
    pic = pic or photo(lang, day)
    if pic is not None:
        meta = PngImagePlugin.PngInfo(); meta.add_text("thumb", "photo")
        small = compose(lang, day, cat, topic, pic).convert("RGB").resize((W // S, H // S), Image.LANCZOS)
        # 사진 PNG 는 0.6~1MB 라 메일에 무겁다. 256색으로 줄이면 겉보기는 같고 200~400KB 가 된다(파일 이름 thumb.png 는 그대로)
        small.quantize(256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG).save(out, optimize=True, pnginfo=meta)
        return out

    img = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    d = ImageDraw.Draw(img)
    # 오른쪽: 분야 색 원 안에 일러스트
    cx, cy = 880 * S, 315 * S
    d.ellipse((cx - 290 * S, cy - 290 * S, cx + 290 * S, cy + 290 * S), fill=soft)
    DRAW[cat](img, d, cx, cy, color)
    d = ImageDraw.Draw(img)
    # 왼쪽: 브랜드, 분야 칩, 주제어, 날짜
    x = 80 * S
    d.text((x, 92 * S), langs.get(lang)["site"], font=font("SemiBold", 30), fill=SUB)
    chip = font("SemiBold", 26)
    cw = d.textlength(label, font=chip)
    d.rounded_rectangle((x, 230 * S, x + cw + 36 * S, 280 * S), 12 * S, fill=soft)
    d.text((x + 18 * S, 255 * S), label, font=chip, fill=color, anchor="lm")
    d.text((x, 300 * S), topic, font=fit(d, topic, "ExtraBold", 104, 500 * S), fill=INK)
    d.text((x, 470 * S), f"{date.month}월 {date.day}일 {DAYS[date.weekday()]}요일", font=font("SemiBold", 32), fill=SUB)
    d.rounded_rectangle((x, 520 * S, x + 64 * S, 528 * S), 4 * S, fill=color)

    img.convert("RGB").resize((W // S, H // S), Image.LANCZOS).save(out, optimize=True)
    return out


if __name__ == "__main__":
    args, pic = sys.argv[1:], None
    if "--photo" in args:  # 이미 만든 사진으로 다시 합성(API 를 부르지 않는다)
        i = args.index("--photo"); pic = Image.open(args[i + 1]).convert("RGB"); del args[i:i + 2]
    print(build(args[0], args[1], args[2] if len(args) > 2 else None, pic))
