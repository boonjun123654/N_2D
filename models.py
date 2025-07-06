from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class DrawResult(db.Model):
    __tablename__ = 'draw_results'
    id = db.Column(db.Integer, primary_key=True)
    draw_no = db.Column(db.String(20), unique=True, nullable=False)
    draw_time = db.Column(db.DateTime, nullable=False)
    head = db.Column(db.String(2), nullable=False)
    specials = db.Column(db.ARRAY(db.String(2)), nullable=False)
    mode = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
