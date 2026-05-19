from app.logic.ranks import xp_to_next_level
from app.models import Quest, QuestStatus, QuestType, User
from app.utils.quest_labels import exercise_label, quest_status_label, quest_type_label


def format_profile(user: User) -> str:
    next_xp = xp_to_next_level(user.level)
    xp_bar = _progress_bar(user.xp, next_xp)
    return (
        "📈 <b>Профиль героя</b>\n\n"
        f"LVL <b>{user.level}</b> | Rank <b>{user.rank}</b>\n"
        f"XP <b>{user.xp}/{next_xp}</b>\n"
        f"{xp_bar}\n\n"
        "⚔️ <b>Характеристики</b>\n"
        f"Сила: <b>{user.strength}</b>\n"
        f"Выносливость: <b>{user.endurance}</b>\n"
        f"🔥 Streak: <b>{user.streak}</b>\n"
        f"🎖 Титул: <b>{_title_for_user(user)}</b>\n\n"
        "🧪 <b>Baseline</b>\n"
        f"Отжимания: {user.baseline_pushups}\n"
        f"Подтягивания: {user.baseline_pullups}\n"
        f"Брусья: {user.baseline_dips}\n"
        f"Приседания: {user.baseline_squats}"
    )


def format_quests(user: User, quests: list[Quest], random_events: list[dict] | None = None) -> str:
    random_events = random_events or []
    active_count = sum(quest.status == QuestStatus.ACTIVE for quest in quests)
    done_count = sum(quest.status == QuestStatus.DONE for quest in quests)
    random_active_count = sum(event["status"] == "sent" for event in random_events)
    random_done_count = sum(event["status"] == "done" for event in random_events)
    total_xp = sum(quest.xp_reward for quest in quests if quest.status == QuestStatus.ACTIVE)
    total_xp += sum(event["xp_reward"] for event in random_events if event["status"] == "sent")
    return (
        "📜 <b>Guild Board</b>\n\n"
        "Выбери квест ниже. У каждого задания своя цель, сдача и награда.\n\n"
        f"🟡 Активно: <b>{active_count}</b>\n"
        f"✅ Завершено: <b>{done_count}</b>\n"
        f"✨ Случайные: <b>{random_active_count}</b> активно | <b>{random_done_count}</b> закрыто\n"
        f"🏆 Доступно XP: <b>{total_xp}</b>\n\n"
        "📈 <b>Герой</b>\n"
        f"LVL {user.level} | {user.rank} | Сила {user.strength} | Выносливость {user.endurance}\n"
        f"🔥 <b>Streak:</b> {user.streak}"
    )


def format_quest_card(quest: Quest) -> str:
    status_text = quest_status_label(quest)
    bonus_text = _bonus_text(quest)
    action_text = (
        "Нажми кнопку ниже, когда выполнишь именно этот квест."
        if quest.status == QuestStatus.ACTIVE
        else "Квест закрыт. Награда за него уже получена."
    )
    return (
        f"{quest_type_label(quest)} <b>Quest #{quest.id}</b>\n\n"
        f"Статус: <b>{status_text}</b>\n"
        f"🎒 Упражнение: <b>{exercise_label(quest.exercise)}</b>\n"
        f"🎯 Цель: <b>{quest.target_reps}</b> повторений\n\n"
        "🏆 <b>Награда квеста</b>\n"
        f"<b>{quest.xp_reward}</b> XP\n"
        f"{bonus_text}\n\n"
        f"{action_text}\n"
        "Фактические повторения влияют на итоговую XP и будущую нагрузку."
    )


def format_quest_reward(quest: Quest, xp_gained: int, user: User) -> str:
    return (
        f"🏆 <b>Награда за Quest #{quest.id}</b>\n\n"
        f"{exercise_label(quest.exercise)} закрыт.\n"
        f"+<b>{xp_gained}</b> XP\n\n"
        "📈 <b>Stats</b>\n"
        f"LVL {user.level} | {user.rank}\n"
        f"Сила {user.strength} | Выносливость {user.endurance}\n"
        f"🔥 Streak: {user.streak}"
    )


def _bonus_text(quest: Quest) -> str:
    if quest.quest_type == QuestType.MAIN:
        return "🎯 Основной прогресс дня"
    if quest.quest_type == QuestType.RAID:
        return "⚔ Повышенная рейдовая награда"
    return "⚔ Дополнительная XP за инициативу"


def format_history(user: User, summary: dict, recent: list[dict]) -> str:
    if not recent:
        return (
            "🧾 <b>Журнал прогресса</b>\n\n"
            "Пока пусто. Закрой первый квест, и здесь появится история выполнений."
        )

    lines = [
        "🧾 <b>Журнал прогресса</b>",
        "",
        f"Всего закрыто квестов: <b>{summary['completed_count']}</b>",
        f"Суммарно XP: <b>{summary['total_xp']}</b>",
        f"Суммарно повторений: <b>{summary['total_reps']}</b>",
        "",
        "<b>Последние выполнения</b>",
    ]
    for item in recent:
        completed_at = item["completed_at"].replace("T", " ")[:16]
        lines.append(
            f"• {completed_at} | {exercise_label(item['exercise'])}: "
            f"{item['actual_reps']}/{item['target_reps']} | +{item['xp_gained']} XP"
        )
    return "\n".join(lines)


def _progress_bar(current: int, total: int, width: int = 10) -> str:
    filled = min(width, max(0, round(width * current / max(1, total))))
    return "▰" * filled + "▱" * (width - filled)


def _title_for_user(user: User) -> str:
    if user.streak >= 30:
        return "Unbreakable"
    if user.level >= 18:
        return "Champion"
    if user.streak >= 14:
        return "Streak Keeper"
    if user.strength >= user.endurance + 8:
        return "Iron Arms"
    if user.endurance >= user.strength + 8:
        return "Enduring Soul"
    return "Guild Adventurer"
