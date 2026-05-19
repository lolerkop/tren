from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum


class QuestType(str, Enum):
    MAIN = "main"
    SIDE = "side"
    RAID = "raid"


class QuestStatus(str, Enum):
    ACTIVE = "active"
    DONE = "done"


class Effort(str, Enum):
    EASY = "easy"
    NORMAL = "normal"
    HARD = "hard"


@dataclass
class User:
    id: int
    telegram_id: int
    username: str | None
    strength: int
    endurance: int
    level: int
    xp: int
    rank: str
    streak: int
    load_factor: float
    baseline_pushups: int
    baseline_pullups: int
    baseline_dips: int
    baseline_squats: int
    last_quest_date: date | None
    last_completed_date: date | None
    reminders_sent_today: int
    last_reminder_date: date | None


@dataclass
class Quest:
    id: int
    user_id: int
    quest_date: date
    quest_type: QuestType
    exercise: str
    target_reps: int
    xp_reward: int
    status: QuestStatus
    difficulty: float
    completed_at: datetime | None = None
