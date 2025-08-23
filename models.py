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
    market = db.Column(db.String(1), nullable=False)  # M, K, T, ...
    head = db.Column(db.String(2), nullable=False)  # 头奖号码
    specials = db.Column(db.String(20), nullable=False)  # 特别奖
    size_type = db.Column(db.String(2), nullable=False)   # 大 or 小
    parity_type = db.Column(db.String(2), nullable=False) # 单 or 双
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(MY_TZ))
    __table_args__ = (db.UniqueConstraint('code', 'market', name='_code_market_uc'),)

class GenRule2D(db.Model):
    __tablename__ = 'gen_rule_2d'
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(2), nullable=False)      # '00'~'99'
    action = db.Column(db.String(8), nullable=False)       # 'force' | 'exclude'
    scope  = db.Column(db.String(10), nullable=False)      # 'head' | 'specials' | 'any'
    markets = db.Column(db.String(20), nullable=True)      # 逗号分隔，如 'M,P,T'；为空=全部
    start_at = db.Column(db.DateTime(timezone=True), nullable=False)
    end_at   = db.Column(db.DateTime(timezone=True), nullable=False)
    active   = db.Column(db.Boolean, nullable=False, default=True)
    note     = db.Column(db.String(100))
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
