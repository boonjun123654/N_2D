from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class DrawResult(db.Model):
    __tablename__ = 'draw_results'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), nullable=False)  # 例如 20250707/0010
    market = db.Column(db.String(1), nullable=False)  # M, K, T, ...
    head = db.Column(db.String(2), nullable=False)  # 头奖号码
    specials = db.Column(db.String(20), nullable=False)  # 特别奖，例如 '55,46,87,99,10'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
