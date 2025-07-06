from flask import Flask, request, render_template, redirect, session, url_for
from models import db, DrawResult
import os
import random
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "defaultsecret")
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# 登录页
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['password'] == os.environ.get("ADMIN_PASSWORD"):
            session['logged_in'] = True
            return redirect(url_for('admin_panel'))
        else:
            return "❌ 密码错误"
    return render_template('login.html')

# 登出
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect('/login')

@app.route('/admin/generate', methods=['POST'])
def generate_draws():
    if not session.get('logged_in'):
        return redirect('/login')

    now = datetime.now()
    timestamp = now.strftime("%Y%m%d/%H%M")  # 如：20250707/0010
    all_numbers = list(range(1, 100))
    
    markets = list('MKTSHEBKW')  # 9 个市场
    
    for m in markets:
        selected = random.sample(all_numbers, 6)
        formatted = [f"{n:02d}" for n in selected]
        head = formatted.pop(random.randint(0, 5))
        specials = ",".join(formatted)
        
        exists = DrawResult.query.filter_by(code=timestamp, market=m).first()
        if not exists:
            db.session.add(DrawResult(
                code=timestamp,
                market=m,
                head=head,
                specials=specials
            ))
    db.session.commit()
    return f"✅ 成功生成 {timestamp} 的号码"
