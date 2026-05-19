from datetime import date

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.config import Settings
from app.db.database import Database
from app.db.repositories import ExerciseSettingsRepository, QuestRepository, RandomEventRepository, UserRepository
from app.keyboards import (
    board_keyboard,
    completion_keyboard,
    effort_keyboard,
    quest_detail_keyboard,
    quests_keyboard,
    reroll_confirm_keyboard,
)
from app.logic.ai_planner import AIPlanner
from app.logic.progress import ProgressService
from app.logic.quest_generator import QuestGenerator
from app.models import Effort, QuestStatus
from app.utils.formatters import format_quest_card, format_quest_reward, format_quests
from app.utils.messages import transition
from app.utils.quest_labels import exercise_label


class CompleteQuest(StatesGroup):
    actual_reps = State()
    effort = State()


def create_quest_router(db: Database, settings: Settings) -> Router:
    router = Router()
    users = UserRepository(db)
    quests = QuestRepository(db)
    random_events = RandomEventRepository(db)
    exercise_settings = ExerciseSettingsRepository(db)
    generator = QuestGenerator()
    ai_planner = AIPlanner(settings)
    progress = ProgressService(users=users, quests=quests)

    @router.message(Command("quest"))
    async def quest_board(message: Message) -> None:
        user = users.get_by_telegram_id(message.from_user.id)
        if not user:
            await message.answer("Сначала пройди регистрацию через /start.")
            return

        today_quests = await _ensure_today_quests(user.id, today=date.today())
        today_random_events = random_events.board_events_for_user(user.id, date.today())
        fresh_user = users.get_by_id(user.id) or user
        await message.answer(
            format_quests(fresh_user, today_quests, today_random_events),
            reply_markup=board_keyboard(today_quests, today_random_events),
        )

    @router.callback_query(F.data == "menu:quest")
    async def quest_board_callback(callback: CallbackQuery, state: FSMContext) -> None:
        await state.clear()
        user = users.get_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.message.answer("Сначала пройди регистрацию через /start.")
            await callback.answer()
            return

        today_quests = await _ensure_today_quests(user.id, today=date.today())
        today_random_events = random_events.board_events_for_user(user.id, date.today())
        fresh_user = users.get_by_id(user.id) or user
        await transition(
            callback,
            format_quests(fresh_user, today_quests, today_random_events),
            board_keyboard(today_quests, today_random_events),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("quest:view:"))
    async def quest_detail(callback: CallbackQuery) -> None:
        user = users.get_by_telegram_id(callback.from_user.id)
        quest_id = int(callback.data.split(":")[-1])
        quest = quests.get(quest_id)
        if not user or not quest or quest.user_id != user.id:
            await callback.answer("Квест не найден.", show_alert=True)
            return

        await transition(callback, format_quest_card(quest), quest_detail_keyboard(quest))
        await callback.answer()

    @router.callback_query(F.data == "quest:already_done")
    async def already_done(callback: CallbackQuery) -> None:
        await callback.answer("Награда за этот квест уже получена.", show_alert=True)

    @router.callback_query(F.data == "quest:reroll:confirm")
    async def reroll_confirm(callback: CallbackQuery) -> None:
        user = users.get_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("Сначала пройди регистрацию через /start.", show_alert=True)
            return
        if quests.has_done_for_user_date(user.id, date.today()):
            await callback.answer("Сегодня уже есть закрытые квесты. Доску не пересобираю, чтобы не потерять прогресс.", show_alert=True)
            return
        await transition(
            callback,
            "♻️ <b>Пересобрать доску?</b>\n\n"
            "Я удалю активные обычные квесты за сегодня и создам новые по текущим настройкам упражнений. "
            "Случайные задания не трогаю.",
            reroll_confirm_keyboard(),
        )
        await callback.answer()

    @router.callback_query(F.data == "quest:reroll:run")
    async def reroll_run(callback: CallbackQuery) -> None:
        user = users.get_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("Сначала пройди регистрацию через /start.", show_alert=True)
            return
        today = date.today()
        if quests.has_done_for_user_date(user.id, today):
            await callback.answer("Сегодня уже есть закрытые квесты. Доску не пересобираю.", show_alert=True)
            return

        quests.delete_active_for_user_date(user.id, today)
        generated = await _generate_quests_for_user(user.id, today)
        if generated:
            quests.create_many(user_id=user.id, quest_date=today, quests=generated)
            users.mark_quest_date(user.id, today)

        today_quests = quests.get_today_for_user(user.id, today)
        today_random_events = random_events.board_events_for_user(user.id, today)
        fresh_user = users.get_by_id(user.id) or user
        await transition(
            callback,
            format_quests(fresh_user, today_quests, today_random_events),
            board_keyboard(today_quests, today_random_events),
        )
        await callback.answer("Доска пересобрана.")

    @router.callback_query(F.data.startswith("done:"))
    async def mark_done(callback: CallbackQuery, state: FSMContext) -> None:
        user = users.get_by_telegram_id(callback.from_user.id)
        quest_id = int(callback.data.split(":", 1)[1])
        quest = quests.get(quest_id)
        if not user or not quest or quest.user_id != user.id:
            await callback.answer("Квест не найден.", show_alert=True)
            return
        if quest.status == QuestStatus.DONE:
            await callback.answer("Этот квест уже выполнен.", show_alert=True)
            return

        await state.update_data(quest_id=quest.id)
        await state.set_state(CompleteQuest.actual_reps)
        await transition(
            callback,
            "🧾 <b>Отчет по квесту</b>\n\n"
            f"#{quest.id}: {exercise_label(quest.exercise)}\n"
            f"Цель: <b>{quest.target_reps}</b> повторений\n\n"
            f"Награда этого квеста: <b>{quest.xp_reward} XP</b>\n\n"
            "Введи фактическое количество повторений одним числом."
        )
        await callback.answer()

    @router.message(CompleteQuest.actual_reps, F.text)
    async def set_actual_reps(message: Message, state: FSMContext) -> None:
        actual_reps = _parse_reps(message.text)
        if actual_reps is None:
            await message.answer("Введи целое число от 0 до 2000.")
            return
        await state.update_data(actual_reps=actual_reps)
        await state.set_state(CompleteQuest.effort)
        await message.answer(
            "⚖ <b>Оценка нагрузки</b>\n\n"
            "Как ощущался квест?",
            reply_markup=effort_keyboard(),
        )

    @router.callback_query(F.data == "complete:cancel")
    async def cancel_completion(callback: CallbackQuery, state: FSMContext) -> None:
        await state.clear()
        user = users.get_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.message.answer("Сначала пройди регистрацию через /start.")
            await callback.answer()
            return
        today_quests = quests.get_today_for_user(user.id, date.today())
        today_random_events = random_events.board_events_for_user(user.id, date.today())
        await transition(
            callback,
            "Отчет отменен. Квест остался активным.",
            board_keyboard(today_quests, today_random_events),
        )
        await callback.answer()

    @router.callback_query(CompleteQuest.effort, F.data.startswith("effort:"))
    async def set_effort(callback: CallbackQuery, state: FSMContext) -> None:
        user = users.get_by_telegram_id(callback.from_user.id)
        data = await state.get_data()
        quest = quests.get(data["quest_id"])
        if not user or not quest or quest.user_id != user.id:
            await callback.answer("Квест не найден.", show_alert=True)
            await state.clear()
            return

        effort = Effort(callback.data.split(":", 1)[1])
        xp_gained = progress.complete_quest(
            user=user,
            quest=quest,
            actual_reps=data["actual_reps"],
            effort=effort,
        )
        await state.clear()

        fresh_user = users.get_by_id(user.id) or user
        await transition(callback, format_quest_reward(quest, xp_gained, fresh_user), completion_keyboard())
        await callback.answer()

    async def _ensure_today_quests(user_id: int, today: date) -> list:
        today_quests = quests.get_today_for_user(user_id, today)
        if today_quests:
            return today_quests

        user = users.get_by_id(user_id)
        if not user:
            return []
        generated = await _generate_quests_for_user(user.id, today)
        quests.create_many(user_id=user.id, quest_date=today, quests=generated)
        users.mark_quest_date(user.id, today)
        return quests.get_today_for_user(user.id, today)

    async def _generate_quests_for_user(user_id: int, today: date) -> list[dict]:
        user = users.get_by_id(user_id)
        if not user:
            return []
        enabled_exercises = exercise_settings.enabled_exercises(user.id)
        generated = await ai_planner.generate_daily(user, today, enabled_exercises)
        if generated is None:
            generated = generator.generate_daily(user, today, enabled_exercises)
        return generated

    return router


def _parse_reps(text: str) -> int | None:
    try:
        value = int(text.strip())
    except ValueError:
        return None
    if 0 <= value <= 2000:
        return value
    return None
