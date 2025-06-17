from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
import random, asyncio

active_bets = {}

async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("大 1:1", callback_data="sicbo:big"),
         InlineKeyboardButton("小 1:1", callback_data="sicbo:small")],
        [InlineKeyboardButton("单 1:1", callback_data="sicbo:odd"),
         InlineKeyboardButton("双 1:1", callback_data="sicbo:even")]
    ]
    await update.message.reply_photo(
        photo="https://example.com/sicbo_start.jpg",  # 替换为你的图
        caption="🎲 开始下注！请选择下注类型（20秒内）",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    # 启动倒计时 20 秒后开奖
    asyncio.create_task(lock_bets_and_roll(update.effective_chat.id, context))

async def handle_type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat.id
    bet_type = query.data.split(":")[1]

    # 存储用户下注类型（等待金额）
    active_bets[chat_id] = {"user_id": user_id, "type": bet_type}
    await query.answer()
    await query.message.reply_text("请输入下注金额（数字）")

async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    if chat_id not in active_bets or active_bets[chat_id]["user_id"] != user_id:
        return
    try:
        amount = float(update.message.text)
        active_bets[chat_id]["amount"] = amount
        await update.message.reply_text("✅ 下注成功！请等待开奖...")
    except ValueError:
        await update.message.reply_text("请输入有效金额（数字）")

async def lock_bets_and_roll(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    await asyncio.sleep(20)
    dice = [random.randint(1, 6) for _ in range(3)]
    total = sum(dice)
    emoji = {1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅"}
    result_text = f"🎲 骰子结果：{' '.join([emoji[d] for d in dice])}（共 {total} 点）"

    # 判断是否中奖
    bet = active_bets.get(chat_id)
    if bet:
        outcome = ""
        if bet["type"] == "big" and 11 <= total <= 17:
            outcome = "✅ 恭喜，买大赢了！"
        elif bet["type"] == "small" and 4 <= total <= 10:
            outcome = "✅ 恭喜，买小赢了！"
        elif bet["type"] == "odd" and total % 2 == 1:
            outcome = "✅ 恭喜，买单赢了！"
        elif bet["type"] == "even" and total % 2 == 0:
            outcome = "✅ 恭喜，买双赢了！"
        else:
            outcome = "❌ 很遗憾，您未中奖。"

        await context.bot.send_message(chat_id, result_text + "\n" + outcome)
        del active_bets[chat_id]
    else:
        await context.bot.send_message(chat_id, result_text + "\n没有有效下注记录。")

app = ApplicationBuilder().token("YOUR_BOT_TOKEN").build()

app.add_handler(CommandHandler("start", start_game))
app.add_handler(CallbackQueryHandler(handle_type_selection, pattern="^sicbo:"))
app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_amount))

app.run_polling()