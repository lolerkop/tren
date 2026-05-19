from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.db.database import Database
from app.db.repositories import UserRepository
from app.keyboards import profile_keyboard
from app.utils.formatters import format_profile
from app.utils.messages import transition


def router(db: Database) -> Router:
    profile_router = Router()
    users = UserRepository(db)

    @profile_router.message(Command("profile"))
    async def profile(message: Message) -> None:
        user = users.get_by_telegram_id(message.from_user.id)
        if not user:
            await message.answer("Сначала пройди регистрацию через /start.")
            return
        await message.answer(format_profile(user), reply_markup=profile_keyboard())

    @profile_router.callback_query(F.data.in_({"profile", "menu:profile"}))
    async def profile_callback(callback: CallbackQuery) -> None:
        user = users.get_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.message.answer("Сначала пройди регистрацию через /start.")
            await callback.answer()
            return
        await transition(callback, format_profile(user), profile_keyboard())
        await callback.answer()

    return profile_router
