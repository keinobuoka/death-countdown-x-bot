#!/usr/bin/env python3
"""Instagram / Threads への自動投稿。

画像は GitHub Pages に置いた URL を使う（両APIとも公開URLしか受け付けないため）。

  python3 social.py --dry           # 投稿せず本文だけ確認
  python3 social.py                 # Instagram と Threads に投稿
  python3 social.py --only threads  # 片方だけ
"""
from __future__ import annotations

import datetime
import json
import os
import sys
import time
import urllib.parse
import urllib.request

JST = datetime.timezone(datetime.timedelta(hours=9))
STORE_URL = "https://play.google.com/store/apps/details?id=com.deathcountdown.app"
# GitHub Pages に置いた当日のカード画像
PAGES_BASE = os.environ.get("PAGES_BASE", "https://keinobuoka.github.io/death-countdown-x-bot")
# Instagram ログイン方式（Facebookページを経由しない）のエンドポイント
IG_API = "https://graph.instagram.com/v21.0"
TH_API = "https://graph.threads.net/v1.0"


def _post(url: str, params: dict) -> dict:
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def days_left_of_year() -> int:
    now = datetime.datetime.now(JST).date()
    return (datetime.date(now.year, 12, 31) - now).days


def build_caption(q: dict, platform: str) -> str:
    year = datetime.datetime.now(JST).year
    author = ""
    if q.get("author_ja"):
        t = f"（{q['title_ja']}）" if q.get("title_ja") else ""
        author = f"— {q['author_ja']}{t}"

    head = f"{year}年も残り{days_left_of_year()}日。"
    body = f"{head}\n\n「{q['ja']}」\n{author}"

    if platform == "instagram":
        tags = "#メメントモリ #名言 #死生観 #人生 #時間 #哲学 #ストア派 #自己啓発 #毎日投稿 #カウントダウン"
        return f"{body}\n\nあなたに残された日数は、プロフィールのアプリで数えられます ⏳\n\n{tags}"
    # Threads は会話が伸びるので問いかけで締める
    return f"{body}\n\nあなたは今年、あと何日残っていると思っていましたか？\n\n#メメントモリ"


def post_instagram(image_url: str, caption: str) -> str:
    user_id = os.environ["IG_USER_ID"]
    token = os.environ["IG_ACCESS_TOKEN"]
    created = _post(f"{IG_API}/{user_id}/media", {
        "image_url": image_url, "caption": caption, "access_token": token,
    })
    time.sleep(5)  # コンテナの処理待ち
    published = _post(f"{IG_API}/{user_id}/media_publish", {
        "creation_id": created["id"], "access_token": token,
    })
    return published.get("id", "")


def post_threads(image_url: str, text: str) -> str:
    user_id = os.environ["THREADS_USER_ID"]
    token = os.environ["THREADS_ACCESS_TOKEN"]
    created = _post(f"{TH_API}/{user_id}/threads", {
        "media_type": "IMAGE", "image_url": image_url, "text": text, "access_token": token,
    })
    time.sleep(5)
    published = _post(f"{TH_API}/{user_id}/threads_publish", {
        "creation_id": created["id"], "access_token": token,
    })
    return published.get("id", "")


def main() -> None:
    dry = "--dry" in sys.argv
    only = None
    if "--only" in sys.argv:
        only = sys.argv[sys.argv.index("--only") + 1]

    import bot
    data = bot.load_data()
    q = bot.today_quote(data)

    stamp = datetime.datetime.now(JST).strftime("%Y%m%d")
    image_url = f"{PAGES_BASE}/cards/{stamp}.png"

    for platform in ("instagram", "threads"):
        if only and only != platform:
            continue
        caption = build_caption(q, platform)
        print(f"---- {platform} ----")
        print(caption)
        print(f"image: {image_url}")
        if dry:
            continue
        try:
            if platform == "instagram":
                print("posted:", post_instagram(image_url, caption))
            else:
                print("posted:", post_threads(image_url, caption))
        except Exception as e:  # noqa: BLE001
            print(f"{platform} post failed:", e)


if __name__ == "__main__":
    main()
