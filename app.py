from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import random
import os
import atexit

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class DrawResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    draw_no = db.Column(db.String(20), unique=True, nullable=False)  # e.g., 20250706/9
    draw_time = db.Column(db.DateTime, nullable=False)
    head = db.Column(db.String(2), nullable=False)
    specials = db.Column(db.ARRAY(db.String(2)), nullable=False)
    mode = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

@app.route('/admin')
def admin_panel():
    draws = DrawResult.query.order_by(DrawResult.draw_time.desc()).all()
    return render_template('admin.html', draws=draws)

@app.route('/admin/generate', methods=['POST'])
def generate_draw():
    draw_no = request.form['draw_no']
    draw_time = request.form['draw_time']
    numbers = random.sample(range(1, 100), 6)
    specials = [f"{n:02d}" for n in numbers]
    head = specials.pop(random.randint(0, 5))
    draw = DrawResult(
        draw_no=draw_no,
        draw_time=datetime.strptime(draw_time, "%Y-%m-%dT%H:%M"),
        head=head,
        specials=specials,
        mode='auto'
    )
    db.session.add(draw)
    db.session.commit()
    return redirect('/admin')

@app.route('/admin/manual', methods=['POST'])
def manual_draw():
    draw_no = request.form['draw_no']
    draw_time = request.form['draw_time']
    head = request.form['head']
    specials = [request.form['s1'], request.form['s2'], request.form['s3'], request.form['s4'], request.form['s5']]
    draw = DrawResult(
        draw_no=draw_no,
        draw_time=datetime.strptime(draw_time, "%Y-%m-%dT%H:%M"),
        head=head,
        specials=specials,
        mode='manual'
    )
    db.session.add(draw)
    db.session.commit()
    return redirect('/admin')

def auto_draw_job():
    now = datetime.now()
    hour = now.hour
    minute = now.minute
    if hour < 9 or hour > 23 or minute != 50:
        return
    draw_no = f"{now.strftime('%Y%m%d')}/{hour}"
    with app.app_context():
        if DrawResult.query.filter_by(draw_no=draw_no).first():
            return
        all_numbers = [f"{n:02d}" for n in range(1, 100)]
        selected = random.sample(all_numbers, 6)
        head = random.choice(selected)
        specials = [n for n in selected if n != head][:5]
        draw = DrawResult(
            draw_no=draw_no,
            draw_time=now,
            head=head,
            specials=specials,
            mode='auto'
        )
        db.session.add(draw)
        db.session.commit()
        print(f"[✅ 自动开奖] {draw_no} | Head: {head}, Specials: {specials}")

scheduler = BackgroundScheduler()
scheduler.add_job(func=auto_draw_job, trigger='interval', minutes=1)
scheduler.start()
atexit.register(lambda: scheduler.shutdown())

if __name__ == '__main__':
    app.run(debug=True)
