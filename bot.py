import logging, asyncio, random
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from db import save_bet, get_bets_by_game, clear_bets
from utils import get_game_id, get_dice_result, get_winners, format_result_text

logging.basicConfig(level=logging.INFO)

active_bets = {}  # 临时储存下注状态

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("🎲 欢迎来到 Sicbo 游戏！请输入『开始』开始新一局！")
        return

    game_id = get_game_id()
    context.chat_data["current_game_id"] = game_id
    context.chat_data["bets"] = []

    keyboard = [
        [InlineKeyboardButton("大 1:1", callback_data="bet:big"),
         InlineKeyboardButton("小 1:1", callback_data="bet:small")],
        [InlineKeyboardButton("单 1:1", callback_data="bet:odd"),
         InlineKeyboardButton("双 1:1", callback_data="bet:even")]
    ]
    await update.message.reply_photo(
        photo=open("images/start.jpg", "rb"),
        caption=f"🎯 第 {game_id} 局开始！请下注！\n⏳ 倒计时 20 秒",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await asyncio.sleep(20)
    await end_game(update, context)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data.startswith("bet:"):
        bet_type = data.split(":")[1]
        active_bets[user_id] = {"type": bet_type}
        await query.message.reply_text(f"你选择了 [{bet_type}]，请输入下注金额（如：10）")

async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()
    if user_id not in active_bets or not text.isdigit():
        return

    bet_info = active_bets[user_id]
    bet_info["amount"] = int(text)
    bet_info["username"] = update.message.from_user.mention_html()

    game_id = get_game_id()
    save_bet(update.effective_chat.id, game_id, user_id, bet_info)
    await update.message.reply_html(f"✅ 下注成功！{bet_info['type']} / RM{bet_info['amount']}\n等待开奖…")
    del active_bets[user_id]

async def end_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    game_id = get_game_id()
    bets = get_bets_by_game(chat_id, game_id)
    dice = get_dice_result()

    winners = get_winners(bets, dice)
    clear_bets(chat_id, game_id)

    caption = format_result_text(game_id, dice, winners)

    dice_images = [open(f"images/dice{d}.png", "rb") for d in dice]
    await context.bot.send_media_group(chat_id, [
        InputMediaPhoto(media=img) for img in dice_images
    ])
    await context.bot.send_message(chat_id, caption, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("📜 历史记录", callback_data="history")]
    ]))

async def handle_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("🕘 历史记录功能尚在开发中。")

def main():
    app = Application.builder().token("YOUR_TELEGRAM_BOT_TOKEN").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount))
    app.add_handler(CallbackQueryHandler(handle_callback, pattern="^bet:"))
    app.add_handler(CallbackQueryHandler(handle_history, pattern="^history$"))

    app.run_polling()

if __name__ == "__main__":
    main()
