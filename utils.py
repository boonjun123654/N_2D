import random
from datetime import datetime

def get_game_id():
    return datetime.now().strftime("%y%m%d") + "001"

def get_dice_result():
    return [random.randint(1, 6) for _ in range(3)]

def get_winners(bets, dice):
    total = sum(dice)
    result = {
        "big": 11 <= total <= 17,
        "small": 4 <= total <= 10,
        "odd": total % 2 == 1,
        "even": total % 2 == 0,
    }
    winners = [b for b in bets if result.get(b["type"], False)]
    return winners

def format_result_text(game_id, dice, winners):
    total = sum(dice)
    winner_text = "无人中奖 😢"
    if winners:
        winner_text = "\n".join(
            f"{w['username']} 赢得 RM{w['amount'] * 2}"
            for w in winners
        )
    return f"🎲 第 {game_id} 局开奖成绩：{dice}（总点数 {total}）\n🎉 恭喜本局赢家：\n{winner_text}"
