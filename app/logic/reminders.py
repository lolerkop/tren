import asyncio
from datetime import date

from aiogram import Bot

from app.db.database import Database
from app.db.repositories import UserRepository


class ReminderService:
    def __init__(self, bot: Bot, db: Database) -> None:
        self.bot = bot
        self.users = UserRepository(db)

    async def run_forever(self) -> None:
        # Lightweight reminder loop. It only nudges users who already generated today's quests.
        await asyncio.sleep(10)
        while True:
            await self.send_reminders()
            await asyncio.sleep(60 * 60 * 4)

    async def send_reminders(self) -> None:
        today = date.today()
        for user in self.users.users_for_reminders(today):
            if user.last_reminder_date == today and user.reminders_sent_today >= 3:
                continue
            await self.bot.send_message(
                chat_id=user.telegram_id,
                text=(
                    "📜 <b>Guild Board</b>\n\n"
                    "Твои активные квесты все еще ждут отчета.\n"
                    "Открой /quest, заверши подходы и забери XP."
                ),
            )
            self.users.register_reminder(user.id, today)
