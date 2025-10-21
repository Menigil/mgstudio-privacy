from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from a local .env file if present
load_dotenv()


@dataclass(frozen=True)
class TelegramConfig:
    bot_token: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id: Optional[str] = os.getenv("TELEGRAM_CHAT_ID")


def get_env_var(key: str, default: Optional[str] = None) -> Optional[str]:
    """Fetch an environment variable with an optional default."""
    return os.getenv(key, default)
