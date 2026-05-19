from datetime import date, datetime
from sqlite3 import Row

from app.db.database import Database
from app.logic.exercises import DEFAULT_ENABLED_EXERCISES
from app.models import Quest, QuestStatus, QuestType, User


def _parse_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def _user_from_row(row: Row) -> User:
    return User(
        id=row["id"],
        telegram_id=row["telegram_id"],
        username=row["username"],
        strength=row["strength"],
        endurance=row["endurance"],
        level=row["level"],
        xp=row["xp"],
        rank=row["rank"],
        streak=row["streak"],
        load_factor=row["load_factor"],
        baseline_pushups=row["baseline_pushups"],
        baseline_pullups=row["baseline_pullups"],
        baseline_dips=row["baseline_dips"],
        baseline_squats=row["baseline_squats"],
        last_quest_date=_parse_date(row["last_quest_date"]),
        last_completed_date=_parse_date(row["last_completed_date"]),
        reminders_sent_today=row["reminders_sent_today"],
        last_reminder_date=_parse_date(row["last_reminder_date"]),
    )


def _quest_from_row(row: Row) -> Quest:
    return Quest(
        id=row["id"],
        user_id=row["user_id"],
        quest_date=date.fromisoformat(row["quest_date"]),
        quest_type=QuestType(row["quest_type"]),
        exercise=row["exercise"],
        target_reps=row["target_reps"],
        xp_reward=row["xp_reward"],
        status=QuestStatus(row["status"]),
        difficulty=row["difficulty"],
    )


class UserRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def get_by_telegram_id(self, telegram_id: int) -> User | None:
        row = self.db.fetchone("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        return _user_from_row(row) if row else None

    def get_by_id(self, user_id: int) -> User | None:
        row = self.db.fetchone("SELECT * FROM users WHERE id = ?", (user_id,))
        return _user_from_row(row) if row else None

    def all(self) -> list[User]:
        rows = self.db.fetchall("SELECT * FROM users ORDER BY id")
        return [_user_from_row(row) for row in rows]

    def create(
        self,
        telegram_id: int,
        username: str | None,
        pushups: int,
        pullups: int,
        dips: int,
        squats: int,
    ) -> User:
        strength = max(1, round((pushups + pullups * 4 + dips * 3) / 12))
        endurance = max(1, round((pushups + squats) / 15))
        self.db.execute(
            """
            INSERT INTO users (
                telegram_id, username, strength, endurance,
                baseline_pushups, baseline_pullups, baseline_dips, baseline_squats
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (telegram_id, username, strength, endurance, pushups, pullups, dips, squats),
        )
        user = self.get_by_telegram_id(telegram_id)
        if not user:
            raise RuntimeError("Failed to create user.")
        return user

    def update_after_progress(
        self,
        user: User,
        strength: int,
        endurance: int,
        level: int,
        xp: int,
        rank: str,
        streak: int,
        load_factor: float,
        completed_date: date,
    ) -> None:
        self.db.execute(
            """
            UPDATE users
            SET strength = ?, endurance = ?, level = ?, xp = ?, rank = ?,
                streak = ?, load_factor = ?, last_completed_date = ?
            WHERE id = ?
            """,
            (
                strength,
                endurance,
                level,
                xp,
                rank,
                streak,
                load_factor,
                completed_date.isoformat(),
                user.id,
            ),
        )

    def update_reward_stats(
        self,
        user_id: int,
        strength: int,
        endurance: int,
        level: int,
        xp: int,
        rank: str,
    ) -> None:
        self.db.execute(
            """
            UPDATE users
            SET strength = ?, endurance = ?, level = ?, xp = ?, rank = ?
            WHERE id = ?
            """,
            (strength, endurance, level, xp, rank, user_id),
        )

    def mark_quest_date(self, user_id: int, quest_date: date) -> None:
        self.db.execute(
            "UPDATE users SET last_quest_date = ? WHERE id = ?",
            (quest_date.isoformat(), user_id),
        )

    def users_for_reminders(self, today: date) -> list[User]:
        rows = self.db.fetchall(
            """
            SELECT DISTINCT users.*
            FROM users
            JOIN quests ON quests.user_id = users.id
            WHERE quests.quest_date = ?
              AND quests.status = 'active'
              AND (
                users.last_reminder_date IS NULL
                OR users.last_reminder_date != ?
                OR users.reminders_sent_today < 3
              )
            """,
            (today.isoformat(), today.isoformat()),
        )
        return [_user_from_row(row) for row in rows]

    def register_reminder(self, user_id: int, today: date) -> None:
        user = self.get_by_id(user_id)
        if not user:
            return
        count = user.reminders_sent_today + 1 if user.last_reminder_date == today else 1
        self.db.execute(
            """
            UPDATE users
            SET reminders_sent_today = ?, last_reminder_date = ?
            WHERE id = ?
            """,
            (count, today.isoformat(), user_id),
        )


class QuestRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def get_today_for_user(self, user_id: int, today: date) -> list[Quest]:
        rows = self.db.fetchall(
            """
            SELECT * FROM quests
            WHERE user_id = ? AND quest_date = ?
            ORDER BY CASE quest_type WHEN 'main' THEN 1 WHEN 'side' THEN 2 ELSE 3 END, id
            """,
            (user_id, today.isoformat()),
        )
        return [_quest_from_row(row) for row in rows]

    def get(self, quest_id: int) -> Quest | None:
        row = self.db.fetchone("SELECT * FROM quests WHERE id = ?", (quest_id,))
        return _quest_from_row(row) if row else None

    def has_done_for_user_date(self, user_id: int, quest_date: date) -> bool:
        row = self.db.fetchone(
            """
            SELECT 1
            FROM quests
            WHERE user_id = ? AND quest_date = ? AND status = 'done'
            LIMIT 1
            """,
            (user_id, quest_date.isoformat()),
        )
        return bool(row)

    def delete_active_for_user_date(self, user_id: int, quest_date: date) -> None:
        self.db.execute(
            """
            DELETE FROM quests
            WHERE user_id = ? AND quest_date = ? AND status = 'active'
            """,
            (user_id, quest_date.isoformat()),
        )

    def create_many(self, user_id: int, quest_date: date, quests: list[dict]) -> None:
        self.db.executemany(
            """
            INSERT INTO quests (
                user_id, quest_date, quest_type, exercise, target_reps, xp_reward, difficulty
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    user_id,
                    quest_date.isoformat(),
                    quest["quest_type"],
                    quest["exercise"],
                    quest["target_reps"],
                    quest["xp_reward"],
                    quest["difficulty"],
                )
                for quest in quests
            ],
        )

    def complete(self, quest: Quest, actual_reps: int, effort: str, xp_gained: int) -> None:
        self.db.execute(
            """
            UPDATE quests
            SET status = 'done', completed_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (quest.id,),
        )
        self.db.execute(
            """
            INSERT INTO progress (
                user_id, quest_id, exercise, target_reps, actual_reps, effort, xp_gained
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                quest.user_id,
                quest.id,
                quest.exercise,
                quest.target_reps,
                actual_reps,
                effort,
                xp_gained,
            ),
        )


class RandomEventRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def count_for_user_date(self, user_id: int, event_date: date) -> int:
        row = self.db.fetchone(
            """
            SELECT COUNT(*) AS count
            FROM random_events
            WHERE user_id = ? AND event_date = ?
            """,
            (user_id, event_date.isoformat()),
        )
        return int(row["count"]) if row else 0

    def create_many(self, user_id: int, event_date: date, events: list[dict]) -> None:
        self.db.executemany(
            """
            INSERT INTO random_events (
                user_id, event_date, due_at, exercise, target_reps, xp_reward
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    user_id,
                    event_date.isoformat(),
                    event["due_at"].isoformat(timespec="minutes"),
                    event["exercise"],
                    event["target_reps"],
                    event["xp_reward"],
                )
                for event in events
            ],
        )

    def due_events(self, now: datetime) -> list[dict]:
        rows = self.db.fetchall(
            """
            SELECT random_events.*, users.telegram_id
            FROM random_events
            JOIN users ON users.id = random_events.user_id
            WHERE random_events.status = 'pending'
              AND random_events.event_date = ?
              AND random_events.due_at <= ?
            ORDER BY random_events.due_at, random_events.id
            """,
            (now.date().isoformat(), now.isoformat(timespec="minutes")),
        )
        return [dict(row) for row in rows]

    def get(self, event_id: int) -> dict | None:
        row = self.db.fetchone(
            """
            SELECT random_events.*, users.telegram_id
            FROM random_events
            JOIN users ON users.id = random_events.user_id
            WHERE random_events.id = ?
            """,
            (event_id,),
        )
        return dict(row) if row else None

    def mark_sent(self, event_id: int, now: datetime) -> None:
        self.db.execute(
            """
            UPDATE random_events
            SET status = 'sent', sent_at = ?
            WHERE id = ? AND status = 'pending'
            """,
            (now.isoformat(timespec="seconds"), event_id),
        )

    def board_events_for_user(self, user_id: int, event_date: date) -> list[dict]:
        rows = self.db.fetchall(
            """
            SELECT *
            FROM random_events
            WHERE user_id = ?
              AND event_date = ?
              AND status IN ('sent', 'done')
            ORDER BY due_at, id
            """,
            (user_id, event_date.isoformat()),
        )
        return [dict(row) for row in rows]

    def complete(self, event_id: int, now: datetime) -> None:
        self.db.execute(
            """
            UPDATE random_events
            SET status = 'done', completed_at = ?
            WHERE id = ? AND status = 'sent'
            """,
            (now.isoformat(timespec="seconds"), event_id),
        )


class ExerciseSettingsRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def enabled_exercises(self, user_id: int) -> set[str]:
        rows = self.db.fetchall(
            """
            SELECT exercise, enabled
            FROM user_exercise_settings
            WHERE user_id = ?
            """,
            (user_id,),
        )
        if not rows:
            return set(DEFAULT_ENABLED_EXERCISES)

        enabled = set(DEFAULT_ENABLED_EXERCISES)
        for row in rows:
            exercise = row["exercise"]
            if exercise not in DEFAULT_ENABLED_EXERCISES:
                continue
            if row["enabled"]:
                enabled.add(exercise)
            else:
                enabled.discard(exercise)
        return enabled

    def is_enabled(self, user_id: int, exercise: str) -> bool:
        return exercise in self.enabled_exercises(user_id)

    def toggle(self, user_id: int, exercise: str) -> bool:
        if exercise not in DEFAULT_ENABLED_EXERCISES:
            raise ValueError(f"Unknown exercise: {exercise}")

        currently_enabled = self.is_enabled(user_id, exercise)
        new_value = 0 if currently_enabled else 1
        self.db.execute(
            """
            INSERT INTO user_exercise_settings (user_id, exercise, enabled, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id, exercise)
            DO UPDATE SET enabled = excluded.enabled, updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, exercise, new_value),
        )
        return bool(new_value)

    def reset(self, user_id: int) -> None:
        self.db.execute(
            "DELETE FROM user_exercise_settings WHERE user_id = ?",
            (user_id,),
        )


class ProgressRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def recent_for_user(self, user_id: int, limit: int = 10) -> list[dict]:
        rows = self.db.fetchall(
            """
            SELECT *
            FROM progress
            WHERE user_id = ?
            ORDER BY completed_at DESC, id DESC
            LIMIT ?
            """,
            (user_id, limit),
        )
        return [dict(row) for row in rows]

    def summary_for_user(self, user_id: int) -> dict:
        row = self.db.fetchone(
            """
            SELECT
                COUNT(*) AS completed_count,
                COALESCE(SUM(xp_gained), 0) AS total_xp,
                COALESCE(SUM(actual_reps), 0) AS total_reps
            FROM progress
            WHERE user_id = ?
            """,
            (user_id,),
        )
        if not row:
            return {"completed_count": 0, "total_xp": 0, "total_reps": 0}
        return {
            "completed_count": row["completed_count"],
            "total_xp": row["total_xp"],
            "total_reps": row["total_reps"],
        }
