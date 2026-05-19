from aiogram import Dispatcher

from app.config import Settings
from app.db.database import Database
from app.handlers.ai_status import router as ai_status_router
from app.handlers.history import router as history_router
from app.handlers.profile import router as profile_router
from app.handlers.quest import create_quest_router
from app.handlers.random_events import router as random_events_router
from app.handlers.settings import router as settings_router
from app.handlers.start import create_start_router


def register_handlers(dp: Dispatcher, db: Database, settings: Settings) -> None:
    dp.include_router(create_start_router(db))
    dp.include_router(create_quest_router(db, settings))
    dp.include_router(profile_router(db))
    dp.include_router(history_router(db))
    dp.include_router(ai_status_router(settings))
    dp.include_router(random_events_router(db))
    dp.include_router(settings_router(db))
