import asyncio
from datetime import date, datetime, time, timedelta
from random import Random

from aiogram import Bot

from app.db.database import Database
from app.db.repositories import ExerciseSettingsRepository, RandomEventRepository, UserRepository
from app.logic.exercises import BASELINE_FIELD_BY_EXERCISE, STRENGTH_EXERCISES
from app.logic.ranks import add_xp, rank_for_level
from app.models import User
from app.utils.quest_labels import exercise_label


class RandomEventService:
    EXERCISES = [
        "pushups",
        "pullups",
        "dips",
        "squats",
        "dumbbell_rows",
        "dumbbell_curls",
        "dumbbell_squats",
    ]

    def __init__(self, bot: Bot, db: Database) -> None:
        self.bot = bot
        self.users = UserRepository(db)
        self.events = RandomEventRepository(db)
        self.settings = ExerciseSettingsRepository(db)

    async def run_forever(self) -> None:
        await asyncio.sleep(15)
        while True:
            now = datetime.now()
            self.ensure_today_schedule(now)
            await self.send_due_events(now)
            await asyncio.sleep(60)

    def ensure_today_schedule(self, now: datetime) -> None:
        today = now.date()
        for user in self.users.all():
            if self.events.count_for_user_date(user.id, today) > 0:
                continue
            self.events.create_many(user.id, today, self._build_events(user, today, now))

    async def send_due_events(self, now: datetime) -> None:
        for event in self.events.due_events(now):
            await self.bot.send_message(
                chat_id=event["telegram_id"],
                text=format_random_event(event),
                reply_markup=random_event_keyboard(event["id"]),
            )
            self.events.mark_sent(event["id"], now)

    def complete_event(self, event_id: int, telegram_id: int) -> tuple[dict, User, int] | None:
        event = self.events.get(event_id)
        if not event or event["telegram_id"] != telegram_id or event["status"] != "sent":
            return None

        user = self.users.get_by_id(event["user_id"])
        if not user:
            return None

        level, xp = add_xp(user.level, user.xp, event["xp_reward"])
        rank = rank_for_level(level)
        strength = user.strength + (1 if event["exercise"] in STRENGTH_EXERCISES else 0)
        endurance = user.endurance + (0 if event["exercise"] in STRENGTH_EXERCISES else 1)
        self.events.complete(event_id, datetime.now())
        self.users.update_reward_stats(
            user_id=user.id,
            strength=strength,
            endurance=endurance,
            level=level,
            xp=xp,
            rank=rank,
        )
        fresh_user = self.users.get_by_id(user.id) or user
        return event, fresh_user, event["xp_reward"]

    def _build_events(self, user: User, today: date, now: datetime) -> list[dict]:
        rnd = Random(f"random-events:{user.id}:{today.isoformat()}")
        count = 1 + (1 if rnd.random() > 0.35 else 0)
        due_times = self._random_due_times(rnd, today, count)
        exercises = [exercise for exercise in self.EXERCISES if exercise in self.settings.enabled_exercises(user.id)]
        if not exercises:
            exercises = list(self.EXERCISES)
        rnd.shuffle(exercises)

        events = []
        for index in range(count):
            exercise = exercises[index % len(exercises)]
            target = self._target_for(user, exercise, rnd)
            due_at = due_times[index]
            if due_at <= now + timedelta(minutes=2):
                due_at = now + timedelta(minutes=rnd.randint(5, 45))
            events.append(
                {
                    "due_at": due_at,
                    "exercise": exercise,
                    "target_reps": target,
                    "xp_reward": 10 + round(target * 0.5) + user.level,
                }
            )
        return events

    def _random_due_times(self, rnd: Random, today: date, count: int) -> list[datetime]:
        windows = [(time(10, 0), time(14, 0)), (time(17, 0), time(21, 30))]
        selected = windows if count == 2 else [rnd.choice(windows)]
        result = []
        for start, end in selected:
            start_dt = datetime.combine(today, start)
            end_dt = datetime.combine(today, end)
            minutes = int((end_dt - start_dt).total_seconds() // 60)
            result.append(start_dt + timedelta(minutes=rnd.randint(0, minutes)))
        return sorted(result)

    def _target_for(self, user: User, exercise: str, rnd: Random) -> int:
        if exercise in BASELINE_FIELD_BY_EXERCISE:
            baseline = getattr(user, BASELINE_FIELD_BY_EXERCISE[exercise])
        else:
            baseline = max(8, user.strength * 2 + user.endurance)
        multiplier = rnd.uniform(0.18, 0.32)
        return max(1, round(baseline * user.load_factor * multiplier))


def format_random_event(event: dict) -> str:
    action_text = (
        "Выполни его сейчас и забери бонус."
        if event["status"] in {"pending", "sent"}
        else "Задание закрыто. Награда уже получена."
    )
    return (
        f"✨ <b>Случайное задание #{event['id']}</b>\n\n"
        f"Статус: <b>{_event_status_label(event)}</b>\n"
        f"🎒 Упражнение: <b>{exercise_label(event['exercise'])}</b>\n"
        f"🎯 Цель: <b>{event['target_reps']}</b> повторений\n\n"
        "🏆 <b>Награда</b>\n"
        f"<b>{event['xp_reward']}</b> XP\n\n"
        f"{action_text}"
    )


def format_random_reward(event: dict, user: User, xp_gained: int) -> str:
    return (
        "🏆 <b>Random reward claimed</b>\n\n"
        f"{exercise_label(event['exercise'])}: +<b>{xp_gained}</b> XP\n\n"
        f"LVL {user.level} | {user.rank}\n"
        f"Сила {user.strength} | Выносливость {user.endurance}"
    )


def random_event_keyboard(event_id: int):
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📜 Открыть на доске", callback_data=f"random:view:{event_id}")],
            [InlineKeyboardButton(text="✅ Выполнено, забрать XP", callback_data=f"random:done:{event_id}")],
            [InlineKeyboardButton(text="📜 Guild Board", callback_data="menu:quest")],
        ]
    )


def _event_status_label(event: dict) -> str:
    if event["status"] == "done":
        return "✅ Завершено"
    if event["status"] == "sent":
        return "✨ Активно"
    return "⏳ Ожидает времени"
