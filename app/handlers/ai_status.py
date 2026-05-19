from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.config import Settings
from app.keyboards import back_to_menu_keyboard
from app.logic.ai_planner import AIPlanner


def router(settings: Settings) -> Router:
    ai_router = Router()
    planner = AIPlanner(settings)

    @ai_router.message(Command("ai"))
    async def ai_status(message: Message) -> None:
        if not settings.ai_enabled:
            await message.answer(
                "🧠 <b>AI Planner</b>\n\n"
                "Статус: <b>выключен</b>\n\n"
                "Для OpenAI/GPT API укажи в .env:\n"
                "<code>AI_ENABLED=true</code>\n"
                "<code>AI_PROVIDER=openai</code>\n"
                "<code>AI_API_KEY=sk-...</code>\n"
                "<code>AI_MODEL=gpt-5.4-mini</code>",
                reply_markup=back_to_menu_keyboard(),
            )
            return

        if not planner.available:
            await message.answer(
                "🧠 <b>AI Planner</b>\n\n"
                "Статус: <b>включен, но не готов</b>\n"
                f"Provider: <code>{settings.ai_provider}</code>\n"
                f"Base URL: <code>{settings.ai_base_url}</code>\n\n"
                "Для OpenAI нужен <code>AI_API_KEY</code>.",
                reply_markup=back_to_menu_keyboard(),
            )
            return

        try:
            models = await planner.list_models()
        except Exception as error:
            await message.answer(
                "🧠 <b>AI Planner</b>\n\n"
                "Статус: <b>не подключен</b>\n"
                f"Provider: <code>{settings.ai_provider}</code>\n"
                f"Base URL: <code>{settings.ai_base_url}</code>\n"
                f"Модель: <code>{planner.resolve_model()}</code>\n\n"
                "Проверь API key, доступ к модели и сеть на сервере.\n"
                f"Ошибка: <code>{type(error).__name__}</code>",
                reply_markup=back_to_menu_keyboard(),
            )
            return

        visible_models = "\n".join(f"• <code>{model}</code>" for model in models[:8]) or "нет моделей"
        await message.answer(
            "🧠 <b>AI Planner</b>\n\n"
            "Статус: <b>подключен</b>\n"
            f"Provider: <code>{settings.ai_provider}</code>\n"
            f"Base URL: <code>{settings.ai_base_url}</code>\n"
            f"Выбранная модель: <code>{planner.resolve_model()}</code>\n\n"
            f"<b>Доступные модели:</b>\n{visible_models}",
            reply_markup=back_to_menu_keyboard(),
        )

    return ai_router
