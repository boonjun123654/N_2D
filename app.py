from flask import Flask,render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime,timedelta, time as dtime
from models import db, DrawResult, GenRule2D,Bet2D
import random, os
from pytz import timezone
from sqlalchemy import func, and_,text

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

def _range_from_request():
    """
    从 /admin?date=YYYY-MM-DD&start=HH:MM&end=HH:MM 读取筛选条件，
    在 Asia/Kuala_Lumpur 生成对应的本地时间窗口，再转成 UTC 返回。
    同时返回用于模板回显的字符串。
    """
    tz = MY_TZ
    date_str  = request.args.get('date', '')
    start_str = request.args.get('start', '00:00')
    end_str   = request.args.get('end',   '23:59')

    # 默认：今天
    now_local = datetime.now(tz)
    if not date_str:
        date_str = now_local.strftime('%Y-%m-%d')

    # 解析
    y, m, d = [int(x) for x in date_str.split('-')]
    sh, sm  = [int(x) for x in start_str.split(':')]
    eh, em  = [int(x) for x in end_str.split(':')]

    # 构造本地带时区时间（pytz 建议 localize）
    start_local = tz.localize(datetime(y, m, d, sh, sm, 0, 0))
    end_local   = tz.localize(datetime(y, m, d, eh, em, 59, 999000))

    # 转 UTC
    start_utc = start_local.astimezone(timezone("UTC"))
    end_utc   = end_local.astimezone(timezone("UTC"))

    # 回显用
    sel_date  = date_str
    sel_start = f"{sh:02d}:{sm:02d}"
    sel_end   = f"{eh:02d}:{em:02d}"

    return start_utc, end_utc, sel_date, sel_start, sel_end

def _today_range_utc():
    now_local = datetime.now(MY_TZ)
    start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    end_local   = now_local.replace(hour=23, minute=59, second=59, microsecond=999000)
    start_utc = start_local.astimezone(timezone("UTC"))
    end_utc   = end_local.astimezone(timezone("UTC"))
    return start_utc, end_utc

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

        if getattr(r, 'use_slots', False):
            # ✅ 按时段规则：必须同时满足“当天窗口 + 分钟:50 + 小时命中”
            if not (r.start_at <= now_dt <= r.end_at):
                continue
            if now_dt.minute != 50:
                continue
            hour_list = [h.strip() for h in (r.slot_hours or '').split(',') if h.strip()]
            if str(now_dt.hour) not in hour_list:
                continue
        else:
            # 兼容旧：时间区间
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

    # 仅按时段：收集小时（9..23），minute 固定 50
    slot_hours = request.form.getlist('slot_hours')  # ['9','10',...]
    slot_hours = sorted({h for h in slot_hours if h.isdigit() and 9 <= int(h) <= 23}, key=int)
    slot_hours_csv = ",".join(slot_hours)

    # ✅ 开始/结束：默认当天（按 Asia/Kuala_Lumpur）
    now_dt = datetime.now(MY_TZ)
    start_dt = now_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    end_dt   = now_dt.replace(hour=23, minute=59, second=0, microsecond=0)

    rule = GenRule2D(
        number=number, action=action, scope=scope, markets=markets,
        start_at=start_dt, end_at=end_dt,
        active=True, note=note,
        use_slots=True, slot_hours=slot_hours_csv
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

        # === 读取“日期 + 时段小时” ===
        sel_date = request.args.get("date")            # "2025-09-15"
        sel_hour = request.args.get("hour", type=int)  # 9..23

        # 默认：今天当前小时（限定 9..23）
        if not sel_date or sel_hour is None:
            now_local = datetime.now(MY_TZ)
            sel_date = now_local.strftime("%Y-%m-%d")
            sel_hour = now_local.hour
        if sel_hour < 9:  sel_hour = 9
        if sel_hour > 23: sel_hour = 23

        # === 构造基于 code 的筛选键 ===
        date_nodash = sel_date.replace('-', '')        # "20250915"
        hh = f"{sel_hour:02d}"                         # "09".."23"
        code_prefix = f"{date_nodash}/"                # "20250915/"

        # === 号码维度统计（按 code 小时）===
        rows = db.session.execute(text("""
          SELECT number,
                 COALESCE(SUM(amount_n1),0) AS sum_n1,
                 COALESCE(SUM(amount_n),0)  AS sum_n
          FROM bets_2d
          WHERE status='active'
            AND code LIKE :prefix || '%'
            AND substr(code, 10, 2) = :hh
          GROUP BY number
          ORDER BY number
        """), {"prefix": code_prefix, "hh": hh}).mappings().all()

        per_number = [{
            "number": str(r["number"]).zfill(2),
            "n1": float(r["sum_n1"]),
            "n":  float(r["sum_n"]),
            # 预计中奖金额（头奖）：N1*50 + N*28
            "est": float(r["sum_n1"])*50.0 + float(r["sum_n"])*28.0
        } for r in rows]

        # === 大小/单双合计（同一 code 小时窗口）===
        tot = db.session.execute(text("""
          SELECT COALESCE(SUM(amount_b),0)  AS b,
                 COALESCE(SUM(amount_s),0)  AS s,
                 COALESCE(SUM(amount_ds),0) AS ds,
                 COALESCE(SUM(amount_ss),0) AS ss
          FROM bets_2d
          WHERE status='active'
            AND code LIKE :prefix || '%'
            AND substr(code, 10, 2) = :hh
        """), {"prefix": code_prefix, "hh": hh}).mappings().one()

        b  = float(tot.get("b", 0)  or 0)
        s  = float(tot.get("s", 0)  or 0)
        ds = float(tot.get("ds", 0) or 0)
        ss = float(tot.get("ss", 0) or 0)

        bsds = {
          "B":  {"amt": b,  "est": b  * 0.90},
          "S":  {"amt": s,  "est": s  * 0.90},
          "DS": {"amt": ds, "est": ds * 0.90},
          "SS": {"amt": ss, "est": ss * 0.90},
        }

    return render_template('admin.html',
                           draws=results,
                           rules=rules,
                           per_number=per_number,
                           bsds=bsds,
                           sel_date=sel_date,
                           sel_hour=sel_hour)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=False)
