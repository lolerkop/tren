# Fitness RPG Telegram Bot

Telegram-бот на Python 3.11+ и aiogram 3.x: RPG-фитнес система в стиле гильдии приключенцев.

## Возможности

- стартовый тест через `/start`: отжимания, подтягивания, брусья, приседания;
- главное inline-меню через `/menu`;
- дневная доска `/quest`: основной квест, side-квесты и случайные задания;
- случайные задания 1-2 раза в день в случайное время, после появления видны на Guild Board;
- настройки `/settings`: включение и выключение упражнений по группам мышц;
- журнал `/history`: последние выполнения, XP и суммарные повторения;
- безопасная пересборка активной доски по текущим настройкам;
- недельный Raid Boss по воскресеньям;
- ввод фактических повторений и сложности нагрузки;
- плавная адаптация нагрузки по результатам;
- OpenAI/GPT AI-планировщик через Responses API и Structured Outputs;
- XP, LVL, rank, сила, выносливость, streak;
- SQLite-хранилище;
- Docker-ready запуск для сервера.

Запрещенные активности не используются: бега, прогулок и берпи в генераторе нет. Жим гантелей исключен, потому что для него нужна скамья.

## Локальный запуск

```bash
python -m venv .venv
```

PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Установка:

```bash
pip install -r requirements.txt
```

Скопируйте `.env.example` в `.env` и заполните:

```env
BOT_TOKEN=123456:telegram_token
DATABASE_PATH=data/fitness_rpg.sqlite3

AI_ENABLED=true
AI_PROVIDER=openai
AI_API_KEY=sk-your-openai-key
AI_BASE_URL=https://api.openai.com/v1
AI_MODEL=gpt-5.4-mini
AI_TIMEOUT_SECONDS=35
```

Запуск:

```bash
python main.py
```

## Сервер через Docker

```bash
docker compose up -d --build
```

SQLite-файл будет лежать в `./data`, потому что `docker-compose.yml` монтирует эту папку в контейнер.

Подробная инструкция для VPS и обновлений через Git: [docs/server-deploy.md](docs/server-deploy.md).

## AI-планировщик

По умолчанию используется OpenAI Responses API. Модель возвращает план по строгой JSON-схеме, бот дополнительно валидирует упражнения, типы квестов, XP и нагрузку. Если API недоступен или ответ невалидный, бот автоматически использует локальный генератор.

Команда `/ai` проверяет текущую AI-конфигурацию и доступ к API.

## Проверки

```bash
python -m compileall main.py app tests
python -m unittest
```

## Структура

```text
app/
  db/          SQLite и репозитории
  handlers/    Telegram-команды, callbacks и FSM
  logic/       RPG-прогрессия, квесты, AI, random events
  utils/       форматирование и UI-переходы
tests/         unittest-проверки ключевой логики
main.py        точка входа
```
