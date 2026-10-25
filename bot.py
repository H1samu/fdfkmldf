import html
import json
import os
import sys
from pathlib import Path

from urllib.parse import urlparse

import requests

# Запасной фильтр по тексту, если не удалось определить конечный сайт
BLOCK_WORDS = ("alienware", "indiegala", "fanatical", "gleam.io", "reddit")

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


def is_steam_native(g: dict) -> bool:
    """True, если раздача забирается прямо в Steam, а не на стороннем сайте."""
    try:
        r = requests.get(
            g["open_giveaway_url"],
            timeout=20,
            allow_redirects=True,
            stream=True,
        )
        host = urlparse(r.url).netloc.lower()
        r.close()
        if host.endswith("steampowered.com") or host.endswith("steamcommunity.com"):
            return True
        if not host.endswith("gamerpower.com"):
            return False  # привело на другой сайт (Alienware и т.п.)
    except requests.RequestException:
        pass
    # Редирект не удалось определить: проверяем по тексту
    text = " ".join(
        str(g.get(k, "")) for k in ("title", "description", "instructions")
    ).lower()
    return not any(w in text for w in BLOCK_WORDS)


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
        if not is_steam_native(g):
            seen.append(g["id"])  # запоминаем, чтобы не проверять снова
            print(f"Пропущено (не Steam): {g['title']}")
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
