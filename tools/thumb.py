"""날짜 페이지의 주제어와 분야 일러스트로 썸네일(YYYY-MM-DD/thumb.png, 1200x630)을 만든다.

사용: python3 tools/thumb.py 2026-10-12 [분야]
분야: science, tech, society, future, culture, space (생략하면 요일별 기본 분야)
메일 상단, 날짜 페이지 상단, 링크 미리보기(OG)에 같은 이미지를 쓴다.
"""
import datetime as dt
import math
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

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


def build(day, cat=None):
    date = dt.date.fromisoformat(day)
    cat = cat or WEEKDAY[date.weekday()]
    label, color, soft = CATS[cat]
    page = (ROOT / day / "index.html").read_text(encoding="utf-8")
    topic = re.search(r"<h1>.*?<em>(.*?)</em>", page, re.S).group(1).strip()

    img = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    d = ImageDraw.Draw(img)
    # 오른쪽: 분야 색 원 안에 일러스트
    cx, cy = 880 * S, 315 * S
    d.ellipse((cx - 290 * S, cy - 290 * S, cx + 290 * S, cy + 290 * S), fill=soft)
    DRAW[cat](img, d, cx, cy, color)
    d = ImageDraw.Draw(img)
    # 왼쪽: 브랜드, 분야 칩, 주제어, 날짜
    x = 80 * S
    d.text((x, 92 * S), "매일 영어 읽기", font=font("SemiBold", 30), fill=SUB)
    chip = font("SemiBold", 26)
    cw = d.textlength(label, font=chip)
    d.rounded_rectangle((x, 230 * S, x + cw + 36 * S, 280 * S), 12 * S, fill=soft)
    d.text((x + 18 * S, 255 * S), label, font=chip, fill=color, anchor="lm")
    d.text((x, 300 * S), topic, font=fit(d, topic, "ExtraBold", 104, 500 * S), fill=INK)
    d.text((x, 470 * S), f"{date.month}월 {date.day}일 {DAYS[date.weekday()]}요일", font=font("SemiBold", 32), fill=SUB)
    d.rounded_rectangle((x, 520 * S, x + 64 * S, 528 * S), 4 * S, fill=color)

    out = ROOT / day / "thumb.png"
    img.convert("RGB").resize((W // S, H // S), Image.LANCZOS).save(out, optimize=True)
    return out


if __name__ == "__main__":
    print(build(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))
