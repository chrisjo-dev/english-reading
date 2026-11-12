"""GitHub Pages 에 올릴 파일만 허용 목록으로 골라 _site/ 에 복사한다(Actions 배포용 artifact).

사용: python3 tools/prepare_site.py              # 저장소 루트 -> _site/
      python3 tools/prepare_site.py --out /tmp/s

허용 목록에 없는 것(content/, pool/, tools/, tests/, landing/, docs/, .github/ 등)은 사이트에 올라가지 않는다.
언어 폴더는 langs.LANGS 에서 읽으므로 새 언어를 더해도 여기를 고치지 않아도 된다.
"""
import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import langs  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# 없으면 배포를 멈춘다(첫 화면과 도메인이 없으면 사이트가 깨진다)
REQUIRED = ["index.html", "CNAME"]
# 있으면 복사한다
FILES = [
    "404.html", ".nojekyll", "latest.json", "sitemap.xml", "robots.txt", "ads.txt", "llms.txt", "rss.xml",
    "favicon.ico", "icon.svg", "icon.png", "icon-32.png", "icon-192.png", "icon-512.png", "apple-icon.png",
]
DIRS = ["_next", "assets", "lily", "listen"]


def dirs():
    return DIRS + list(langs.LANGS)


def prepare(root=ROOT, out=None):
    root = Path(root)
    out = Path(out) if out else root / "_site"
    missing = [f for f in REQUIRED if not (root / f).is_file()]
    if missing:
        raise SystemExit(f"필수 파일 없음: {', '.join(missing)}")
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for f in REQUIRED + FILES:
        if (root / f).is_file():
            shutil.copy2(root / f, out / f)
    for d in dirs():
        if (root / d).is_dir():
            # 파일을 실제로 복사한다(upload-pages-artifact 는 링크를 받지 않는다)
            shutil.copytree(root / d, out / d, ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    out = prepare(out=ap.parse_args().out)
    files = [p for p in out.rglob("*") if p.is_file()]
    size = sum(p.stat().st_size for p in files)
    print(f"{out}: 파일 {len(files)}개, {size / 1e6:.1f}MB")


if __name__ == "__main__":
    main()
