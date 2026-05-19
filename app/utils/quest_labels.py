from app.logic.exercises import EXERCISE_LABELS
from app.models import Quest, QuestStatus, QuestType

LEGACY_EXERCISE_REPLACEMENTS = {
    "dumbbell_press": "dumbbell_rows",
}


def exercise_label(exercise: str) -> str:
    if "+" in exercise:
        return " + ".join(exercise_label(part) for part in exercise.split("+"))
    normalized = LEGACY_EXERCISE_REPLACEMENTS.get(exercise, exercise)
    return EXERCISE_LABELS.get(normalized, normalized.replace("_", " "))


def quest_type_label(quest: Quest) -> str:
    if quest.quest_type == QuestType.MAIN:
        return "🎯 Основной квест"
    if quest.quest_type == QuestType.RAID:
        return "⚔ Рейд-босс"
    return "⚔ Доп. квест"


def quest_type_button_label(quest: Quest) -> str:
    if quest.quest_type == QuestType.MAIN:
        return "Основной"
    if quest.quest_type == QuestType.RAID:
        return "Рейд"
    return "Доп."


def quest_status_label(quest: Quest) -> str:
    return "✅ Завершен" if quest.status == QuestStatus.DONE else "🟡 Активен"


def quest_button_label(quest: Quest) -> str:
    status = "✅" if quest.status == QuestStatus.DONE else "🟡"
    return (
        f"{status} {quest_type_button_label(quest)} #{quest.id} | "
        f"{exercise_label(quest.exercise)} | {quest.xp_reward} XP"
    )
