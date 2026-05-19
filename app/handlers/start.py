from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.db.database import Database
from app.db.repositories import UserRepository
from app.keyboards import back_to_menu_keyboard, main_menu_keyboard
from app.utils.messages import transition


class Registration(StatesGroup):
    pushups = State()
    pullups = State()
    dips = State()
    squats = State()


def create_start_router(db: Database) -> Router:
    router = Router()
    users = UserRepository(db)

    @router.message(CommandStart())
    async def start(message: Message, state: FSMContext) -> None:
        user = users.get_by_telegram_id(message.from_user.id)
        if user:
            await state.clear()
            await message.answer(_menu_text(user.rank), reply_markup=main_menu_keyboard())
            return

        await state.clear()
        await state.set_state(Registration.pushups)
        await message.answer(
            "📜 <b>Guild Board</b>\n\n"
            "Добро пожаловать в гильдию.\n"
            "Начнем стартовый тест: введи максимум отжиманий за один подход."
        )

    @router.message(Command("menu"))
    async def menu(message: Message, state: FSMContext) -> None:
        await state.clear()
        user = users.get_by_telegram_id(message.from_user.id)
        if not user:
            await message.answer("Сначала пройди регистрацию через /start.")
            return
        await message.answer(_menu_text(user.rank), reply_markup=main_menu_keyboard())

    @router.callback_query(F.data == "menu:home")
    async def menu_callback(callback: CallbackQuery, state: FSMContext) -> None:
        await state.clear()
        user = users.get_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.message.answer("Сначала пройди регистрацию через /start.")
            await callback.answer()
            return
        await transition(callback, _menu_text(user.rank), main_menu_keyboard())
        await callback.answer()

    @router.callback_query(F.data == "menu:help")
    async def help_callback(callback: CallbackQuery) -> None:
        await transition(
            callback,
            "❔ <b>Guild Help</b>\n\n"
            "📜 <b>Guild Board</b> — получить задания дня.\n"
            "✅ <b>Сдать квест</b> — ввести реальные повторения и сложность.\n"
            "📈 <b>Profile</b> — посмотреть LVL, rank, XP, силу, выносливость и streak.\n"
            "⚙️ <b>Настройки</b> — включить или выключить упражнения по группам мышц.\n"
            "⚔ <b>Raid Boss</b> появляется по воскресеньям и дает повышенную награду.",
            back_to_menu_keyboard(),
        )
        await callback.answer()

    @router.callback_query(F.data == "menu:rewards")
    async def rewards_callback(callback: CallbackQuery) -> None:
        await transition(
            callback,
            "🏆 <b>Rewards</b>\n\n"
            "Основной квест дает базовую XP.\n"
            "Дополнительные квесты дают бонусную XP.\n"
            "Raid Boss дает повышенную награду.\n\n"
            "Чем стабильнее streak и выше уровень, тем серьезнее задания.",
            back_to_menu_keyboard(),
        )
        await callback.answer()

    @router.message(Registration.pushups, F.text)
    async def set_pushups(message: Message, state: FSMContext) -> None:
        value = _parse_reps(message.text)
        if value is None:
            await message.answer("Введи целое число от 0 до 500.")
            return
        await state.update_data(pushups=value)
        await state.set_state(Registration.pullups)
        await message.answer("Теперь введи максимум подтягиваний за один подход.")

    @router.message(Registration.pullups, F.text)
    async def set_pullups(message: Message, state: FSMContext) -> None:
        value = _parse_reps(message.text)
        if value is None:
            await message.answer("Введи целое число от 0 до 500.")
            return
        await state.update_data(pullups=value)
        await state.set_state(Registration.dips)
        await message.answer("Введи максимум повторений на брусьях.")

    @router.message(Registration.dips, F.text)
    async def set_dips(message: Message, state: FSMContext) -> None:
        value = _parse_reps(message.text)
        if value is None:
            await message.answer("Введи целое число от 0 до 500.")
            return
        await state.update_data(dips=value)
        await state.set_state(Registration.squats)
        await message.answer("Последний тест: максимум приседаний за один подход.")

    @router.message(Registration.squats, F.text)
    async def set_squats(message: Message, state: FSMContext) -> None:
        value = _parse_reps(message.text)
        if value is None:
            await message.answer("Введи целое число от 0 до 500.")
            return

        data = await state.get_data()
        user = users.create(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            pushups=data["pushups"],
            pullups=data["pullups"],
            dips=data["dips"],
            squats=value,
        )
        await state.clear()
        await message.answer(
            "🏆 <b>Регистрация завершена</b>\n\n"
            f"LVL {user.level} | Rank {user.rank}\n"
            f"Сила: {user.strength} | Выносливость: {user.endurance}",
            reply_markup=main_menu_keyboard(),
        )

    return router


def _menu_text(rank: str) -> str:
    return (
        "🏰 <b>Adventurer Guild</b>\n\n"
        f"Ранг: <b>{rank}</b>\n"
        "Выбери раздел:"
    )


def _parse_reps(text: str) -> int | None:
    try:
        value = int(text.strip())
    except ValueError:
        return None
    if 0 <= value <= 500:
        return value
    return None
