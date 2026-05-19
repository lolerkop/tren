from datetime import date
from random import Random

from app.logic.exercises import BASELINE_FIELD_BY_EXERCISE
from app.models import QuestType, User


class QuestGenerator:
    MAIN_EXERCISES = ["pushups", "pullups", "dips", "squats"]
    SIDE_EXERCISES = [
        "pushups",
        "pullups",
        "dips",
        "squats",
        "dumbbell_rows",
        "dumbbell_curls",
        "dumbbell_squats",
    ]

    def generate_daily(self, user: User, today: date, allowed_exercises: set[str] | None = None) -> list[dict]:
        rnd = Random(f"{user.id}:{today.isoformat()}")
        quests: list[dict] = []
        allowed = allowed_exercises or set(self.SIDE_EXERCISES)
        main_pool = [exercise for exercise in self.MAIN_EXERCISES if exercise in allowed]
        side_pool_all = [exercise for exercise in self.SIDE_EXERCISES if exercise in allowed]
        if not side_pool_all:
            side_pool_all = list(self.SIDE_EXERCISES)
        if not main_pool:
            main_pool = list(side_pool_all)

        if today.weekday() == 6:
            quests.append(self._raid_quest(user, rnd, main_pool))
            return quests

        main_exercise = rnd.choice(main_pool)
        quests.append(
            self._build_quest(
                user=user,
                quest_type=QuestType.MAIN,
                exercise=main_exercise,
                multiplier=rnd.uniform(0.58, 0.76),
                xp_base=35,
            )
        )

        side_pool = [exercise for exercise in side_pool_all if exercise != main_exercise]
        if not side_pool:
            side_pool = [main_exercise]
        rnd.shuffle(side_pool)
        side_count = min(len(side_pool), 2 + (1 if user.level >= 4 and rnd.random() > 0.45 else 0))
        for exercise in side_pool[:side_count]:
            quests.append(
                self._build_quest(
                    user=user,
                    quest_type=QuestType.SIDE,
                    exercise=exercise,
                    multiplier=rnd.uniform(0.28, 0.46),
                    xp_base=18,
                )
            )

        return quests

    def _raid_quest(self, user: User, rnd: Random, main_pool: list[str]) -> dict:
        raid_count = min(3, len(main_pool))
        exercises = rnd.sample(main_pool, raid_count)
        # Raid is stored as a single total-reps challenge, but text names all movements.
        total = sum(self._target_for(user, exercise, rnd.uniform(0.42, 0.56)) for exercise in exercises)
        return {
            "quest_type": QuestType.RAID.value,
            "exercise": "+".join(exercises),
            "target_reps": max(20, total),
            "xp_reward": 95 + user.level * 8,
            "difficulty": 1.45,
        }

    def _build_quest(
        self,
        user: User,
        quest_type: QuestType,
        exercise: str,
        multiplier: float,
        xp_base: int,
    ) -> dict:
        target = self._target_for(user, exercise, multiplier)
        difficulty = multiplier * user.load_factor
        return {
            "quest_type": quest_type.value,
            "exercise": exercise,
            "target_reps": target,
            "xp_reward": xp_base + round(target * (0.7 if quest_type == QuestType.MAIN else 0.45)),
            "difficulty": round(difficulty, 2),
        }

    def _target_for(self, user: User, exercise: str, multiplier: float) -> int:
        if exercise in BASELINE_FIELD_BY_EXERCISE:
            baseline = getattr(user, BASELINE_FIELD_BY_EXERCISE[exercise])
        else:
            baseline = max(10, user.strength * 3 + user.endurance * 2)

        level_bonus = 1 + min(0.35, (user.level - 1) * 0.025)
        streak_bonus = 1 + min(0.12, user.streak * 0.01)
        raw_target = baseline * multiplier * user.load_factor * level_bonus * streak_bonus
        return max(1, round(raw_target))
