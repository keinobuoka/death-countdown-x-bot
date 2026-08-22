#!/usr/bin/env python3
"""名言カード画像を生成する。アプリと同じ黒背景・白文字の世界観。"""
from __future__ import annotations

import datetime
import os
from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 675          # X のタイムラインで最も大きく出る 16:9
JST = datetime.timezone(datetime.timedelta(hours=9))

# GitHub Actions (fonts-noto-cjk) と mac の両対応
FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Light.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
]
MONO_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/HelveticaNeue.ttc",
]


def _font(paths: list[str], size: int, index: int = 0) -> ImageFont.FreeTypeFont:
    for p in paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size, index=index)
            except Exception:
                try:
                    return ImageFont.truetype(p, size)
                except Exception:
                    continue
    return ImageFont.load_default()


def _wrap(draw, text: str, font, max_w: int) -> list[str]:
    lines, line = [], ""
    for ch in text:
        if ch == "\n":
            lines.append(line)
            line = ""
            continue
        if draw.textlength(line + ch, font=font) > max_w:
            lines.append(line)
            line = ch
        else:
            line += ch
    if line:
        lines.append(line)
    return lines


def days_left_of_year() -> int:
    now = datetime.datetime.now(JST).date()
    return (datetime.date(now.year, 12, 31) - now).days


def build(quote: dict, out_path: str) -> str:
    img = Image.new("RGB", (W, H), "#000000")
    d = ImageDraw.Draw(img)

    ja = quote["ja"]
    size = 58 if len(ja) <= 28 else (48 if len(ja) <= 44 else 40)
    f_quote = _font(FONT_CANDIDATES, size)
    f_author = _font(FONT_CANDIDATES, 30)
    f_en = _font(MONO_CANDIDATES, 24)
    f_foot = _font(FONT_CANDIDATES, 22)

    max_w = W - 200
    lines = _wrap(d, f"「{ja}」" if not quote.get("tip") else ja, f_quote, max_w)
    line_h = int(size * 1.65)

    en_lines: list[str] = []
    if quote.get("en") and not quote.get("ja_original") and not quote.get("tip") and len(lines) <= 3:
        en_lines = _wrap(d, quote["en"], f_en, max_w)[:2]

    author = ""
    if quote.get("author_ja") and not quote.get("tip"):
        t = f"（{quote['title_ja']}）" if quote.get("title_ja") else ""
        author = f"— {quote['author_ja']}{t}"

    block_h = len(lines) * line_h + (len(en_lines) * 34 + 24 if en_lines else 0) + (54 if author else 0)
    y = (H - block_h) // 2 - 20

    for ln in lines:
        w = d.textlength(ln, font=f_quote)
        d.text(((W - w) / 2, y), ln, font=f_quote, fill="#F2F2F2")
        y += line_h

    if en_lines:
        y += 24
        for ln in en_lines:
            w = d.textlength(ln, font=f_en)
            d.text(((W - w) / 2, y), ln, font=f_en, fill="#8A8A8A")
            y += 34

    if author:
        y += 24
        w = d.textlength(author, font=f_author)
        d.text(((W - w) / 2, y), author, font=f_author, fill="#AFAFAF")

    # フッター: 今年の残り日数（自分ごと化のフック）
    foot = f"{datetime.datetime.now(JST).year}年も残り {days_left_of_year()} 日　//　死ぬまでカウントダウン"
    fw = d.textlength(foot, font=f_foot)
    d.text(((W - fw) / 2, H - 62), foot, font=f_foot, fill="#5A5A5A")

    img.save(out_path)
    return out_path
