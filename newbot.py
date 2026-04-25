import os
import random
import json
import asyncio
import time
from datetime import date

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("TELEGRAM_TOKEN")
DATA_FILE = "scores.json"


def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


data = load_data()

keyboard = [
    ["🎲 Ставка 10", "🎲 Ставка 25"],
    ["🎲 Ставка 50", "🔥 Ва-банк"],
    ["💰 Баланс", "🏆 Топ"],
    ["🎁 Ежедневный бонус", "💎 Квест"],
    ["📈 Профиль", "🔄 Сброс"],
]

markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def today_str():
    return str(date.today())


def get_user(user_id):
    user_id = str(user_id)

    if user_id not in data:
        data[user_id] = {
            "balance": 100,
            "xp": 0,
            "wins": 0,
            "losses": 0,
            "games": 0,
            "last_daily": 0,
            "daily_games": 0,
            "daily_quest_claimed": False,
            "daily_day": today_str(),
        }

    user = data[user_id]

    user.setdefault("balance", 100)
    user.setdefault("xp", 0)
    user.setdefault("wins", 0)
    user.setdefault("losses", 0)
    user.setdefault("games", 0)
    user.setdefault("last_daily", 0)
    user.setdefault("daily_games", 0)
    user.setdefault("daily_quest_claimed", False)
    user.setdefault("daily_day", today_str())

    if user["daily_day"] != today_str():
        user["daily_day"] = today_str()
        user["daily_games"] = 0
        user["daily_quest_claimed"] = False

    save_data(data)
    return user


def level_from_xp(xp):
    return xp // 100 + 1


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    get_user(update.message.from_user.id)

    await update.message.reply_text(
        "🎲 Dice Game\n\n"
        "Бросай кубик против бота.\n"
        "Победил — получил фан-очки.\n"
        "Проиграл — потерял ставку.\n\n"
        "🎰 Иногда победа даёт x2 или x3.\n"
        "💎 Каждый день сыграй 5 игр и получи награду.\n\n"
        "Это просто игра без реальных денег.",
        reply_markup=markup,
    )


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.message.from_user.id)
    await update.message.reply_text(f"💰 Баланс: {user['balance']} фан-очков")


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.message.from_user.id)

    await update.message.reply_text(
        f"📈 Профиль\n\n"
        f"💰 Баланс: {user['balance']}\n"
        f"⭐ Уровень: {level_from_xp(user['xp'])}\n"
        f"✨ XP: {user['xp']}\n"
        f"🎮 Игр: {user['games']}\n"
        f"✅ Побед: {user['wins']}\n"
        f"❌ Поражений: {user['losses']}\n\n"
        f"💎 Квест сегодня: {min(user['daily_games'], 5)}/5"
    )


async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top_users = sorted(
        data.items(),
        key=lambda x: x[1].get("balance", 0),
        reverse=True,
    )[:10]

    text = "🏆 Топ игроков:\n\n"

    if not top_users:
        text += "Пока никого нет."
    else:
        for i, (_, user) in enumerate(top_users, 1):
            text += (
                f"{i}. {user.get('balance', 0)} очков "
                f"| lvl {level_from_xp(user.get('xp', 0))}\n"
            )

    await update.message.reply_text(text)


async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.message.from_user.id)

    now = int(time.time())
    cooldown = 24 * 60 * 60
    last_daily = user.get("last_daily", 0)

    if now - last_daily < cooldown:
        left = cooldown - (now - last_daily)
        hours = left // 3600
        minutes = (left % 3600) // 60

        await update.message.reply_text(
            f"🎁 Бонус уже забран.\n"
            f"Приходи через {hours}ч {minutes}м."
        )
        return
	
    bonus = 50 + level_from_xp(user["xp"]) * 5
    user["balance"] += bonus
    user["last_daily"] = now

    save_data(data)

    await update.message.reply_text(
        f"🎁 Ежедневный бонус получен!\n\n"
        f"+{bonus} фан-очков\n"
        f"💰 Баланс: {user['balance']}"
    )


async def quest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.message.from_user.id)

    if user["daily_quest_claimed"]:
        await update.message.reply_text("💎 Квест уже выполнен сегодня ✅")
        return

    if user["daily_games"] < 5:
        await update.message.reply_text(
            f"💎 Ежедневный квест:\n"
            f"Сыграй 5 игр сегодня.\n\n"
            f"Прогресс: {user['daily_games']}/5\n"
            f"Награда: +75 очков и +50 XP"
        )
        return

    user["balance"] += 75
    user["xp"] += 50
    user["daily_quest_claimed"] = True

    save_data(data)

    await update.message.reply_text(
        "💎 Квест выполнен!\n\n"
        "+75 фан-очков\n"
        "+50 XP"
    )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)

    data[user_id] = {
        "balance": 100,
        "xp": 0,
        "wins": 0,
        "losses": 0,
        "games": 0,
        "last_daily": 0,
        "daily_games": 0,
        "daily_quest_claimed": False,
        "daily_day": today_str(),
    }

    save_data(data)

    await update.message.reply_text("🔄 Профиль сброшен. Баланс снова 100.")


async def play(update: Update, context: ContextTypes.DEFAULT_TYPE, bet):
    user = get_user(update.message.from_user.id)

    if bet == "all":
        bet = user["balance"]

    if bet <= 0:
        await update.message.reply_text("❌ У тебя нет очков для ставки.")
        return

    if user["balance"] < bet:
        await update.message.reply_text("❌ Недостаточно фан-очков.")
        return

    await update.message.reply_text(f"🎲 Ставка: {bet}\nТы бросаешь кубик...")

    user_dice = await update.message.reply_dice(emoji="🎲")
    user_roll = user_dice.dice.value

    await asyncio.sleep(3)

    bot_roll = random.randint(1, 6)

    user["games"] += 1
    user["daily_games"] += 1
    user["xp"] += 10

    multiplier = 1
    bonus_text = ""

    if user_roll > bot_roll:
        chance = random.randint(1, 100)

        if chance <= 5:
            multiplier = 3
            bonus_text = "\n🎰 СУПЕР-БОНУС x3!"
        elif chance <= 20:
            multiplier = 2
            bonus_text = "\n🎰 БОНУС x2!"

        win_amount = bet * multiplier
        user["balance"] += win_amount
        user["wins"] += 1
        user["xp"] += 25

        result = f"🎉 Победа! +{win_amount}{bonus_text}"

    elif user_roll < bot_roll:
        user["balance"] -= bet
        user["losses"] += 1

        result = f"😢 Поражение! -{bet}"

    else:
        result = "🤝 Ничья! Ставка возвращена."

    quest_hint = ""
    if user["daily_games"] >= 5 and not user["daily_quest_claimed"]:
        quest_hint = "\n\n💎 Квест готов! Нажми «💎 Квест», чтобы забрать награду."

    save_data(data)

    await update.message.reply_text(
        f"🎲 Ты: {user_roll}\n"
        f"🤖 Бот: {bot_roll}\n\n"
        f"{result}\n\n"
        f"💰 Баланс: {user['balance']}\n"
        f"⭐ Уровень: {level_from_xp(user['xp'])}\n"
        f"✨ XP: {user['xp']}\n"
        f"💎 Квест: {min(user['daily_games'], 5)}/5"
        f"{quest_hint}"
    )


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "🎲 Ставка 10":
        await play(update, context, 10)
    elif text == "🎲 Ставка 25":
        await play(update, context, 25)
    elif text == "🎲 Ставка 50":
        await play(update, context, 50)
    elif text == "🔥 Ва-банк":
        await play(update, context, "all")
    elif text == "💰 Баланс":
        await balance(update, context)
    elif text == "🏆 Топ":
        await top(update, context)
    elif text == "🎁 Ежедневный бонус":
        await daily(update, context)
    elif text == "💎 Квест":
        await quest(update, context)
    elif text == "📈 Профиль":
        await profile(update, context)
    elif text == "🔄 Сброс":
        await reset(update, context)
    else:
        await update.message.reply_text("Выбери действие кнопкой 👇", reply_markup=markup)


app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

print("Dice bot запущен 🎲")
app.run_polling()