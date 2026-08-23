#!/usr/bin/env python3
"""その回の投稿に使うカード画像を cards/ に作る。

  python3 make_card.py morning   -> cards/YYYYMMDD.png
  python3 make_card.py evening   -> cards/YYYYMMDD-e.png
"""
import datetime
import sys

import bot
import card
import social

JST = datetime.timezone(datetime.timedelta(hours=9))


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "morning"
    data = bot.load_data()
    offset = bot.daily_index(97)
    stamp = datetime.datetime.now(JST).strftime("%Y%m%d")

    if mode == "morning":
        q = bot.today_quote(data)
        path = f"cards/{stamp}.png"
    else:
        _, q = social.build_evening(data, "instagram", offset)
        path = f"cards/{stamp}-e.png"

    card.build(q, path)
    print("card:", path)


if __name__ == "__main__":
    main()
