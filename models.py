from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

DAYS = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(255))
    role = db.Column(db.String(10), default="user")


class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    day = db.Column(db.String(10))
    status = db.Column(db.String(10), default="")


class Config(db.Model):
    day = db.Column(db.String(10), primary_key=True)
    max_off = db.Column(db.Integer)