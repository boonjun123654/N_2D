from flask import Flask,render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import random, os
from pytz import timezone

MY_TZ = timezone("Asia/Kuala_Lumpur")

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

app.secret_key = os.environ.get("SECRET_KEY", "default_secret_key")  # session 加密

@app.route('/')
def index():
    # 如果已经登录，直接去 /admin，否则去 /login
    if session.get('logged_in'):
        return redirect(url_for('admin'))
    else:
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        admin_user = os.environ.get("ADMIN_USERNAME")
        admin_pass = os.environ.get("ADMIN_PASSWORD")

        if username == admin_user and password == admin_pass:
            session['logged_in'] = True
            return redirect(url_for('admin'))
        else:
            return render_template('login.html', error="❌ 用户名或密码错误")
    
    return render_template('login.html')

def generate_numbers_for_time(hour, minute):
    now = datetime.now(MY_TZ)
    draw_code = now.strftime(f"%Y%m%d/{hour:02d}{minute:02d}")
    markets = list("MPTSHEBKW")

    with app.app_context():
        for market in markets:
            exists = DrawResult.query.filter_by(code=draw_code, market=market).first()
            if not exists:
                numbers = random.sample(range(1, 100), 6)
                formatted = [f"{n:02d}" for n in numbers]
                head = formatted.pop(random.randint(0, 5))
                head_num = int(head)

                # 判断大/小
                size_type = "大" if head_num >= 50 else "小"

                # 判断单/双
                parity_type = "单" if head_num % 2 == 1 else "双"

                specials = ",".join(formatted)

                result = DrawResult(
                    code=draw_code,
                    market=market,
                    head=head,
                    specials=specials,
                    size_type=size_type,
                    parity_type=parity_type
                )
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
            trigger=CronTrigger(hour=hour, minute=minute, timezone=MY_TZ),
            args=[hour, minute],
            id=f"draw_{hour:02d}{minute:02d}",
            replace_existing=True
        )

scheduler.start()

@app.route('/admin')
def admin():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    with app.app_context():
        results = DrawResult.query.order_by(DrawResult.code.desc(), DrawResult.market.asc()).limit(100).all()
    return render_template('admin.html', draws=results)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=False)
