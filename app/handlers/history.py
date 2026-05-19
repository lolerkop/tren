from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.db.database import Database
from app.db.repositories import ProgressRepository, UserRepository
from app.keyboards import history_keyboard
from app.utils.formatters import format_history
from app.utils.messages import transition


def router(db: Database) -> Router:
    history_router = Router()
    users = UserRepository(db)
    progress = ProgressRepository(db)

    @history_router.message(Command("history"))
    async def history_command(message: Message) -> None:
        user = users.get_by_telegram_id(message.from_user.id)
        if not user:
            await message.answer("Сначала пройди регистрацию через /start.")
            return
        await message.answer(
            format_history(user, progress.summary_for_user(user.id), progress.recent_for_user(user.id)),
            reply_markup=history_keyboard(),
        )

    @history_router.callback_query(F.data == "menu:history")
    async def history_callback(callback: CallbackQuery) -> None:
        user = users.get_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("Сначала пройди регистрацию через /start.", show_alert=True)
            return
        await transition(
            callback,
            format_history(user, progress.summary_for_user(user.id), progress.recent_for_user(user.id)),
            history_keyboard(),
        )
        await callback.answer()

    return history_router
