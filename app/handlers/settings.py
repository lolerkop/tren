from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.db.database import Database
from app.db.repositories import ExerciseSettingsRepository, UserRepository
from app.keyboards import settings_exercises_keyboard, settings_groups_keyboard
from app.logic.exercises import EXERCISE_GROUPS
from app.utils.messages import transition


def router(db: Database) -> Router:
    settings_router = Router()
    users = UserRepository(db)
    exercise_settings = ExerciseSettingsRepository(db)

    @settings_router.message(Command("settings"))
    async def settings_command(message: Message) -> None:
        user = users.get_by_telegram_id(message.from_user.id)
        if not user:
            await message.answer("Сначала пройди регистрацию через /start.")
            return
        enabled = exercise_settings.enabled_exercises(user.id)
        await message.answer(_settings_text(enabled), reply_markup=settings_groups_keyboard(enabled))

    @settings_router.callback_query(F.data == "settings:home")
    async def settings_home(callback: CallbackQuery) -> None:
        user = users.get_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("Сначала пройди регистрацию через /start.", show_alert=True)
            return
        enabled = exercise_settings.enabled_exercises(user.id)
        await transition(callback, _settings_text(enabled), settings_groups_keyboard(enabled))
        await callback.answer()

    @settings_router.callback_query(F.data == "settings:reset")
    async def settings_reset(callback: CallbackQuery) -> None:
        user = users.get_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("Сначала пройди регистрацию через /start.", show_alert=True)
            return
        exercise_settings.reset(user.id)
        enabled = exercise_settings.enabled_exercises(user.id)
        await transition(callback, _settings_text(enabled), settings_groups_keyboard(enabled))
        await callback.answer("Все упражнения включены.")

    @settings_router.callback_query(F.data.startswith("settings:group:"))
    async def settings_group(callback: CallbackQuery) -> None:
        user = users.get_by_telegram_id(callback.from_user.id)
        group_id = callback.data.split(":")[-1]
        if not user or group_id not in EXERCISE_GROUPS:
            await callback.answer("Раздел не найден.", show_alert=True)
            return
        enabled = exercise_settings.enabled_exercises(user.id)
        await transition(
            callback,
            _group_text(group_id, enabled),
            settings_exercises_keyboard(group_id, enabled),
        )
        await callback.answer()

    @settings_router.callback_query(F.data.startswith("settings:toggle:"))
    async def settings_toggle(callback: CallbackQuery) -> None:
        user = users.get_by_telegram_id(callback.from_user.id)
        parts = callback.data.split(":")
        if not user or len(parts) != 4:
            await callback.answer("Настройка не найдена.", show_alert=True)
            return

        _, _, group_id, exercise = parts
        if group_id not in EXERCISE_GROUPS or exercise not in EXERCISE_GROUPS[group_id]["exercises"]:
            await callback.answer("Упражнение не найдено.", show_alert=True)
            return

        enabled = exercise_settings.enabled_exercises(user.id)
        if exercise in enabled and len(enabled) <= 1:
            await callback.answer("Нельзя выключить последнее упражнение.", show_alert=True)
            return

        now_enabled = exercise_settings.toggle(user.id, exercise)
        enabled = exercise_settings.enabled_exercises(user.id)
        await transition(
            callback,
            _group_text(group_id, enabled),
            settings_exercises_keyboard(group_id, enabled),
        )
        await callback.answer("Включено" if now_enabled else "Выключено")

    return settings_router


def _settings_text(enabled_exercises: set[str]) -> str:
    total = sum(len(group["exercises"]) for group in EXERCISE_GROUPS.values())
    return (
        "⚙️ <b>Настройки программы</b>\n\n"
        "Выбери группу мышц, затем включи или выключи упражнения галочками.\n"
        "В новые квесты и случайные задания будут попадать только отмеченные упражнения.\n\n"
        f"✅ Включено: <b>{len(enabled_exercises)}/{total}</b>"
    )


def _group_text(group_id: str, enabled_exercises: set[str]) -> str:
    group = EXERCISE_GROUPS[group_id]
    enabled_count = sum(exercise in enabled_exercises for exercise in group["exercises"])
    return (
        f"{group['icon']} <b>{group['label']}</b>\n\n"
        "Нажимай на упражнение, чтобы переключить галочку.\n\n"
        f"✅ Включено в группе: <b>{enabled_count}/{len(group['exercises'])}</b>"
    )
