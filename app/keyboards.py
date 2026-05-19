from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.logic.exercises import EXERCISE_GROUPS
from app.models import Quest, QuestStatus
from app.utils.quest_labels import exercise_label, quest_button_label


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📜 Guild Board", callback_data="menu:quest"),
                InlineKeyboardButton(text="📈 Profile", callback_data="menu:profile"),
            ],
            [
                InlineKeyboardButton(text="🧾 Журнал", callback_data="menu:history"),
            ],
            [
                InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings:home"),
            ],
            [
                InlineKeyboardButton(text="🏆 Rewards", callback_data="menu:rewards"),
                InlineKeyboardButton(text="❔ Help", callback_data="menu:help"),
            ],
        ]
    )


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏰 Главное меню", callback_data="menu:home")],
        ]
    )


def profile_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📜 Квесты", callback_data="menu:quest"),
                InlineKeyboardButton(text="🔄 Обновить", callback_data="menu:profile"),
            ],
            [InlineKeyboardButton(text="🧾 Журнал прогресса", callback_data="menu:history")],
            [InlineKeyboardButton(text="⚙️ Настройки программы", callback_data="settings:home")],
            [InlineKeyboardButton(text="🏰 Главное меню", callback_data="menu:home")],
        ]
    )


def quests_keyboard(quests: list[Quest]) -> InlineKeyboardMarkup:
    return board_keyboard(quests, [])


def board_keyboard(quests: list[Quest], random_events: list[dict]) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    for quest in quests:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=quest_button_label(quest),
                    callback_data=f"quest:view:{quest.id}",
                )
            ]
        )
    for event in random_events:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=random_event_button_label(event),
                    callback_data=f"random:view:{event['id']}",
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(text="📈 Профиль", callback_data="menu:profile"),
            InlineKeyboardButton(text="🔄 Обновить", callback_data="menu:quest"),
        ]
    )
    buttons.append([InlineKeyboardButton(text="♻️ Пересобрать активные", callback_data="quest:reroll:confirm")])
    buttons.append([InlineKeyboardButton(text="🏰 Главное меню", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def reroll_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="♻️ Да, пересобрать", callback_data="quest:reroll:run")],
            [InlineKeyboardButton(text="↩️ Назад к доске", callback_data="menu:quest")],
        ]
    )


def history_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📜 К доске", callback_data="menu:quest"),
                InlineKeyboardButton(text="📈 Профиль", callback_data="menu:profile"),
            ],
            [InlineKeyboardButton(text="🏰 Главное меню", callback_data="menu:home")],
        ]
    )


def random_event_button_label(event: dict) -> str:
    status = "✅" if event["status"] == "done" else "✨"
    return f"{status} Случайное #{event['id']} | {exercise_label(event['exercise'])} | {event['xp_reward']} XP"


def random_event_detail_keyboard(event: dict) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    if event["status"] == "sent":
        buttons.append([InlineKeyboardButton(text="✅ Выполнено, забрать XP", callback_data=f"random:done:{event['id']}")])
    else:
        buttons.append([InlineKeyboardButton(text="🏆 Награда получена", callback_data="random:already_done")])
    buttons.extend(
        [
            [
                InlineKeyboardButton(text="📜 К доске", callback_data="menu:quest"),
                InlineKeyboardButton(text="📈 Профиль", callback_data="menu:profile"),
            ],
            [InlineKeyboardButton(text="🏰 Главное меню", callback_data="menu:home")],
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def settings_groups_keyboard(enabled_exercises: set[str]) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    for group_id, group in EXERCISE_GROUPS.items():
        exercises = group["exercises"]
        enabled_count = sum(exercise in enabled_exercises for exercise in exercises)
        total_count = len(exercises)
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{group['icon']} {group['label']} ({enabled_count}/{total_count})",
                    callback_data=f"settings:group:{group_id}",
                )
            ]
        )

    buttons.append([InlineKeyboardButton(text="✅ Включить все", callback_data="settings:reset")])
    buttons.append([InlineKeyboardButton(text="♻️ Пересобрать сегодняшнюю доску", callback_data="quest:reroll:confirm")])
    buttons.append([InlineKeyboardButton(text="🏰 Главное меню", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def settings_exercises_keyboard(group_id: str, enabled_exercises: set[str]) -> InlineKeyboardMarkup:
    group = EXERCISE_GROUPS[group_id]
    buttons: list[list[InlineKeyboardButton]] = []
    for exercise in group["exercises"]:
        marker = "✅" if exercise in enabled_exercises else "⬜"
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{marker} {exercise_label(exercise)}",
                    callback_data=f"settings:toggle:{group_id}:{exercise}",
                )
            ]
        )

    buttons.append([InlineKeyboardButton(text="↩️ К группам", callback_data="settings:home")])
    buttons.append([InlineKeyboardButton(text="🏰 Главное меню", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def quest_detail_keyboard(quest: Quest) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    if quest.status == QuestStatus.ACTIVE:
        buttons.append([InlineKeyboardButton(text="✅ Сдать этот квест", callback_data=f"done:{quest.id}")])
    else:
        buttons.append([InlineKeyboardButton(text="🏆 Награда получена", callback_data="quest:already_done")])

    buttons.extend(
        [
            [
                InlineKeyboardButton(text="📜 К доске", callback_data="menu:quest"),
                InlineKeyboardButton(text="📈 Профиль", callback_data="menu:profile"),
            ],
            [InlineKeyboardButton(text="🏰 Главное меню", callback_data="menu:home")],
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def effort_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🟢 Легко", callback_data="effort:easy"),
                InlineKeyboardButton(text="🟡 Нормально", callback_data="effort:normal"),
            ],
            [
                InlineKeyboardButton(text="🔴 Тяжело", callback_data="effort:hard"),
                InlineKeyboardButton(text="↩️ Отмена", callback_data="complete:cancel"),
            ],
        ]
    )


def completion_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📜 К доске", callback_data="menu:quest"),
                InlineKeyboardButton(text="📈 Профиль", callback_data="menu:profile"),
            ],
            [InlineKeyboardButton(text="🏰 Главное меню", callback_data="menu:home")],
        ]
    )
