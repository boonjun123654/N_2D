from flask import Flask, render_template, request, redirect
from models import db, DrawResult
import random
import os
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

@app.route('/admin', methods=['GET'])
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
    specials = [
        request.form['s1'],
        request.form['s2'],
        request.form['s3'],
        request.form['s4'],
        request.form['s5']
    ]
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

if __name__ == '__main__':
    app.run(debug=True)
