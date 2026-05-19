import sqlite3
from pathlib import Path
from sqlite3 import Row


class Database:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.connection: sqlite3.Connection | None = None

    def connect(self) -> None:
        if self.path.parent != Path("."):
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = Row
        self.connection.execute("PRAGMA foreign_keys = ON")

    def close(self) -> None:
        if self.connection:
            self.connection.close()

    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        if not self.connection:
            raise RuntimeError("Database is not connected.")
        cursor = self.connection.execute(query, params)
        self.connection.commit()
        return cursor

    def executemany(self, query: str, params: list[tuple]) -> None:
        if not self.connection:
            raise RuntimeError("Database is not connected.")
        self.connection.executemany(query, params)
        self.connection.commit()

    def fetchone(self, query: str, params: tuple = ()) -> Row | None:
        if not self.connection:
            raise RuntimeError("Database is not connected.")
        return self.connection.execute(query, params).fetchone()

    def fetchall(self, query: str, params: tuple = ()) -> list[Row]:
        if not self.connection:
            raise RuntimeError("Database is not connected.")
        return self.connection.execute(query, params).fetchall()

    def init_schema(self) -> None:
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL UNIQUE,
                username TEXT,
                strength INTEGER NOT NULL DEFAULT 1,
                endurance INTEGER NOT NULL DEFAULT 1,
                level INTEGER NOT NULL DEFAULT 1,
                xp INTEGER NOT NULL DEFAULT 0,
                rank TEXT NOT NULL DEFAULT 'Novice',
                streak INTEGER NOT NULL DEFAULT 0,
                load_factor REAL NOT NULL DEFAULT 1.0,
                baseline_pushups INTEGER NOT NULL,
                baseline_pullups INTEGER NOT NULL,
                baseline_dips INTEGER NOT NULL,
                baseline_squats INTEGER NOT NULL,
                last_quest_date TEXT,
                last_completed_date TEXT,
                reminders_sent_today INTEGER NOT NULL DEFAULT 0,
                last_reminder_date TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS quests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                quest_date TEXT NOT NULL,
                quest_type TEXT NOT NULL,
                exercise TEXT NOT NULL,
                target_reps INTEGER NOT NULL,
                xp_reward INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                difficulty REAL NOT NULL DEFAULT 1.0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                quest_id INTEGER NOT NULL,
                exercise TEXT NOT NULL,
                target_reps INTEGER NOT NULL,
                actual_reps INTEGER NOT NULL,
                effort TEXT NOT NULL,
                xp_gained INTEGER NOT NULL,
                completed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (quest_id) REFERENCES quests(id) ON DELETE CASCADE
            )
            """
        )
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS random_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                event_date TEXT NOT NULL,
                due_at TEXT NOT NULL,
                exercise TEXT NOT NULL,
                target_reps INTEGER NOT NULL,
                xp_reward INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                sent_at TEXT,
                completed_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS user_exercise_settings (
                user_id INTEGER NOT NULL,
                exercise TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, exercise),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        self._migrate_legacy_exercises()

    def _migrate_legacy_exercises(self) -> None:
        # Old builds could already have dumbbell_press saved in SQLite.
        # Replace it with dumbbell rows because the user has no bench.
        replacements = {"dumbbell_press": "dumbbell_rows"}
        for old_exercise, new_exercise in replacements.items():
            self.execute(
                "UPDATE quests SET exercise = ? WHERE exercise = ?",
                (new_exercise, old_exercise),
            )
            self.execute(
                "UPDATE random_events SET exercise = ? WHERE exercise = ?",
                (new_exercise, old_exercise),
            )
            self.execute(
                "UPDATE progress SET exercise = ? WHERE exercise = ?",
                (new_exercise, old_exercise),
            )
