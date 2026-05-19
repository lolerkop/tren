from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.db.database import Database
from app.db.repositories import RandomEventRepository
from app.keyboards import random_event_detail_keyboard
from app.logic.random_events import RandomEventService, format_random_event, format_random_reward
from app.utils.messages import transition


def router(db: Database) -> Router:
    random_router = Router()
    events = RandomEventRepository(db)

    @random_router.callback_query(F.data.startswith("random:view:"))
    async def view_random_event(callback: CallbackQuery) -> None:
        event_id = int(callback.data.split(":")[-1])
        event = events.get(event_id)
        if not event or event["telegram_id"] != callback.from_user.id:
            await callback.answer("Случайное задание не найдено.", show_alert=True)
            return

        await transition(callback, format_random_event(event), random_event_detail_keyboard(event))
        await callback.answer()

    @random_router.callback_query(F.data == "random:already_done")
    async def random_already_done(callback: CallbackQuery) -> None:
        await callback.answer("Награда за это случайное задание уже получена.", show_alert=True)

    @random_router.callback_query(F.data.startswith("random:done:"))
    async def complete_random_event(callback: CallbackQuery) -> None:
        service = RandomEventService(bot=callback.bot, db=db)
        event_id = int(callback.data.split(":")[-1])
        result = service.complete_event(event_id, callback.from_user.id)
        if result is None:
            await callback.answer("Задание уже закрыто или недоступно.", show_alert=True)
            return

        event, user, xp_gained = result
        await transition(callback, format_random_reward(event, user, xp_gained), random_event_detail_keyboard({**event, "status": "done"}))
        await callback.answer("XP начислен!")

    return random_router
