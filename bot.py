import os, logging, asyncio, random, asyncpg
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

from utils import format_result_text, RESULT_MAP

logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv("TOKEN")
DB_URL = os.getenv("DATABASE_URL")

# 初始化数据库
async def init_db():
    conn = await asyncpg.connect(DB_URL)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS bets (
            id SERIAL PRIMARY KEY,
            chat_id BIGINT,
            game_id TEXT,
            user_id BIGINT,
            username TEXT,
            bet_type TEXT,
            amount NUMERIC,
            timestamp TIMESTAMPTZ
        );
    """)
    return conn

# /start 或 "开始"
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    app = context.application
    if not hasattr(app, "db"):
        app.db = await init_db()

    chat_id = update.effective_chat.id
    game_id = datetime.now().strftime("%y%m%d") + "001"
    context.chat_data["game_id"] = game_id

    keyboard = [
        [InlineKeyboardButton("大 1:1", callback_data="bet:big"),
         InlineKeyboardButton("小 1:1", callback_data="bet:small")],
        [InlineKeyboardButton("单 1:1", callback_data="bet:odd"),
         InlineKeyboardButton("双 1:1", callback_data="bet:even")]
    ]
    await update.message.reply_photo(
        photo=open("images/start.jpg", "rb"),
        caption=f"🎯 第 {game_id} 局开始！请下注！⏳ 倒计时 20 秒",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await asyncio.sleep(20)
    await end_game(update, context)

# 玩家点击下注按钮
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    user = update.callback_query.from_user
    data = update.callback_query.data
    if data.startswith("bet:"):
        context.user_data["bet_type"] = data.split(":")[1]
        await update.callback_query.message.reply_text(f"你选择了【{context.user_data['bet_type']}】，请输入下注金额：")

    elif data == "history":
        rows = await context.application.db.fetch(
            "SELECT game_id, bet_type, amount, timestamp FROM bets WHERE chat_id=$1 ORDER BY timestamp DESC LIMIT 10",
            update.effective_chat.id)
        if not rows:
            text = "🕘 暂无历史记录。"
        else:
            text = "🕘 最近 10 局下注记录：\n" + "\n".join(
                f"{r['timestamp'].strftime('%y%m%d')} 局 {r['bet_type']} RM{r['amount']}" for r in rows)
        await update.callback_query.message.reply_text(text)

# 玩家输入下注金额
async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "bet_type" not in context.user_data:
        return
    amount = update.message.text.strip()
    if not amount.isdigit():
        await update.message.reply_text("请输入有效数字金额！")
        return

    chat_id = update.effective_chat.id
    user = update.message.from_user
    game_id = context.chat_data.get("game_id", datetime.now().strftime("%y%m%d") + "001")

    await context.application.db.execute(
        "INSERT INTO bets(chat_id, game_id, user_id, username, bet_type, amount, timestamp) \
         VALUES($1,$2,$3,$4,$5,$6,now())",
        chat_id, game_id, user.id, user.mention_html(), context.user_data["bet_type"], amount)
    await update.message.reply_html(f"✅ 下注成功：{context.user_data['bet_type']} / RM{amount}")
    del context.user_data["bet_type"]

# 开奖流程
async def end_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    game_id = context.chat_data["game_id"]

    rows = await context.application.db.fetch(
        "SELECT username, bet_type, amount FROM bets WHERE chat_id=$1 AND game_id=$2",
        chat_id, game_id)

    dice = [random.randint(1, 6) for _ in range(3)]
    winners = [r for r in rows if RESULT_MAP[r["bet_type"]](sum(dice))]

    await context.bot.send_media_group(chat_id, [
        InputMediaPhoto(open(f"images/dice{d}.png", "rb")) for d in dice
    ])
    caption = format_result_text(game_id, dice, winners)
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("📜 历史记录", callback_data="history")]])
    await context.bot.send_message(chat_id, caption, reply_markup=keyboard)

# 启动入口
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.run_polling()

if __name__ == "__main__":
    main()
