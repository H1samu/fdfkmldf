import html
import json
import os
import sys
from pathlib import Path

import requests

API_URL = "https://www.gamerpower.com/api/giveaways"
SEEN_FILE = Path("seen.json")
MAX_SEEN = 500

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHANNEL_ID = os.environ["CHANNEL_ID"]


def load_seen() -> list[int]:
    if SEEN_FILE.exists():
        return json.loads(SEEN_FILE.read_text(encoding="utf-8"))
    return []


def save_seen(seen: list[int]) -> None:
    SEEN_FILE.write_text(json.dumps(seen[-MAX_SEEN:]), encoding="utf-8")


def fetch_giveaways() -> list[dict]:
    r = requests.get(
        API_URL,
        params={"platform": "steam", "type": "game"},
        timeout=30,
    )
    # API возвращает 201 и пустой ответ, если раздач нет
    if r.status_code != 200 or not r.text.strip():
        return []
    data = r.json()
    return data if isinstance(data, list) else []


def build_message(g: dict) -> str:
    title = html.escape(g["title"])
    worth = html.escape(g.get("worth", "N/A"))
    end = html.escape(g.get("end_date", "N/A"))
    url = g["open_giveaway_url"]
    return (
        f"🎁 <b>{title}</b>\n"
        f"Обычная цена: {worth}\n"
        f"Действует до: {end}\n\n"
        f'<a href="{url}">Забрать в Steam</a>'
    )


def send(text: str) -> None:
    r = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={
            "chat_id": CHANNEL_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        },
        timeout=30,
    )
    r.raise_for_status()


def main() -> None:
    seen = load_seen()
    giveaways = fetch_giveaways()

    for g in giveaways:
        if g.get("status") != "Active" or g.get("type") != "Game":
            continue
        if g["id"] in seen:
            continue
        try:
            send(build_message(g))
        except requests.RequestException as e:
            print(f"Не удалось отправить {g['id']}: {e}", file=sys.stderr)
            continue
        seen.append(g["id"])
        print(f"Отправлено: {g['title']}")

    save_seen(seen)


if __name__ == "__main__":
    main()
