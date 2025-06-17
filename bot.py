import logging
import os
import random
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BET_OPTIONS = [
    ("big", "大"),
    ("small", "小"),
    ("odd", "单"),
    ("even", "双"),
]

DICE_EMOJI = {
    1: "\u2680",
    2: "\u2681",
    3: "\u2682",
    4: "\u2683",
    5: "\u2684",
    6: "\u2685",
}


def start(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    game_id = datetime.now().strftime("%d%m%H%M%S")
    context.chat_data["game_id"] = game_id
    context.chat_data["bets"] = {}

    keyboard = [
        [InlineKeyboardButton(text, callback_data=f"bet:{key}")]
        for key, text in BET_OPTIONS
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        f"{game_id}局开始！倒计时20秒！",
        reply_markup=reply_markup,
    )

    context.job_queue.run_once(
        end_game,
        20,
        chat_id=chat_id,
        name=str(chat_id),
        data={"username": update.effective_user.username or update.effective_user.first_name}
    )


def bet_choice(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    bet_key = query.data.split(":")[1]
    context.user_data["bet_key"] = bet_key
    query.edit_message_reply_markup(None)
    query.message.reply_text("请输入下注金额：")
    context.user_data["await_amount"] = True


def amount_input(update: Update, context: CallbackContext) -> None:
    if not context.user_data.get("await_amount"):
        return
    try:
        amount = float(update.message.text)
    except ValueError:
        update.message.reply_text("请输入数字金额")
        return
    context.user_data["amount"] = amount
    context.user_data["await_amount"] = False
    update.message.reply_text("下注成功，等待开奖…")


def end_game(context: CallbackContext) -> None:
    chat_id = context.job.chat_id
    game_id = context.chat_data.get("game_id", "")
    user_bet = context.user_data.get("bet_key")
    amount = context.user_data.get("amount")
    dice = [random.randint(1, 6) for _ in range(3)]
    total = sum(dice)

    result_text = "".join(DICE_EMOJI[d] for d in dice)
    win = False
    if user_bet and amount:
        if user_bet == "big" and total >= 11:
            win = True
        elif user_bet == "small" and total <= 10:
            win = True
        elif user_bet == "odd" and total % 2 == 1:
            win = True
        elif user_bet == "even" and total % 2 == 0:
            win = True
    mention = context.chat_data.get("winner")
    if win:
        mention = context.job.data.get("username") if context.job.data else "玩家"
        result_line = f"{game_id}局开奖成绩 {result_text} @{mention} 赢得 {amount}"
    else:
        result_line = f"{game_id}局开奖成绩 {result_text} 没有赢家"
    keyboard = [[InlineKeyboardButton("历史记录", callback_data="history")]]
    context.bot.send_message(
        chat_id=chat_id,
        text=result_line,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


def history(update: Update, context: CallbackContext) -> None:
    update.callback_query.answer()
    amount = context.user_data.get("amount")
    bet = context.user_data.get("bet_key")
    update.callback_query.message.reply_text(
        f"上局下注：{bet} {amount}")


def main() -> None:
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("BOT_TOKEN missing")
        return
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Regex("^开始$"), start))
    app.add_handler(CallbackQueryHandler(bet_choice, pattern="^bet:"))
    app.add_handler(CallbackQueryHandler(history, pattern="^history$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, amount_input))

    app.run_polling()


if __name__ == "__main__":
    main()
