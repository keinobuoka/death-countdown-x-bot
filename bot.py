#!/usr/bin/env python3
"""死ぬまでカウントダウン X自動投稿ボット。

朝: アプリと同じ「今日の名言」(日替わりロジックをアプリと同期)
夜: Tips とアプリ紹介(ストアリンク付き)を交互に。日曜夜はウィジェット推し。

使い方:
  python3 bot.py morning          # 朝の名言を投稿
  python3 bot.py evening          # 夜の投稿
  python3 bot.py morning --dry    # 投稿せず本文だけ表示
"""
import json
import os
import sys
import datetime

STORE_URL = "https://play.google.com/store/apps/details?id=com.deathcountdown.app"
JST = datetime.timezone(datetime.timedelta(hours=9))


def weighted_len(text: str) -> int:
    """Xの重み付き文字数。CJK等は2、半角は1、URLは23固定。"""
    total = 0
    for token in text.split():
        if token.startswith("http://") or token.startswith("https://"):
            total += 23 + 1
            continue
        for ch in token:
            total += 2 if ord(ch) > 0x2000 else 1
        total += 1
    return total


def load_data():
    with open(os.path.join(os.path.dirname(__file__), "quotes.json"), encoding="utf-8") as f:
        return json.load(f)


def daily_index(n: int, offset: int = 0) -> int:
    """アプリの dailyQuote() と同じ: (dayOfYear + year*7) % n"""
    now = datetime.datetime.now(JST)
    day_of_year = now.timetuple().tm_yday
    return (day_of_year + now.year * 7 + offset) % n


def interleaved(data):
    """アプリと同じ並び: 名言6個ごとにTipsを1個挟む。"""
    quotes, tips = data["quotes"], data["tips"]
    out, ti = [], 0
    for i, q in enumerate(quotes):
        out.append(q)
        if (i + 1) % 6 == 0 and ti < len(tips):
            out.append(tips[ti])
            ti += 1
    while ti < len(tips):
        out.append(tips[ti])
        ti += 1
    return out


def author_line(q) -> str:
    if q["tip"] or not q["author_ja"]:
        return ""
    t = f"（{q['title_ja']}）" if q["title_ja"] else ""
    return f"— {q['author_ja']}{t}"


def build_morning(data) -> str:
    pool = interleaved(data)
    q = pool[daily_index(len(pool))]
    lines = [f"「{q['ja']}」"]
    al = author_line(q)
    if al:
        lines.append(al)
    body = "\n".join(lines)
    # 英語原文は文字数に余裕がある時だけ併記
    if not q["tip"] and not q["ja_original"]:
        with_en = body + "\n\n" + q["en"]
        if weighted_len(with_en + "\n\n#メメントモリ #名言") <= 275:
            body = with_en
    body += "\n\n#メメントモリ #名言"
    return body


TIP_CLOSERS = [
    "ホーム画面に残り日数を置くと、毎日が少し変わる ⏳",
    "あなたの残り時間、何日か知っていますか ⏳",
    "時間は最も公平な資源。全員に1日24時間 ⏳",
]

PROMO_BODIES = [
    "人生の残り日数を、ホーム画面のウィジェットで毎日。\n偉人の名言（出典検証済み）が日替わりで届きます。",
    "生年月日を入れるだけで、残り時間が「日数」で見える。\n完全無料・広告なし・オフライン。",
    "「ウィジェットが、本体。」\n残り日数・残り時間・経過率・今日の名言をホーム画面に常時表示。",
]


def build_evening(data) -> str:
    now = datetime.datetime.now(JST)
    if now.weekday() == 6 or now.toordinal() % 2 == 0:
        # 日曜 or 偶数日: アプリ紹介(リンク付き)
        body = PROMO_BODIES[daily_index(len(PROMO_BODIES))]
        return f"{body}\n\n{STORE_URL}\n\n#メメントモリ #死ぬまでカウントダウン"
    # 奇数日: Tips
    tips = data["tips"]
    tip = tips[daily_index(len(tips), offset=3)]
    closer = TIP_CLOSERS[daily_index(len(TIP_CLOSERS), offset=1)]
    return f"{tip['ja']}\n\n{closer}\n\n#メメントモリ"


def post(text: str):
    import tweepy

    client = tweepy.Client(
        consumer_key=os.environ["X_API_KEY"],
        consumer_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_SECRET"],
    )
    resp = client.create_tweet(text=text)
    print("posted:", resp.data.get("id"))


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "morning"
    dry = "--dry" in sys.argv
    data = load_data()
    text = build_morning(data) if mode == "morning" else build_evening(data)
    print("---- post body ----")
    print(text)
    print(f"---- weighted length: {weighted_len(text)}/280 ----")
    if not dry:
        post(text)


if __name__ == "__main__":
    main()
