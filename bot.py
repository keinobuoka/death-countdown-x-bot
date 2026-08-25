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


def today_quote(data):
    pool = interleaved(data)
    return pool[daily_index(len(pool))]


def days_left_of_year() -> int:
    now = datetime.datetime.now(JST).date()
    return (datetime.date(now.year, 12, 31) - now).days


def build_morning(data) -> str:
    """画像に名言を載せるので、本文は「自分ごと化」のフックに徹する。"""
    q = today_quote(data)
    year = datetime.datetime.now(JST).year
    hook = f"{year}年も残り{days_left_of_year()}日。"
    lines = [hook, ""]
    lines.append(f"【{TIP_LABEL}】\n{q['ja']}" if q["tip"] else f"「{q['ja']}」")
    al = author_line(q)
    if al:
        lines.append(al)
    body = "\n".join(lines)
    body += "\n\n#メメントモリ"
    # 長すぎる場合は名言を画像に任せ、本文は短く
    if weighted_len(body) > 270:
        body = f"{hook}\n\n{al}\n\n#メメントモリ" if al else f"{hook}\n\n#メメントモリ"
    return body


TIP_LABEL = "今日のTips"

TIP_CLOSERS = [
    "ホーム画面に残り日数があると、一日の見え方が少し変わる。",
    "自分に残された日数は、数えれば分かる。",
    "時間は最も公平な資源。全員に一日24時間。",
]

# 反応を取りにいく問いかけ型（リプライが付くとタイムラインに乗りやすい）
QUESTIONS = [
    "残りの人生が1000日だと分かったら、明日いちばんにやることは何ですか。",
    "80年を日数にすると約29,200日。あなたはいま何日目ですか。",
    "今日が人生最後の日だとしたら、今日の予定を変えますか。",
    "10年後の自分から見て、今日は何をしていた日ですか。",
    "1日は86,400秒。今日、意図して使えた秒はどれくらいですか。",
    "やらないまま10年が過ぎたこと。ひとつ挙げるとしたら何ですか。",
    "今週いちばん時間を使ったこと。来年も覚えていますか。",
]

PROMO_BODIES = [
    "人生の残り日数を、ホーム画面のウィジェットに。\n出典を確かめた偉人の名言が、日替わりで一つ。",
    "生年月日を入れるだけ。残り時間が日数で見える。\n無料、広告なし、通信もなし。",
    "ウィジェットが本体。\n残り日数、残り時間、経過率、今日の名言。\nホーム画面に置いたまま。",
]


def build_evening(data) -> str:
    # URL付き投稿は$0.20/件と高いため、リンク付き紹介は日曜のみ。他はTips/問いかけ
    now = datetime.datetime.now(JST)
    if now.weekday() in (1, 4):
        # 火・金: 問いかけ（返信を誘って露出を取る）
        q = QUESTIONS[daily_index(len(QUESTIONS))]
        return f"{q}\n\n#メメントモリ"
    if now.weekday() == 6:
        # 日曜: アプリ紹介(ストアリンク付き)
        body = PROMO_BODIES[daily_index(len(PROMO_BODIES))]
        return f"{body}\n\n{STORE_URL}\n\n#メメントモリ #死ぬまでカウントダウン"
    if now.toordinal() % 2 == 0:
        # 偶数日: アプリ紹介(リンクなし・プロフィールへ誘導)
        body = PROMO_BODIES[daily_index(len(PROMO_BODIES))]
        return f"{body}\n\nアプリはプロフィールのリンクから\n\n#メメントモリ #死ぬまでカウントダウン"
    # 奇数日: Tips
    tips = data["tips"]
    tip = tips[daily_index(len(tips), offset=3)]
    closer = TIP_CLOSERS[daily_index(len(TIP_CLOSERS), offset=1)]
    return f"【{TIP_LABEL}】\n{tip['ja']}\n\n{closer}\n\n#メメントモリ"


def post(text: str, image_path: str | None = None):
    import tweepy

    auth_kwargs = dict(
        consumer_key=os.environ["X_API_KEY"],
        consumer_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_SECRET"],
    )
    client = tweepy.Client(**auth_kwargs)

    media_ids = None
    if image_path and os.path.exists(image_path):
        # 画像アップロードは v1.1 API を使う
        auth = tweepy.OAuth1UserHandler(
            auth_kwargs["consumer_key"], auth_kwargs["consumer_secret"],
            auth_kwargs["access_token"], auth_kwargs["access_token_secret"],
        )
        api = tweepy.API(auth)
        media = api.media_upload(filename=image_path)
        media_ids = [media.media_id_string]

    resp = client.create_tweet(text=text, media_ids=media_ids)
    print("posted:", resp.data.get("id"), "with_image:", bool(media_ids))


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "morning"
    dry = "--dry" in sys.argv
    data = load_data()
    text = build_morning(data) if mode == "morning" else build_evening(data)

    image_path = None
    if mode == "morning":
        try:
            import card
            q = dict(today_quote(data))
            if q.get("tip"):
                q["label"] = TIP_LABEL
            image_path = card.build(q, "/tmp/quote_card.png")
        except Exception as e:  # noqa: BLE001
            print("card generation failed:", e)

    print("---- post body ----")
    print(text)
    print(f"---- weighted length: {weighted_len(text)}/280 ---- image: {image_path}")
    if not dry:
        post(text, image_path)


if __name__ == "__main__":
    main()
