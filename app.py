import os
import secrets
import io
from flask import Flask, render_template, request, redirect, url_for, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO, send, emit, join_room, leave_room
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import sessionmaker, declarative_base
import qrcode

# Configuració bàsica
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
port = int(os.environ.get("PORT", 5000))

# Base de dades SQLite
engine = create_engine("sqlite:///database.db", echo=False)
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine)
db_session = SessionLocal()

# ----------------------------------------------------
# Models
# ----------------------------------------------------

class User(Base, UserMixin):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    password = Column(String)
    sim_id = Column(String, default="0000")

class RPApp(Base):
    __tablename__ = "rp_apps"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    description = Column(Text)
    icon = Column(String, default="default.png")
    html_code = Column(Text)
    creator_id = Column(Integer)

class BankAccount(Base):
    __tablename__ = "bank_accounts"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True)
    balance = Column(Integer, default=1000)
    qr_code = Column(String, unique=True, default=lambda: "BANK-" + secrets.token_hex(4))

Base.metadata.create_all(engine)

# ----------------------------------------------------
# Login manager
# ----------------------------------------------------

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return db_session.query(User).get(int(user_id))

# ----------------------------------------------------
# Rutes web principals
# ----------------------------------------------------

@app.route("/")
@login_required
def home():
    return render_template("mobile_home.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = db_session.query(User).filter_by(username=username, password=password).first()
        if user:
            login_user(user)
            return redirect(url_for("home"))
        return "Credencials incorrectes"
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# ----------------------------------------------------
# Bank App
# ----------------------------------------------------

@app.route("/bank")
@login_required
def bank():
    account = db_session.query(BankAccount).filter_by(user_id=current_user.id).first()
    if not account:
        account = BankAccount(user_id=current_user.id)
        db_session.add(account)
        db_session.commit()
    return render_template("bank.html", account=account)

@app.route("/bank/qr/<int:user_id>")
@login_required
def bank_qr(user_id):
    account = db_session.query(BankAccount).filter_by(user_id=user_id).first()
    if not account:
        return "Compte no trobat", 404
    img = qrcode.make(account.qr_code)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")

@app.route("/bank/transfer", methods=["POST"])
@login_required
def bank_transfer():
    target_qr = request.form.get("target_qr")
    try:
        amount = int(request.form.get("amount", 0))
    except:
        return "Quantitat no vàlida", 400

    sender = db_session.query(BankAccount).filter_by(user_id=current_user.id).first()
    receiver = db_session.query(BankAccount).filter_by(qr_code=target_qr).first()
    if not receiver:
        return "Destinatari no trobat", 404
    if sender.balance < amount or amount <= 0:
        return "Fons insuficients o quantitat no vàlida", 400
    sender.balance -= amount
    receiver.balance += amount
    db_session.commit()
    return redirect(url_for("bank"))

# ----------------------------------------------------
# Hotel App
# ----------------------------------------------------

@app.route("/hotel")
@login_required
def hotel():
    return render_template("hotel.html")

# ----------------------------------------------------
# Globo App
# ----------------------------------------------------

@app.route("/globo")
@login_required
def globo():
    return render_template("globo.html")

# ----------------------------------------------------
# Creator App
# ----------------------------------------------------

@app.route("/creator")
@login_required
def creator():
    apps = db_session.query(RPApp).filter_by(creator_id=current_user.id).all()
    return render_template("creator.html", apps=apps)

@app.route("/creator/new", methods=["POST"])
@login_required
def create_app():
    name = request.form.get("name")
    desc = request.form.get("description")
    icon = request.form.get("icon", "default.png")
    html_code = request.form.get("html_code")
    new_app = RPApp(
        name=name,
        description=desc,
        icon=icon,
        html_code=html_code,
        creator_id=current_user.id
    )
    db_session.add(new_app)
    db_session.commit()
    return redirect(url_for("creator"))

@app.route("/creator/delete/<int:app_id>", methods=["POST"])
@login_required
def delete_app(app_id):
    app_to_delete = db_session.query(RPApp).get(app_id)
    if app_to_delete and app_to_delete.creator_id == current_user.id:
        db_session.delete(app_to_delete)
        db_session.commit()
    return redirect(url_for("creator"))

@app.route("/creator/view/<int:app_id>")
@login_required
def view_app(app_id):
    app_entry = db_session.query(RPApp).get(app_id)
    if not app_entry:
        return "App no trobada"
    return render_template("view_app.html", app=app_entry)

# ----------------------------------------------------
# Admin Panel
# ----------------------------------------------------

@app.route("/admin")
@login_required
def admin_panel():
    if current_user.username != "joan":
        return "Accés denegat"
    return render_template("admin.html")

# ----------------------------------------------------
# SocketIO / xat i trucades
# ----------------------------------------------------

socketio = SocketIO(app, async_mode="threading", cors_allowed_origins="*")

@socketio.on("join")
def handle_join(data):
    room = data.get("room")
    username = data.get("username")
    join_room(room)
    send(f"{username} s'ha unit a {room}", to=room)

@socketio.on("message")
def handle_message(data):
    room = data.get("room")
    username = data.get("username")
    msg = data.get("msg")
    send(f"{username}: {msg}", to=room)

@socketio.on("leave")
def handle_leave(data):
    room = data.get("room")
    username = data.get("username")
    leave_room(room)
    send(f"{username} ha sortit de {room}", to=room)

@socketio.on("call")
def handle_call(data):
    emit("incoming_call", data, broadcast=True)

# ----------------------------------------------------
# Execució
# ----------------------------------------------------

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=port, debug=False, allow_unsafe_werkzeug=True)
