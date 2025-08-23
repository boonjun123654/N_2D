from flask import Flask,render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime,timedelta
from models import db, DrawResult, GenRule2D
import random, os
from pytz import timezone

MY_TZ = timezone("Asia/Kuala_Lumpur")

app = Flask(__name__)
app.permanent_session_lifetime = timedelta(hours=12)  # 登录有效期12小时
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

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
            session.permanent = True  # ✅ 让 session 受有效期控制
            session['logged_in'] = True
            return redirect(url_for('admin'))
        else:
            return render_template('login.html', error="❌ 用户名或密码错误")
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()  # 清除登录状态
    return redirect(url_for('login'))

def _parse_markets_str(s: str):
    if not s or not s.strip():
        return set(list("MPTSHEBKW"))  # 全部市场
    return set([x.strip().upper() for x in s.split(",") if x.strip()])

def generate_numbers_for_time(hour, minute):
    now = datetime.now(MY_TZ)
    draw_code = now.strftime(f"%Y%m%d/{hour:02d}{minute:02d}")
    markets = list("MPTSHEBKW")

    with app.app_context():
        for market in markets:
            exists = DrawResult.query.filter_by(code=draw_code, market=market).first()
            if not exists:
                numbers = random.sample(range(0, 100), 4)
                formatted = [f"{n:02d}" for n in numbers]
                head = formatted.pop(random.randint(0, 3))
                head_num = int(head.lstrip("0") or "0")

                size_type = "小" if 0 <= head_num <= 49 else "大"
                parity_type = "双" if head_num % 2 == 0 else "单"

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

if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    scheduler = BackgroundScheduler()
    for hour in range(9, 24):
        scheduler.add_job(
            generate_numbers_for_time,
            trigger=CronTrigger(hour=hour, minute=50, timezone=MY_TZ),
            args=[hour, 50],
            id=f"draw_{hour:02d}50",
            replace_existing=True
        )
    scheduler.start()
    print("✅ APScheduler started")

def _require_login():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return None

@app.route('/admin/rules/add', methods=['POST'])
def admin_add_rule():
    need = _require_login()
    if need: return need
    number = request.form.get('number', '').strip()
    action = request.form.get('action', 'exclude')
    scope  = request.form.get('scope', 'any')
    markets = ",".join(request.form.getlist('markets'))  # 多选
    note = request.form.get('note', '')

    # datetime-local -> 本地时间
    start_raw = request.form.get('start_at')
    end_raw   = request.form.get('end_at')
    # 格式：YYYY-MM-DDTHH:MM
    start_dt = MY_TZ.localize(datetime.strptime(start_raw, "%Y-%m-%dT%H:%M"))
    end_dt   = MY_TZ.localize(datetime.strptime(end_raw, "%Y-%m-%dT%H:%M"))

    number = number.zfill(2)
    rule = GenRule2D(
        number=number, action=action, scope=scope,
        markets=markets, start_at=start_dt, end_at=end_dt,
        active=True, note=note
    )
    db.session.add(rule)
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/admin/rules/<int:rid>/toggle', methods=['POST'])
def admin_toggle_rule(rid):
    need = _require_login()
    if need: return need
    r = GenRule2D.query.get_or_404(rid)
    r.active = not r.active
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/admin/rules/<int:rid>/delete', methods=['POST'])
def admin_delete_rule(rid):
    need = _require_login()
    if need: return need
    r = GenRule2D.query.get_or_404(rid)
    db.session.delete(r)
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/admin')
def admin():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    with app.app_context():
        results = DrawResult.query.order_by(DrawResult.code.desc(), DrawResult.market.asc()).limit(100).all()
        rules = GenRule2D.query.order_by(GenRule2D.created_at.desc()).all()
    # 供 datetime-local 默认值
    now_local = datetime.now(MY_TZ).strftime("%Y-%m-%dT%H:%M")
    return render_template('admin.html', draws=results, rules=rules, now_local=now_local)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=False)
