from flask import Flask, render_template, request, jsonify
from models import db, User, Schedule, Config, DAYS
from flask_jwt_extended import (
    JWTManager, create_access_token,
    jwt_required, get_jwt_identity
)
from sqlalchemy import func
import datetime
import traceback
import os

app = Flask(__name__)
app.config.from_pyfile("config.py")

db.init_app(app)
jwt = JWTManager(app)

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "connect_args": {"sslmode": "require"}
}

# ================= INIT =================
def init_db():
    with app.app_context():
        db.create_all()

        # tạo admin
        if not User.query.filter_by(username="admin").first():
            admin = User(username="admin", password="admin", role="admin")
            db.session.add(admin)
            db.session.commit()

        # init config
        for d in DAYS:
            if not Config.query.filter_by(day=d).first():
                db.session.add(Config(day=d, max_off=2))
        db.session.commit()

# ================= PAGE =================
@app.route("/")
def login_page():
    return render_template("login.html")

@app.route("/register_page")
def register_page():
    return render_template("register.html")

@app.route("/admin_page")
def admin_page():
    return render_template("admin.html")

@app.route("/user_page")
def user_page():
    return render_template("user.html")


# @app.route("/init_db")
# def init_db():
#     db.create_all()
#     return "DB created!"

# ================= AUTH API =================
@app.route("/api/register", methods=["POST"])
def register():
    data = request.json

    if User.query.filter_by(username=data["username"]).first():
        return jsonify({"msg": "User exists"}), 400

    user = User(username=data["username"], password=data["password"])
    db.session.add(user)
    db.session.commit()

    for d in DAYS:
        db.session.add(Schedule(user_id=user.id, day=d))
    db.session.commit()

    return jsonify({"msg": "Created"})


@app.route("/api/login", methods=["POST"])
def login():
    data = request.json

    user = User.query.filter_by(
        username=data["username"],
        password=data["password"]
    ).first()

    if not user:
        return jsonify({"msg": "Invalid"}), 401

    token = create_access_token(identity=str(user.id))

    return jsonify(token=token, role=user.role)


# ================= GET SCHEDULE =================
@app.route("/api/schedule", methods=["GET"])
@jwt_required()
def get_schedule():
    rows = db.session.query(
        User.id,
        User.username,
        Schedule.day,
        Schedule.status
    ).join(Schedule)\
    .order_by(User.username.asc())\
    .all()

    result = {}
    for uid, uname, d, s in rows:
        if uname not in result:
            result[uname] = {
                "id": uid,
                "days": [""] * 7
            }
        result[uname]["days"][DAYS.index(d)] = s

    print(result)
    return jsonify(result)


# ================= TIME RULE =================
def is_time_allowed():
    now = datetime.datetime.now()
    return now.weekday() == 4 and 9 <= now.hour < 20


# ================= REGISTER OFF =================
@app.route("/api/register_off", methods=["POST"])
@jwt_required()
def register_off():

    if not is_time_allowed():
        return jsonify({"msg": "Not allowed time"}), 400

    user_id = int(get_jwt_identity())
    day = request.json["day"]

    try:
        with db.session.begin():

            config = Config.query\
                .filter_by(day=day)\
                .with_for_update().first()

            count = db.session.query(func.count(Schedule.id))\
                .filter(Schedule.day == day, Schedule.status == "OFF")\
                .scalar()

            if count >= config.max_off:
                return jsonify({"msg": "Full slot"}), 400

            sched = Schedule.query.filter_by(
                user_id=user_id, day=day
            ).with_for_update().first()

            if sched.status == "OFF":
                return jsonify({"msg": "Already"}), 400

            sched.status = "OFF"

        return jsonify({"msg": f"Success {day}"})

    except Exception as e:
        print("❌ ERROR:", e)
        traceback.print_exc()
        return jsonify({"msg": str(e)}), 500


# ================= ADMIN =================
@app.route("/api/admin/set_limit", methods=["POST"])
@jwt_required()
def set_limit():
    user = db.session.get(User, int(get_jwt_identity()))

    if user.role != "admin":
        return jsonify({"msg": "Forbidden"}), 403

    data = request.json

    for d, val in data.items():
        cfg = Config.query.filter_by(day=d).first()
        cfg.max_off = val

    db.session.commit()
    return jsonify({"msg": "Updated"})

@app.route("/api/admin/config", methods=["GET"])
@jwt_required()
def get_config():
    user = db.session.get(User, int(get_jwt_identity()))

    if user.role != "admin":
        return jsonify({"msg": "Forbidden"}), 403

    data = {c.day: c.max_off for c in Config.query.all()}
    return jsonify(data)

@app.route("/api/admin/set_off", methods=["POST"])
@jwt_required()
def admin_set_off():
    user = db.session.get(User, int(get_jwt_identity()))

    if user.role != "admin":
        return jsonify({"msg": "Forbidden"}), 403

    data = request.json
    user_id = data.get("user_id")
    day = data.get("day")
    status = data.get("status")  # "OFF" hoặc ""

    # validate
    if not user_id or day not in DAYS:
        return jsonify({"msg": "Invalid data"}), 400

    try:
        # KHÔNG dùng begin()

        config = Config.query.filter_by(day=day)\
            .with_for_update().first()

        count = db.session.query(func.count(Schedule.id))\
            .filter(Schedule.day == day, Schedule.status == "OFF")\
            .scalar()

        sched = Schedule.query.filter_by(
            user_id=user_id, day=day
        ).with_for_update().first()

        if not sched:
            return jsonify({"msg": "Not found"}), 404

        if status == "OFF":
            if count >= config.max_off:
                return jsonify({"msg": "Full slot"}), 400
            sched.status = "OFF"
        else:
            sched.status = ""

        db.session.commit()

        return jsonify({"msg": "Updated"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": str(e)}), 500

# ================= RUN =================
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))