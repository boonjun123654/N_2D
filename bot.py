import asyncio
import random
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder

API_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# 存储下注
bets = {}
current_game_id = "250617001"

# 骰子图片路径
dice_images = {
    1: "🎲1",
    2: "🎲2",
    3: "🎲3",
    4: "🎲4",
    5: "🎲5",
    6: "🎲6",
}

@dp.message(F.text.lower() == "开始")
async def start_game(message: Message):
    bets.clear()
    keyboard = InlineKeyboardBuilder()
    for opt in ["大", "小", "单", "双"]:
        keyboard.button(text=opt, callback_data=f"sicbo:{opt}")
    await message.answer_photo(
        photo="https://your-image-url.com/sicbo.jpg",
        caption=f"🎲 第 {current_game_id} 局开始！请下注！倒计时 20 秒！",
        reply_markup=keyboard.as_markup()
    )
    asyncio.create_task(lock_bets_after_20s(message.chat.id))

@dp.callback_query(F.data.startswith("sicbo:"))
async def handle_bet_type(callback: CallbackQuery):
    bet_type = callback.data.split(":")[1]
    user_id = callback.from_user.id
    bets[user_id] = {"type": bet_type}
    await callback.answer(f"你选择了「{bet_type}」，请输入下注金额", show_alert=True)

@dp.message()
async def handle_amount(message: Message):
    user_id = message.from_user.id
    if user_id in bets and "amount" not in bets[user_id]:
        try:
            amount = float(message.text)
            bets[user_id]["amount"] = amount
            await message.reply(f"✅ 下注成功：{bets[user_id]['type']} RM{amount}")
        except:
            await message.reply("请输入有效金额")

async def lock_bets_after_20s(chat_id):
    await asyncio.sleep(20)
    d1, d2, d3 = random.randint(1, 6), random.randint(1, 6), random.randint(1, 6)
    total = d1 + d2 + d3
    result_type = []

    if total >= 11 and total <= 17:
        result_type.append("大")
    elif total >= 4 and total <= 10:
        result_type.append("小")
    if total % 2 == 0:
        result_type.append("双")
    else:
        result_type.append("单")

    winners = []
    for uid, data in bets.items():
        if data["type"] in result_type:
            winners.append((uid, data["amount"] * 2))

    dice_result = f"{dice_images[d1]} {dice_images[d2]} {dice_images[d3]}"
    caption = f"🎲 第 {current_game_id} 局开奖成绩\n{dice_result}\n"
    if winners:
        caption += "\n".join([f"🎉 <a href='tg://user?id={uid}'>玩家</a> 获得 RM{amt:.2f}" for uid, amt in winners])
    else:
        caption += "😢 本局无人中奖"

    history_btn = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="历史记录", callback_data="sicbo:history")]
    ])

    await bot.send_message(chat_id, caption, reply_markup=history_btn)

@dp.callback_query(F.data == "sicbo:history")
async def handle_history(callback: CallbackQuery):
    await callback.answer("暂未开放历史记录", show_alert=True)

if __name__ == "__main__":
    import asyncio
    async def main():
        await dp.start_polling(bot)
    asyncio.run(main())

