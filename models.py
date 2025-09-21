from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from pytz import timezone
from sqlalchemy.sql import func

MY_TZ = timezone("Asia/Kuala_Lumpur")
db = SQLAlchemy()

class DrawResult(db.Model):
    __tablename__ = 'draw_results'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), nullable=False)  # 例如 20250707/0010
    market = db.Column(db.String(32), nullable=False)  # M, K, T, ...
    head = db.Column(db.String(2), nullable=False)  # 头奖号码
    specials = db.Column(db.String(20), nullable=False)  # 特别奖
    size_type = db.Column(db.String(2), nullable=False)   # 大 or 小
    parity_type = db.Column(db.String(2), nullable=False) # 单 or 双
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(MY_TZ))
    __table_args__ = (db.UniqueConstraint('code', 'market', name='_code_market_uc'),)

class GenRule2D(db.Model):
    __tablename__ = 'gen_rule_2d'
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(2), nullable=False)
    action = db.Column(db.String(16), nullable=False)       # 'force' | 'exclude'
    scope  = db.Column(db.String(16), nullable=False)       # 'head' | 'specials' | 'any'
    markets = db.Column(db.String(32))                      # CSV，比如 "M,P,T"
    start_at = db.Column(db.DateTime(timezone=True), nullable=False)
    end_at   = db.Column(db.DateTime(timezone=True), nullable=False)
    active   = db.Column(db.Boolean, default=True)
    note     = db.Column(db.String(255))
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())

    # 🆕 新增：时段模式（9~23点的小时，固定 :50）
    use_slots  = db.Column(db.Boolean, default=False)
    slot_hours = db.Column(db.String(64))  # CSV，例如 "9,10,11"

class Bet2D(db.Model):
    __tablename__ = 'bets_2d'

    id         = db.Column(db.Integer, primary_key=True)
    order_code = db.Column(db.String(20))
    agent_id   = db.Column(db.Integer)
    market     = db.Column(db.String(10))
    code       = db.Column(db.String(20))  # YYYYMMDD/HHMM
    number     = db.Column(db.String(2))   # '00'~'99'
    amount_n1  = db.Column(db.Numeric)     # N1
    amount_n   = db.Column(db.Numeric)     # N
    amount_b   = db.Column(db.Numeric)     # 大
    amount_s   = db.Column(db.Numeric)     # 小
    amount_ds  = db.Column(db.Numeric)     # 单
    amount_ss  = db.Column(db.Numeric)     # 双
    status     = db.Column(db.String(16))
    created_at = db.Column(db.DateTime(timezone=True))
    locked_at  = db.Column(db.DateTime(timezone=True))

