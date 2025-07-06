from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import random, os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ==== 数据表定义 ====
class DrawResult(db.Model):
    __tablename__ = 'draw_results'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), nullable=False)
    market = db.Column(db.String(1), nullable=False)
    head = db.Column(db.String(2), nullable=False)
    specials = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('code', 'market', name='_code_market_uc'),)

# ==== 号码生成函数 ====
def generate_numbers_for_time(hour, minute):
    now = datetime.now()
    draw_code = now.strftime(f"%Y%m%d/{hour:02d}{minute:02d}")
    markets = list("MKTSHEBKW")

    with app.app_context():
        for market in markets:
            exists = DrawResult.query.filter_by(code=draw_code, market=market).first()
            if not exists:
                numbers = random.sample(range(1, 100), 6)
                formatted = [f"{n:02d}" for n in numbers]
                head = formatted.pop(random.randint(0, 5))
                specials = ",".join(formatted)
                result = DrawResult(code=draw_code, market=market, head=head, specials=specials)
                db.session.add(result)
        db.session.commit()
        print(f"✅ {draw_code} 号码生成完成")

# ==== 启动 APScheduler ====
scheduler = BackgroundScheduler()

# 每小时 00/10/20/30/40/50 启动（共 144 个）
for hour in range(0, 24):
    for minute in [0, 10, 20, 30, 40, 50]:
        scheduler.add_job(
            generate_numbers_for_time,
            trigger=CronTrigger(hour=hour, minute=minute),
            args=[hour, minute],
            id=f"draw_{hour:02d}{minute:02d}",
            replace_existing=True
        )

scheduler.start()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=False)
