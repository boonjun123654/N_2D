import os
import random
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("BOT_TOKEN")
bets = {}
game_id = "250617001"
dice_emojis = {i: f"🎲{i}" for i in range(1, 7)}

logging.basicConfig(level=logging.INFO)

# ▶️ /开始 指令处理
async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    bets.clear()

    keyboard = [
        [InlineKeyboardButton("大", callback_data="bet:大"), InlineKeyboardButton("小", callback_data="bet:小")],
        [InlineKeyboardButton("单", callback_data="bet:单"), InlineKeyboardButton("双", callback_data="bet:双")],
    ]

    await context.bot.send_photo(
        chat_id=chat_id,
        photo="https://i.ibb.co/6R6nH9z/sicbo-start.jpg",
        caption=f"🎲 第 {game_id} 局开始！倒计时 20 秒！\n请选择下注类型👇",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    # 开始 20 秒倒计时
    context.job_queue.run_once(announce_result, 20, chat_id=chat_id)

# ✅ 玩家点击下注类型
async def choose_bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    bet_type = query.data.split(":")[1]
    bets[user_id] = {"type": bet_type}

    await query.message.reply_text(f"你选择了【{bet_type}】类型，请输入下注金额（例：10）")

# ✅ 玩家输入金额
async def input_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if user_id in bets and "amount" not in bets[user_id]:
        try:
            amount = float(text)
            bets[user_id]["amount"] = amount
            await update.message.reply_text(f"✅ 下注成功：{bets[user_id]['type']} RM{amount}")
        except:
            await update.message.reply_text("❌ 请输入有效的金额数字")

# 🎯 20 秒后开奖
async def announce_result(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id

    d1, d2, d3 = random.randint(1, 6), random.randint(1, 6), random.randint(1, 6)
    total = d1 + d2 + d3

    result_tags = []
    if 4 <= total <= 10:
        result_tags.append("小")
    if 11 <= total <= 17:
        result_tags.append("大")
    if total % 2 == 0:
        result_tags.append("双")
    else:
        result_tags.append("单")

    winners = []
    for uid, info in bets.items():
        if info.get("amount") and info["type"] in result_tags:
            prize = info["amount"] * 2
            winners.append((uid, prize))

    caption = f"🎲 第 {game_id} 局开奖成绩\n{dice_emojis[d1]} {dice_emojis[d2]} {dice_emojis[d3]}（总和 {total}）\n\n"
    if winners:
        for uid, prize in winners:
            caption += f"🎉 <a href='tg://user?id={uid}'>玩家</a> 获得 RM{prize:.2f}\n"
    else:
        caption += "😢 本局无人中奖"

    keyboard = [[InlineKeyboardButton("📜 历史记录", callback_data="history")]]
    await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

# ⏳ 点历史记录按钮
async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer("暂未开放历史记录功能", show_alert=True)

# 🚀 主程序入口
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("开始", start_game))
    app.add_handler(CallbackQueryHandler(choose_bet, pattern="^bet:"))
    app.add_handler(CallbackQueryHandler(history, pattern="^history$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, input_amount))

    app.run_polling()

if __name__ == "__main__":
    main()
