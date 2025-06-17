bets_db = {}

def save_bet(chat_id, game_id, user_id, bet_info):
    key = f"{chat_id}:{game_id}"
    if key not in bets_db:
        bets_db[key] = []
    bets_db[key].append(bet_info)

def get_bets_by_game(chat_id, game_id):
    key = f"{chat_id}:{game_id}"
    return bets_db.get(key, [])

def clear_bets(chat_id, game_id):
    key = f"{chat_id}:{game_id}"
    bets_db.pop(key, None)
