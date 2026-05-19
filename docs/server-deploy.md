# Server Deploy

## First Install

```bash
sudo apt update
sudo apt install -y git docker.io docker-compose-plugin
sudo systemctl enable --now docker
```

If `docker-compose-plugin` is unavailable on your VPS image, install the classic compose package:

```bash
sudo apt install -y git docker.io docker-compose
sudo systemctl enable --now docker
```

```bash
git clone https://github.com/lolerkop/tren.git fitness-rpg-bot
cd fitness-rpg-bot
cp .env.example .env
nano .env
```

Fill `.env`:

```env
BOT_TOKEN=your_telegram_token
DATABASE_PATH=data/fitness_rpg.sqlite3

AI_ENABLED=true
AI_PROVIDER=openai
AI_API_KEY=sk-your-openai-key
AI_BASE_URL=https://api.openai.com/v1
AI_MODEL=gpt-5.4-mini
AI_TIMEOUT_SECONDS=35
```

Start:

```bash
docker compose up -d --build || docker-compose up -d --build
docker compose logs -f --tail=100 || docker-compose logs -f --tail=100
```

## Update Bot

```bash
cd fitness-rpg-bot
bash scripts/deploy.sh
```

Equivalent manual update:

```bash
git pull --ff-only
docker compose up -d --build || docker-compose up -d --build
```

## Backup

SQLite lives in `data/fitness_rpg.sqlite3`.

```bash
mkdir -p backups
cp data/fitness_rpg.sqlite3 "backups/fitness_rpg_$(date +%F_%H-%M).sqlite3"
```

## Useful Commands

```bash
docker compose ps || docker-compose ps
docker compose logs -f --tail=100 || docker-compose logs -f --tail=100
docker compose restart || docker-compose restart
docker compose down || docker-compose down
```
