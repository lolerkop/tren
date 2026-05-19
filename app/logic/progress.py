from datetime import date, timedelta

from app.db.repositories import QuestRepository, UserRepository
from app.logic.exercises import STRENGTH_EXERCISES
from app.logic.ranks import add_xp, rank_for_level
from app.models import Effort, Quest, User


class ProgressService:
    def __init__(self, users: UserRepository, quests: QuestRepository) -> None:
        self.users = users
        self.quests = quests

    def complete_quest(self, user: User, quest: Quest, actual_reps: int, effort: Effort) -> int:
        xp_gained = self._xp_for(quest, actual_reps)
        strength, endurance = self._stats_after(user, quest.exercise, actual_reps, effort)
        level, xp = add_xp(user.level, user.xp, xp_gained)
        rank = rank_for_level(level)
        streak = self._streak_after(user, date.today())
        load_factor = self._load_factor_after(user, quest.target_reps, actual_reps, effort)

        self.quests.complete(quest=quest, actual_reps=actual_reps, effort=effort.value, xp_gained=xp_gained)
        self.users.update_after_progress(
            user=user,
            strength=strength,
            endurance=endurance,
            level=level,
            xp=xp,
            rank=rank,
            streak=streak,
            load_factor=load_factor,
            completed_date=date.today(),
        )
        return xp_gained

    def _xp_for(self, quest: Quest, actual_reps: int) -> int:
        ratio = min(1.35, actual_reps / max(1, quest.target_reps))
        return max(5, round(quest.xp_reward * ratio))

    def _stats_after(self, user: User, exercise: str, actual_reps: int, effort: Effort) -> tuple[int, int]:
        stat_gain = 1 if actual_reps >= 1 else 0
        if effort == Effort.EASY and actual_reps >= 10:
            stat_gain += 1

        if any(part in STRENGTH_EXERCISES for part in exercise.split("+")):
            return user.strength + stat_gain, user.endurance + max(0, stat_gain - 1)
        return user.strength, user.endurance + stat_gain

    def _streak_after(self, user: User, today: date) -> int:
        if user.last_completed_date == today:
            return user.streak
        if user.last_completed_date == today - timedelta(days=1):
            return user.streak + 1
        return 1

    def _load_factor_after(self, user: User, target_reps: int, actual_reps: int, effort: Effort) -> float:
        ratio = actual_reps / max(1, target_reps)
        delta = 0.0
        if effort == Effort.EASY and ratio >= 1:
            delta = 0.03
        elif effort == Effort.NORMAL and ratio >= 1.05:
            delta = 0.01
        elif effort == Effort.HARD or ratio < 0.85:
            delta = -0.05

        return round(min(1.8, max(0.6, user.load_factor + delta)), 2)
