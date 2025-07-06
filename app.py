from flask import Flask, request, render_template, redirect, session, url_for
from models import db, DrawResult
import os

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
