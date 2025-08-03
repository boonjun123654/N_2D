from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from pytz import timezone

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
