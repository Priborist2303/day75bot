from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes
import json, os

TOKEN = "8231541683:AAG-ovgwaEqbb1eLHtiK9Xo7yTZZlzgw8TU"

TASKS = [
    "45 min workout",
    "45 min outdoor workout",
    "Progress photo",
    "10 pages reading",
    "Water",
    "Diet",
    "No alcohol / cheat meals",
]

DATA_FILE = "data.json"


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_user(data, user_id):
    key = str(user_id)
    if key not in data:
        data[key] = {
            "day": 1,
            "tasks": [False] * len(TASKS),
            "note": "",
            "notes": {},  # archived notes by day: {"1": "...", "2": "..."}
        }
    # upgrade old users (if you already ran the bot before adding notes)
    data[key].setdefault("note", "")
    data[key].setdefault("notes", {})
    # if tasks length changed in future, keep it safe
    if len(data[key].get("tasks", [])) != len(TASKS):
        data[key]["tasks"] = [False] * len(TASKS)
    return data[key]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await render(update, context)


async def render(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    user = get_user(data, update.effective_user.id)

    keyboard = []
    for i, task in enumerate(TASKS):
        mark = "✅" if user["tasks"][i] else "⬜"
        # double space after mark makes it look more "left-aligned" in Telegram UI
        keyboard.append([InlineKeyboardButton(f"{mark}  {task}", callback_data=str(i))])

    note = user.get("note", "").strip()
    text = f"DAY {user['day']}\n📝 Note: {note if note else '—'}"

    save_data(data)

    markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(text, reply_markup=markup)
    else:
        # edit existing message when pressing buttons
        await update.callback_query.message.edit_text(text, reply_markup=markup)


async def toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    data = load_data()
    user = get_user(data, q.from_user.id)

    idx = int(q.data)
    user["tasks"][idx] = not user["tasks"][idx]

    # if day completed -> congratulate + archive note + advance day
    if all(user["tasks"]):
        finished_day = user["day"]

        note = user.get("note", "").strip()
        user["notes"][str(finished_day)] = note
        user["note"] = ""

        user["day"] += 1
        user["tasks"] = [False] * len(TASKS)

        await q.message.reply_text(
            f"🎉 Congratulations!\n"
            f"✅ DAY {finished_day} completed.\n"
            f"➡️ Next: DAY {user['day']}"
        )

    save_data(data)
    await render(update, context)


async def add_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    user = get_user(data, update.effective_user.id)

    if not context.args:
        await update.message.reply_text(
            "📝 Use it like:\n"
            "/note Felt strong today, legs ok"
        )
        return

    user["note"] = " ".join(context.args).strip()
    save_data(data)
    await update.message.reply_text("📝 Note saved for today.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    user = get_user(data, update.effective_user.id)

    current_day = user["day"]
    notes = user.get("notes", {})
    today_note = user.get("note", "").strip()

    lines = ["📊 Progress\n"]

    # completed days
    for day_str in sorted(notes.keys(), key=lambda x: int(x)):
        lines.append(f"Day {day_str} ✅")
        note = notes.get(day_str)
        if note:
            lines.append(f"  📝 {note}")

    # current day
    lines.append(f"\nDay {current_day} ⏳")
    lines.append(f"  📝 {today_note if today_note else '—'}")

    await update.message.reply_text("\n".join(lines))

def main():
    if TOKEN == "PASTE_YOUR_TOKEN_HERE":
        raise RuntimeError("Please paste your real Telegram bot token into TOKEN.")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("note", add_note))
    app.add_handler(CommandHandler("status", status))    
    app.add_handler(CallbackQueryHandler(toggle))

    app.run_polling()


if __name__ == "__main__":
    main()
