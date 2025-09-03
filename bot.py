import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
import sqlite3
import datetime

# -------------------------
# CONFIG
# -------------------------
import os
BOT_TOKEN = os.getenv("8486169884:AAGWEhcMg15C4f-jdiAEHPqnPseCLH9gWQM")DAILY_ENERGY = 100
TAP_POINTS = 10
REF_POINTS = 50

# -------------------------
# DATABASE SETUP
# -------------------------
conn = sqlite3.connect("game.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    points INTEGER DEFAULT 0,
    energy INTEGER DEFAULT 100,
    last_reset TEXT
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS referrals (
    referrer_id INTEGER,
    referred_id INTEGER
)""")

conn.commit()

# -------------------------
# RESET DAILY ENERGY
# -------------------------
def reset_daily_energy(user_id):
    today = datetime.date.today().isoformat()
    cursor.execute("SELECT last_reset FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if row:
        last_reset = row[0]
        if last_reset != today:
            cursor.execute("UPDATE users SET energy=?, last_reset=? WHERE user_id=?",
                           (DAILY_ENERGY, today, user_id))
            conn.commit()

# -------------------------
# COMMANDS
# -------------------------
async def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    cursor.execute("INSERT OR IGNORE INTO users (user_id, points, energy, last_reset) VALUES (?, 0, ?, ?)",
                   (user_id, DAILY_ENERGY, datetime.date.today().isoformat()))
    conn.commit()
    await update.message.reply_text("🚀 Welcome to ElonTrump Mini-Game!\nUse /tap, /balance, /leaderboard, /ref <friend_id>")

async def tap(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    reset_daily_energy(user_id)
    cursor.execute("SELECT energy FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if row and row[0] > 0:
        cursor.execute("UPDATE users SET points = points + ?, energy = energy - 1 WHERE user_id=?",
                       (TAP_POINTS, user_id))
        conn.commit()
        await update.message.reply_text(f"💥 Tap registered! +{TAP_POINTS} points.")
    else:
        await update.message.reply_text("⚡ Out of energy! Wait until tomorrow reset.")

async def balance(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    reset_daily_energy(user_id)
    cursor.execute("SELECT points, energy FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if row:
        await update.message.reply_text(f"📊 Points: {row[0]}\n⚡ Energy left: {row[1]}")
    else:
        await update.message.reply_text("❌ You are not registered. Use /start")

async def leaderboard(update: Update, context: CallbackContext):
    cursor.execute("SELECT user_id, points FROM users ORDER BY points DESC LIMIT 10")
    rows = cursor.fetchall()
    msg = "🏆 Top 10 Leaderboard 🏆\n\n"
    for i, row in enumerate(rows, 1):
        msg += f"{i}. User {row[0]} — {row[1]} pts\n"
    await update.message.reply_text(msg)

async def ref(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Usage: /ref <friend_id>")
        return
    try:
        friend_id = int(context.args[0])
        if friend_id == user_id:
            await update.message.reply_text("❌ You cannot refer yourself!")
            return
        cursor.execute("SELECT 1 FROM users WHERE user_id=?", (friend_id,))
        if cursor.fetchone():
            cursor.execute("SELECT 1 FROM referrals WHERE referrer_id=? AND referred_id=?", (user_id, friend_id))
            if cursor.fetchone():
                await update.message.reply_text("⚠️ You already referred this friend.")
            else:
                cursor.execute("INSERT INTO referrals (referrer_id, referred_id) VALUES (?, ?)", (user_id, friend_id))
                cursor.execute("UPDATE users SET points = points + ? WHERE user_id=?", (REF_POINTS, user_id))
                conn.commit()
                await update.message.reply_text(f"🎉 Referral successful! +{REF_POINTS} points.")
        else:
            await update.message.reply_text("❌ Friend not found (they must use /start first).")
    except ValueError:
        await update.message.reply_text("❌ Invalid friend_id")

# -------------------------
# MAIN
# -------------------------
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tap", tap))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("leaderboard", leaderboard))
    app.add_handler(CommandHandler("ref", ref))

    app.run_polling()

if _name_ == "_main_":
    main()