#!/usr/bin/env python3
"""Instagram / Threads への自動投稿。

朝(7:00 JST): アプリと同じ「今日の名言」をカード画像つきで
夜(21:00 JST): 問いかけ / Tips / アプリ紹介（画像は別カード）

画像は GitHub Pages に置いた URL を使う（両APIとも公開URLしか受け付けないため）。

  python3 social.py --dry                    # 投稿せず本文だけ確認
  python3 social.py --mode evening           # 夜の投稿
  python3 social.py --only threads           # 片方だけ
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


# ---------------------------------------------------------------- ハッシュタグ
# Instagram は大・中・小の規模を混ぜたほうが埋もれにくい。毎日同じ並びだと
# スパム扱いされやすいので、日付で回して組み合わせを変える。
IG_TAGS_CORE = ["#メメントモリ", "#死ぬまでカウントダウン"]
IG_TAGS_BIG = ["#名言", "#名言集", "#格言", "#言葉の力", "#人生", "#モチベーション"]
IG_TAGS_MID = [
    "#今日の名言", "#心に響く言葉", "#生き方", "#自己啓発", "#哲学",
    "#マインドセット", "#時間の使い方", "#死生観", "#人生の名言",
]
IG_TAGS_SMALL = [
    "#ストア派", "#偉人の言葉", "#一日一言", "#毎日投稿", "#カウントダウン",
    "#残りの人生", "#人生哲学", "#言葉の贈り物", "#日々の気づき",
]
# Threads はタグが1件しか効かない仕様なので、1つだけ回す
TH_TAGS = ["#メメントモリ", "#名言", "#人生", "#死生観", "#哲学", "#時間"]


def _rotate(pool: list[str], take: int, offset: int) -> list[str]:
    n = len(pool)
    return [pool[(offset + i) % n] for i in range(min(take, n))]


def ig_hashtags(offset: int) -> str:
    tags = (
        IG_TAGS_CORE
        + _rotate(IG_TAGS_BIG, 3, offset)
        + _rotate(IG_TAGS_MID, 4, offset)
        + _rotate(IG_TAGS_SMALL, 4, offset)
    )
    return " ".join(tags)


# ---------------------------------------------------------------- 投稿API
def _post(url: str, params: dict) -> dict:
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def days_left_of_year() -> int:
    now = datetime.datetime.now(JST).date()
    return (datetime.date(now.year, 12, 31) - now).days


def author_line(q: dict) -> str:
    if q.get("tip") or not q.get("author_ja"):
        return ""
    t = f"（{q['title_ja']}）" if q.get("title_ja") else ""
    return f"— {q['author_ja']}{t}"


# ---------------------------------------------------------------- 本文
def build_morning(q: dict, platform: str, offset: int) -> str:
    year = datetime.datetime.now(JST).year
    head = f"{year}年も残り{days_left_of_year()}日。"
    quote = q["ja"] if q.get("tip") else f"「{q['ja']}」"
    body = f"{head}\n\n{quote}"
    al = author_line(q)
    if al:
        body += f"\n{al}"

    if platform == "instagram":
        return (
            f"{body}\n\n"
            "あなたに残された日数は、プロフィールのアプリで数えられます。\n\n"
            f"{ig_hashtags(offset)}"
        )
    return f"{body}\n\nあなたは今年、あと何日残っていると思っていましたか？\n\n{TH_TAGS[offset % len(TH_TAGS)]}"


def evening_source(data: dict, offset: int) -> tuple[str, str]:
    """(カードに載せる文, 投稿の締め) を返す。"""
    import bot

    now = datetime.datetime.now(JST)
    if now.weekday() in (1, 4):          # 火・金は問いかけ（コメントを取りにいく）
        text = bot.QUESTIONS[offset % len(bot.QUESTIONS)]
        return text, "あなたの答えをコメントで教えてください。"
    if now.weekday() == 6:               # 日曜はアプリ紹介
        text = bot.PROMO_BODIES[offset % len(bot.PROMO_BODIES)].replace("\n", " ")
        return text, "アプリはプロフィールのリンクから（無料・広告なし）。"
    tips = data["tips"]                  # 平日はTips
    tip = tips[offset % len(tips)]
    return tip["ja"], bot.TIP_CLOSERS[offset % len(bot.TIP_CLOSERS)]


def build_evening(data: dict, platform: str, offset: int) -> tuple[str, dict]:
    text, closer = evening_source(data, offset)
    card_quote = {"ja": text, "tip": True, "author_ja": "", "title_ja": "", "en": ""}
    body = f"{text}\n\n{closer}"
    if platform == "instagram":
        return f"{body}\n\n{ig_hashtags(offset + 5)}", card_quote
    return f"{body}\n\n{TH_TAGS[(offset + 3) % len(TH_TAGS)]}", card_quote


# ---------------------------------------------------------------- 送信
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


def arg(name: str, default: str = "") -> str:
    if name in sys.argv:
        i = sys.argv.index(name) + 1
        if i < len(sys.argv):
            return sys.argv[i]
    return default


def main() -> None:
    dry = "--dry" in sys.argv
    mode = arg("--mode", "morning")
    only = arg("--only") or None

    import bot
    data = bot.load_data()
    q = bot.today_quote(data)
    offset = bot.daily_index(97)  # 日付で回すための共通オフセット

    stamp = datetime.datetime.now(JST).strftime("%Y%m%d")
    suffix = "" if mode == "morning" else "-e"
    image_url = f"{PAGES_BASE}/cards/{stamp}{suffix}.png"

    failed = []
    for platform in ("instagram", "threads"):
        if only and only != platform:
            continue
        if mode == "morning":
            caption = build_morning(q, platform, offset)
        else:
            caption, _ = build_evening(data, platform, offset)
        print(f"---- {platform} / {mode} ----")
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
            failed.append(platform)

    if failed:
        sys.exit(f"failed: {', '.join(failed)}")


if __name__ == "__main__":
    main()
