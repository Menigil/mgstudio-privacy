from __future__ import annotations

import os
from typing import Optional

import requests

from .config import TelegramConfig


def send_telegram_message(text: str, token: Optional[str] = None, chat_id: Optional[str] = None) -> bool:
    cfg = TelegramConfig(
        bot_token=token if token is not None else TelegramConfig().bot_token,
        chat_id=chat_id if chat_id is not None else TelegramConfig().chat_id,
    )

    if not cfg.bot_token or not cfg.chat_id:
        # Missing configuration; we surface this as a soft failure to keep CLI usable
        print("[telegram] Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID; skipping send.")
        return False

    url = f"https://api.telegram.org/bot{cfg.bot_token}/sendMessage"
    payload = {"chat_id": cfg.chat_id, "text": text}

    try:
        resp = requests.post(url, json=payload, timeout=15)
        ok = resp.ok and resp.json().get("ok", False)
        if not ok:
            print(f"[telegram] Failed to send: {resp.text}")
        return ok
    except Exception as exc:  # noqa: BLE001
        print(f"[telegram] Exception sending message: {exc}")
        return False
