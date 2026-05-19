import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from app.config import Settings
from app.db.database import Database
from app.handlers import register_handlers
from app.logic.random_events import RandomEventService
from app.logic.reminders import ReminderService


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    settings = Settings.from_env()
    db = Database(settings.database_path)
    db.connect()
    db.init_schema()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    register_handlers(dp, db, settings)
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Регистрация и старт"),
            BotCommand(command="menu", description="Главное меню"),
            BotCommand(command="quest", description="Guild Board на сегодня"),
            BotCommand(command="profile", description="Профиль и статы"),
            BotCommand(command="history", description="Журнал прогресса"),
            BotCommand(command="settings", description="Настройки программы"),
            BotCommand(command="ai", description="Проверка LM Studio"),
        ]
    )

    reminder_service = ReminderService(bot=bot, db=db)
    reminder_task = asyncio.create_task(reminder_service.run_forever())
    random_event_service = RandomEventService(bot=bot, db=db)
    random_event_task = asyncio.create_task(random_event_service.run_forever())

    try:
        await dp.start_polling(bot)
    finally:
        for task in (reminder_task, random_event_task):
            task.cancel()
        await asyncio.gather(reminder_task, random_event_task, return_exceptions=True)
        await bot.session.close()
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
