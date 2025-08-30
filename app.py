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

def _get_active_rules_for_market(now_dt, market):
    candidates = GenRule2D.query.filter(GenRule2D.active == True).all()
    picked = []
    for r in candidates:
        # 市场命中
        markets = _parse_markets_str(r.markets)
        if market not in markets:
            continue

        if r.use_slots:
            # 仅在 :50 且小时在选中列表时命中
            if now_dt.minute != 50:
                continue
            hour_list = [h.strip() for h in (r.slot_hours or '').split(',') if h.strip()]
            if str(now_dt.hour) not in hour_list:
                continue
        else:
            # 旧：时间区间
            if not (r.start_at <= now_dt <= r.end_at):
                continue

        picked.append(r)
    return picked

def generate_numbers_for_time(hour, minute):
    now = datetime.now(MY_TZ)
    draw_code = now.strftime(f"%Y%m%d/{hour:02d}{minute:02d}")
    markets = list("MPTSHEBKW")

    with app.app_context():
        for market in markets:
            # 已生成则跳过
            if DrawResult.query.filter_by(code=draw_code, market=market).first():
                continue

            rules = _get_active_rules_for_market(now, market)

            # 分类规则
            head_force, specials_force, any_force = set(), set(), set()
            head_excl, specials_excl = set(), set()

            for r in rules:
                num = (r.number or "").zfill(2)
                if r.action == "force":
                    if r.scope == "head":
                        head_force.add(num)
                    elif r.scope == "specials":
                        specials_force.add(num)
                    else:  # any
                        any_force.add(num)
                else:  # exclude
                    if r.scope == "head":
                        head_excl.add(num)
                    elif r.scope == "specials":
                        specials_excl.add(num)
                    else:  # any
                        head_excl.add(num); specials_excl.add(num)

            all_nums = [f"{i:02d}" for i in range(100)]
            available = set(all_nums)

            # 选头奖
            head_candidates = [n for n in head_force if n not in head_excl]
            if head_candidates:
                head = random.choice(head_candidates)
            else:
                # 若没有指定 head，可尝试用 any_force 顶上（优先满足“强制出现”）
                any_head_candidates = [n for n in any_force if n not in head_excl]
                if any_head_candidates:
                    head = random.choice(any_head_candidates)
                    any_force.discard(head)
                else:
                    pool = list(available - head_excl)
                    if not pool:
                        # 极端情况：被排除覆盖，放宽为全池
                        pool = list(available)
                    head = random.choice(pool)

            if head in available:
                available.remove(head)

            # 选特别奖（3个，不与 head 重复）
            specials = set()
            # 先放 specials_force
            for n in list(specials_force):
                if len(specials) >= 3: break
                if n == head or n in specials_excl: continue
                specials.add(n); available.discard(n)

            # 再放 any_force
            for n in list(any_force):
                if len(specials) >= 3: break
                if n == head or n in specials_excl: continue
                specials.add(n); available.discard(n)

            # 随机补齐
            while len(specials) < 3:
                pool = list(available - specials_excl - {head})
                if not pool:
                    # 极端：放宽为除了 head 以外任意
                    pool = [x for x in all_nums if x != head and x not in specials]
                pick = random.choice(pool)
                specials.add(pick)
                if pick in available:
                    available.remove(pick)

            specials_list = list(specials)
            random.shuffle(specials_list)

            head_num = int(head)
            size_type = "小" if 0 <= head_num <= 49 else "大"
            parity_type = "双" if head_num % 2 == 0 else "单"

            result = DrawResult(
                code=draw_code,
                market=market,
                head=head,
                specials=",".join(specials_list),
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

    number  = (request.form.get('number', '').strip() or '0').zfill(2)
    action  = request.form.get('action', 'exclude')
    scope   = request.form.get('scope', 'any')
    markets = ",".join(request.form.getlist('markets'))  # 多选
    note    = request.form.get('note', '')

    mode = request.form.get('mode', 'slots')  # 'slots' | 'range'
    use_slots = (mode == 'slots')

    if use_slots:
        # ✅ 按时段：收集小时（9..23），minute 固定 50
        slot_hours = request.form.getlist('slot_hours')  # ['9','10',...]
        slot_hours = sorted({h for h in slot_hours if h.isdigit() and 9 <= int(h) <= 23}, key=int)
        slot_hours_csv = ",".join(slot_hours)

        # 为兼容非空 start/end，这里给超宽范围
        start_dt = MY_TZ.localize(datetime(2000,1,1,0,0))
        end_dt   = MY_TZ.localize(datetime(2099,12,31,23,59))

        rule = GenRule2D(
            number=number, action=action, scope=scope, markets=markets,
            start_at=start_dt, end_at=end_dt,
            active=True, note=note,
            use_slots=True, slot_hours=slot_hours_csv
        )
    else:
        # 🟨 高级：按时间区间（保留旧逻辑）
        start_raw = request.form.get('start_at')
        end_raw   = request.form.get('end_at')
        start_dt = MY_TZ.localize(datetime.strptime(start_raw, "%Y-%m-%dT%H:%M"))
        end_dt   = MY_TZ.localize(datetime.strptime(end_raw,   "%Y-%m-%dT%H:%M"))
        if end_dt <= start_dt:
            end_dt = start_dt + timedelta(hours=12)

        rule = GenRule2D(
            number=number, action=action, scope=scope, markets=markets,
            start_at=start_dt, end_at=end_dt,
            active=True, note=note,
            use_slots=False, slot_hours=None
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

    now_dt = datetime.now(MY_TZ)
    start_today = now_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    end_today   = now_dt.replace(hour=23, minute=59, second=0, microsecond=0)

    start_today_local = start_today.strftime("%Y-%m-%dT%H:%M")
    end_today_local   = end_today.strftime("%Y-%m-%dT%H:%M")

    return render_template(
        'admin.html',
        draws=results,
        rules=rules,
        start_today_local=start_today_local,
        end_today_local=end_today_local
    )

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=False)
