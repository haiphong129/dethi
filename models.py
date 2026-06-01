from datetime import datetime
import random, string

from app import db

def gen_code():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default="user")
    links = db.relationship("Link", backref="user", lazy=True)

class Dethi(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False,unique=True)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    links = db.relationship("Link", backref="dethi_obj", lazy=True)
    oj = db.Column(db.Text)

class Link(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    original_url = db.Column(db.String(500), nullable=False, unique=True)
    short_code = db.Column(db.String(10), unique=True, default=gen_code,index=True)
    clicks = db.Column(db.Integer, default=0)
    title = db.Column(db.String(200)) #Tiêu đề
    created_at = db.Column(db.DateTime, default=datetime.now)
    loai = db.Column(db.String(20), default="Khác") #Loại link: Khác; Đề; Hướng dẫn; Test; all (toàn bộ)
    dethi_id = db.Column(db.Integer, db.ForeignKey("dethi.id"))

class ClickLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    link_id = db.Column(db.Integer)
    user_id = db.Column(db.Integer)
    country = db.Column(db.String(100))
    device = db.Column(db.String(50))
    revenue = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now)