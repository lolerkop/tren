import unittest
from datetime import date, datetime

from app.config import Settings
from app.db.database import Database
from app.db.repositories import ExerciseSettingsRepository, ProgressRepository, QuestRepository, RandomEventRepository, UserRepository
from app.logic.ai_planner import AIPlanner
from app.logic.progress import ProgressService
from app.logic.quest_generator import QuestGenerator
from app.logic.random_events import RandomEventService
from app.models import Effort, Quest, QuestStatus, QuestType
from app.utils.formatters import format_history, format_profile, format_quest_card
from app.utils.quest_labels import quest_button_label


class BotStub:
    async def send_message(self, **kwargs):
        return None


class CoreLogicTest(unittest.TestCase):
    def setUp(self) -> None:
        self.db = Database(":memory:")
        self.db.connect()
        self.db.init_schema()
        self.users = UserRepository(self.db)
        self.user = self.users.create(telegram_id=123, username="tester", pushups=20, pullups=5, dips=8, squats=40)

    def tearDown(self) -> None:
        self.db.close()

    def test_exercise_settings_toggle_and_generator_respects_allowed_set(self) -> None:
        settings = ExerciseSettingsRepository(self.db)
        self.assertIn("pushups", settings.enabled_exercises(self.user.id))

        settings.toggle(self.user.id, "pushups")
        self.assertNotIn("pushups", settings.enabled_exercises(self.user.id))

        quests = QuestGenerator().generate_daily(self.user, date(2026, 5, 6), {"dumbbell_curls"})
        self.assertTrue(quests)
        self.assertTrue(all(quest["exercise"] == "dumbbell_curls" for quest in quests))

    def test_random_event_reaches_board_and_can_complete(self) -> None:
        events = RandomEventRepository(self.db)
        service = RandomEventService(BotStub(), self.db)
        now = datetime.now()

        service.ensure_today_schedule(now)
        due = events.due_events(datetime.max.replace(year=now.year, month=now.month, day=now.day))
        self.assertTrue(due)

        events.mark_sent(due[0]["id"], now)
        board_events = events.board_events_for_user(self.user.id, now.date())
        self.assertEqual(board_events[0]["status"], "sent")

        result = service.complete_event(board_events[0]["id"], self.user.telegram_id)
        self.assertIsNotNone(result)
        completed = events.get(board_events[0]["id"])
        self.assertEqual(completed["status"], "done")

    def test_legacy_dumbbell_press_never_leaks_to_ui(self) -> None:
        quest = Quest(
            id=4,
            user_id=self.user.id,
            quest_date=date.today(),
            quest_type=QuestType.SIDE,
            exercise="dumbbell_press",
            target_reps=5,
            xp_reward=20,
            status=QuestStatus.ACTIVE,
            difficulty=1.0,
        )
        self.assertNotIn("dumbbell_press", format_quest_card(quest))
        self.assertNotIn("dumbbell_press", quest_button_label(quest))

    def test_ai_planner_openai_config_and_response_parsing(self) -> None:
        no_key = Settings(bot_token="x", ai_enabled=True, ai_provider="openai", ai_api_key=None)
        self.assertFalse(AIPlanner(no_key).available)

        with_key = Settings(bot_token="x", ai_enabled=True, ai_provider="openai", ai_api_key="sk-test")
        planner = AIPlanner(with_key)
        self.assertTrue(planner.available)
        self.assertEqual(planner.resolve_model(), "gpt-5.4-mini")

        text = planner._extract_responses_text(
            {
                "output": [
                    {
                        "content": [
                            {
                                "type": "output_text",
                                "text": '{"quests":[{"quest_type":"main","exercise":"pushups","target_reps":10,"xp_reward":20,"difficulty":1.0,"reason":"test"},{"quest_type":"side","exercise":"squats","target_reps":12,"xp_reward":16,"difficulty":0.8,"reason":"test"},{"quest_type":"side","exercise":"dumbbell_curls","target_reps":8,"xp_reward":14,"difficulty":0.7,"reason":"test"}]}',
                            }
                        ]
                    }
                ]
            }
        )
        quests = planner._parse_plan(text, date(2026, 5, 6), {"pushups", "squats", "dumbbell_curls"})
        self.assertEqual(len(quests), 3)
        self.assertEqual(quests[0]["exercise"], "pushups")

    def test_history_and_profile_formatting_after_completed_quest(self) -> None:
        quests = QuestRepository(self.db)
        quests.create_many(
            self.user.id,
            date.today(),
            [
                {
                    "quest_type": "main",
                    "exercise": "pushups",
                    "target_reps": 10,
                    "xp_reward": 20,
                    "difficulty": 1.0,
                }
            ],
        )
        quest = quests.get_today_for_user(self.user.id, date.today())[0]
        ProgressService(self.users, quests).complete_quest(self.user, quest, actual_reps=11, effort=Effort.NORMAL)

        progress = ProgressRepository(self.db)
        summary = progress.summary_for_user(self.user.id)
        recent = progress.recent_for_user(self.user.id)
        self.assertEqual(summary["completed_count"], 1)
        self.assertTrue(recent)
        self.assertIn("Журнал", format_history(self.user, summary, recent))
        self.assertIn("▰", format_profile(self.users.get_by_id(self.user.id)))

    def test_active_quest_reroll_repository_helpers(self) -> None:
        quests = QuestRepository(self.db)
        quests.create_many(
            self.user.id,
            date.today(),
            [
                {
                    "quest_type": "main",
                    "exercise": "pushups",
                    "target_reps": 10,
                    "xp_reward": 20,
                    "difficulty": 1.0,
                }
            ],
        )
        self.assertFalse(quests.has_done_for_user_date(self.user.id, date.today()))
        quests.delete_active_for_user_date(self.user.id, date.today())
        self.assertEqual(quests.get_today_for_user(self.user.id, date.today()), [])


if __name__ == "__main__":
    unittest.main()
