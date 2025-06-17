import os
import random
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
bets = {}
game_id = "250617001"

dice_emojis = {
    1: "🎲1", 2: "🎲2", 3: "🎲3", 4: "🎲4", 5: "🎲5", 6: "🎲6"
}

logging.basicConfig(level=logging.INFO)

async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    bets.clear()
    keyboard = [
        [InlineKeyboardButton("大", callback_data="bet:大"),
         InlineKeyboardButton("小", callback_data="bet:小")],
        [InlineKeyboardButton("单", callback_data="bet:单"),
         InlineKeyboardButton("双", callback_data="bet:双")]
    ]
    await context.bot.send_photo(
        chat_id=chat_id,
        photo="https://i.ibb.co/6R6nH9z/sicbo-start.jpg",
        caption=f"🎲 第 {game_id} 局开始！倒计时 20 秒！\n请选择下注类型👇",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    context.job_queue.run_once(lock_bets, 20, chat_id=chat_id)

async def choose_bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    bet_type = query.data.split(":")[1]
    bets[user_id] = {"type": bet_type}
    await query.answer(f"你选择了『{bet_type}』，请输入下注金额", show_alert=True)

async def input_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    if user_id in bets and "amount" not in bets[user_id]:
        try:
            amount = float(text)
            bets[user_id]["amount"] = amount
            await update.message.reply_text(f"✅ 下注成功：{bets[user_id]['type']} RM{amount}")
        except:
            await update.message.reply_text("❌ 请输入有效金额")

async def lock_bets(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    d1, d2, d3 = random.randint(1,6), random.randint(1,6), random.randint(1,6)
    total = d1 + d2 + d3
    result = []
    if 4 <= total <= 10: result.append("小")
    if 11 <= total <= 17: result.append("大")
    if total % 2 == 0: result.append("双")
    else: result.append("单")

    winners = []
    for uid, data in bets.items():
        if data["type"] in result:
            winners.append((uid, data["amount"] * 2))

    result_text = f"🎲 第 {game_id} 局开奖成绩\n{dice_emojis[d1]} {dice_emojis[d2]} {dice_emojis[d3]}（总和 {total}）\n"
    if winners:
        for uid, prize in winners:
            result_text += f"🎉 <a href='tg://user?id={uid}'>玩家</a> 获得 RM{prize:.2f}\n"
    else:
        result_text += "😢 本局无人中奖"

    keyboard = [[InlineKeyboardButton("📜 历史记录", callback_data="history")]]
    await context.bot.send_message(chat_id=chat_id, text=result_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer("暂未开放历史记录", show_alert=True)

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("开始", start_game))
    app.add_handler(CallbackQueryHandler(choose_bet, pattern="^bet:"))
    app.add_handler(CallbackQueryHandler(history, pattern="^history$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, input_amount))
    app.run_polling()

if __name__ == "__main__":
    main()
