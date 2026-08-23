#!/usr/bin/env python3
"""Instagram / Threads の長期トークンを延長し、GitHub Secrets に書き戻す。

どちらのトークンも有効期限は約60日。更新するたびに60日先へ延びるので、
週に一度これを回しておけば人が触る必要がなくなる。

  python3 refresh_tokens.py --dry   # 延長だけして書き戻さない
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request

REPO = os.environ.get("TARGET_REPO", "keinobuoka/death-countdown-x-bot")

TARGETS = [
    {
        "name": "Instagram",
        "url": "https://graph.instagram.com/refresh_access_token",
        "grant": "ig_refresh_token",
        "secret": "IG_ACCESS_TOKEN",
    },
    {
        "name": "Threads",
        "url": "https://graph.threads.net/refresh_access_token",
        "grant": "th_refresh_token",
        "secret": "THREADS_ACCESS_TOKEN",
    },
]


def refresh(url: str, grant: str, token: str) -> dict:
    q = urllib.parse.urlencode({"grant_type": grant, "access_token": token})
    with urllib.request.urlopen(f"{url}?{q}", timeout=60) as r:
        return json.loads(r.read().decode())


def store(secret: str, value: str) -> None:
    subprocess.run(
        ["gh", "secret", "set", secret, "-R", REPO, "--body", value],
        check=True,
    )


def main() -> None:
    dry = "--dry" in sys.argv
    failed = []

    for t in TARGETS:
        current = os.environ.get(t["secret"])
        if not current:
            print(f"{t['name']}: トークンが環境にないので飛ばします")
            failed.append(t["name"])
            continue
        try:
            res = refresh(t["url"], t["grant"], current)
            new_token = res["access_token"]
            days = int(res.get("expires_in", 0)) // 86400
            print(f"{t['name']}: 延長しました（あと約{days}日）")
            if not dry:
                store(t["secret"], new_token)
                print(f"{t['name']}: Secrets を更新しました")
        except Exception as e:  # noqa: BLE001
            print(f"{t['name']}: 延長に失敗しました: {e}")
            failed.append(t["name"])

    if failed:
        sys.exit(f"failed: {', '.join(failed)}")


if __name__ == "__main__":
    main()
