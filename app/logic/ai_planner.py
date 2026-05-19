import json
import logging
from datetime import date
from typing import Any

import aiohttp

from app.config import Settings
from app.logic.exercises import EXERCISE_LABELS
from app.models import QuestType, User

logger = logging.getLogger(__name__)

OPENAI_DEFAULT_MODEL = "gpt-5.4-mini"
ALLOWED_EXERCISES = set(EXERCISE_LABELS)
FORBIDDEN_WORDS = {"бег", "пробеж", "прогул", "walk", "run", "running", "бурпи", "берпи", "burpee"}


class AIPlanner:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def available(self) -> bool:
        if not self.settings.ai_enabled:
            return False
        if self.settings.ai_provider == "openai" and not self.settings.ai_api_key:
            return False
        return True

    async def generate_daily(
        self,
        user: User,
        today: date,
        allowed_exercises: set[str] | None = None,
    ) -> list[dict] | None:
        if not self.available:
            return None

        try:
            allowed = allowed_exercises or set(ALLOWED_EXERCISES)
            content = await self._request_plan(user, today, allowed)
            return self._parse_plan(content, today, allowed)
        except Exception:
            logger.exception("AI quest generation failed. Falling back to local generator.")
            return None

    async def _request_plan(self, user: User, today: date, allowed_exercises: set[str]) -> str:
        if self.settings.ai_provider == "openai":
            return await self._request_openai_responses(user, today, allowed_exercises)
        return await self._request_chat_completions(user, today, allowed_exercises)

    async def _request_openai_responses(self, user: User, today: date, allowed_exercises: set[str]) -> str:
        payload = {
            "model": self.resolve_model(),
            "input": [
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": self._system_prompt(allowed_exercises)}],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": self._user_prompt(user, today)}],
                },
            ],
            "text": {"format": self._response_schema(allowed_exercises)},
            "temperature": 0.25,
            "max_output_tokens": 1200,
        }
        data = await self._post_json(f"{self.settings.ai_base_url}/responses", payload)
        return self._extract_responses_text(data)

    async def _request_chat_completions(self, user: User, today: date, allowed_exercises: set[str]) -> str:
        payload = {
            "model": self.resolve_model(),
            "temperature": 0.35,
            "max_tokens": 900,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": self._system_prompt(allowed_exercises)},
                {"role": "user", "content": self._user_prompt(user, today)},
            ],
        }
        data = await self._post_json(f"{self.settings.ai_base_url}/chat/completions", payload)
        return data["choices"][0]["message"]["content"]

    async def _post_json(self, url: str, payload: dict) -> dict:
        headers = {
            "Content-Type": "application/json",
            "X-Title": "Fitness RPG Bot",
        }
        if self.settings.ai_api_key:
            headers["Authorization"] = f"Bearer {self.settings.ai_api_key}"

        timeout = aiohttp.ClientTimeout(total=self.settings.ai_timeout_seconds)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, headers=headers, json=payload) as response:
                response.raise_for_status()
                return await response.json()

    def resolve_model(self) -> str:
        model = (self.settings.ai_model or "").strip()
        if model and model.lower() != "auto":
            return model
        if self.settings.ai_provider == "openai":
            return OPENAI_DEFAULT_MODEL
        return model or OPENAI_DEFAULT_MODEL

    async def list_models(self) -> list[str]:
        headers = {"Content-Type": "application/json"}
        if self.settings.ai_api_key:
            headers["Authorization"] = f"Bearer {self.settings.ai_api_key}"

        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(f"{self.settings.ai_base_url}/models", headers=headers) as response:
                response.raise_for_status()
                data = await response.json()

        return [
            item["id"]
            for item in data.get("data", [])
            if isinstance(item, dict) and item.get("id")
        ]

    def _system_prompt(self, allowed_exercises: set[str]) -> str:
        allowed = ", ".join(sorted(allowed_exercises))
        return (
            "Ты опытный тренер по домашним тренировкам и гейм-дизайнер фитнес RPG. "
            "Верни только JSON по заданной схеме. "
            "Цель: составить безопасные, плавные и персональные квесты на сегодня. "
            "Запрещены бег, прогулки, берпи, прыжковые кардио-задания и упражнения вне списка. "
            f"Разрешенные exercise id: {allowed}. "
            "В обычный день нужен 1 main и 2-3 side. В воскресенье можно 1 raid вместо обычной доски. "
            "Не назначай максимальные подходы: цель должна быть выполнимой дома, с запасом восстановления. "
            "Если упражнение слабое, уменьши repetitions, но не превращай день в наказание."
        )

    def _user_prompt(self, user: User, today: date) -> str:
        return (
            f"Дата: {today.isoformat()}, weekday={today.weekday()}.\n"
            f"Профиль: LVL={user.level}, rank={user.rank}, xp={user.xp}, "
            f"strength={user.strength}, endurance={user.endurance}, streak={user.streak}, "
            f"load_factor={user.load_factor}.\n"
            "Baseline за один подход: "
            f"pushups={user.baseline_pushups}, pullups={user.baseline_pullups}, "
            f"dips={user.baseline_dips}, squats={user.baseline_squats}.\n"
            "Сделай программу на сегодня с учетом восстановления и слабых мест."
        )

    def _response_schema(self, allowed_exercises: set[str]) -> dict:
        return {
            "type": "json_schema",
            "name": "fitness_rpg_daily_plan",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["quests"],
                "properties": {
                    "quests": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": [
                                "quest_type",
                                "exercise",
                                "target_reps",
                                "xp_reward",
                                "difficulty",
                                "reason",
                            ],
                            "properties": {
                                "quest_type": {
                                    "type": "string",
                                    "enum": [QuestType.MAIN.value, QuestType.SIDE.value, QuestType.RAID.value],
                                },
                                "exercise": {"type": "string", "enum": sorted(allowed_exercises)},
                                "target_reps": {"type": "integer", "minimum": 1, "maximum": 500},
                                "xp_reward": {"type": "integer", "minimum": 5, "maximum": 250},
                                "difficulty": {"type": "number", "minimum": 0.4, "maximum": 2.2},
                                "reason": {"type": "string"},
                            },
                        },
                    }
                },
            },
        }

    def _parse_plan(self, content: str, today: date, allowed_exercises: set[str]) -> list[dict]:
        data = self._loads_json(content)
        raw_quests = data.get("quests", [])
        if not isinstance(raw_quests, list):
            raise ValueError("AI response must contain quests list.")

        quests = [self._normalize_quest(item, allowed_exercises) for item in raw_quests]
        self._validate_shape(quests, today)
        return quests

    def _loads_json(self, content: str) -> dict[str, Any]:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            cleaned = cleaned.removeprefix("json").strip()
        return json.loads(cleaned)

    def _extract_responses_text(self, data: dict) -> str:
        if data.get("output_text"):
            return data["output_text"]

        for item in data.get("output", []):
            if not isinstance(item, dict):
                continue
            for content in item.get("content", []):
                if not isinstance(content, dict):
                    continue
                if content.get("type") in {"output_text", "text"} and content.get("text"):
                    return content["text"]
        raise ValueError("OpenAI response did not contain output text.")

    def _normalize_quest(self, item: Any, allowed_exercises: set[str]) -> dict:
        if not isinstance(item, dict):
            raise ValueError("Quest item must be an object.")

        quest_type = str(item.get("quest_type", "")).lower()
        exercise = str(item.get("exercise", "")).lower()
        target_reps = int(item.get("target_reps", 0))
        xp_reward = int(item.get("xp_reward", 0))
        difficulty = float(item.get("difficulty", 1.0))

        if quest_type not in {QuestType.MAIN.value, QuestType.SIDE.value, QuestType.RAID.value}:
            raise ValueError(f"Invalid quest_type: {quest_type}")
        if exercise not in allowed_exercises:
            raise ValueError(f"Invalid exercise: {exercise}")
        if any(word in exercise for word in FORBIDDEN_WORDS):
            raise ValueError(f"Forbidden exercise: {exercise}")

        return {
            "quest_type": quest_type,
            "exercise": exercise,
            "target_reps": max(1, min(500, target_reps)),
            "xp_reward": max(5, min(250, xp_reward)),
            "difficulty": round(max(0.4, min(2.2, difficulty)), 2),
        }

    def _validate_shape(self, quests: list[dict], today: date) -> None:
        if not quests:
            raise ValueError("AI returned empty plan.")

        if today.weekday() == 6:
            if not any(quest["quest_type"] == QuestType.RAID.value for quest in quests):
                raise ValueError("Sunday plan must include a raid quest.")
            return

        main_count = sum(quest["quest_type"] == QuestType.MAIN.value for quest in quests)
        side_count = sum(quest["quest_type"] == QuestType.SIDE.value for quest in quests)
        if main_count != 1 or side_count not in {2, 3}:
            raise ValueError("Daily plan must contain 1 main and 2-3 side quests.")
