import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    bot_token: str
    database_path: str = "fitness_rpg.sqlite3"
    ai_enabled: bool = False
    ai_provider: str = "openai"
    ai_api_key: str | None = None
    ai_base_url: str = "https://api.openai.com/v1"
    ai_model: str = "gpt-5.4-mini"
    ai_timeout_seconds: int = 35

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv(encoding="utf-8-sig")
        bot_token = os.getenv("BOT_TOKEN")
        if not bot_token:
            raise RuntimeError("BOT_TOKEN is missing. Create .env from .env.example.")

        return cls(
            bot_token=bot_token,
            database_path=os.getenv("DATABASE_PATH", "fitness_rpg.sqlite3"),
            ai_enabled=os.getenv("AI_ENABLED", "false").lower() in {"1", "true", "yes", "on"},
            ai_provider=os.getenv("AI_PROVIDER", "openai").strip().lower(),
            ai_api_key=os.getenv("AI_API_KEY"),
            ai_base_url=os.getenv("AI_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
            ai_model=os.getenv("AI_MODEL", "gpt-5.4-mini").strip(),
            ai_timeout_seconds=int(os.getenv("AI_TIMEOUT_SECONDS", "35")),
        )
