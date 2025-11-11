# app.py — servidor Flask + SocketIO lleuger per Render

from flask import Flask, render_template, request, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO, send, emit, join_room, leave_room
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base
import os
import secrets

# --- Configuració bàsica ---
app = Flask(__name__)

# Clau secreta segura (carregada de variable d'entorn o generada automàticament)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

# Base de dades SQLite local
engine = create_engine("sqlite:///database.db", echo=False)
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine)
db_session = SessionLocal()

# --- Sistema de login ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

class User(Base, UserMixin):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    password = Column(String)
    sim_id = Column(String, default="0000")

Base.metadata.create_all(engine)

@login_manager.user_loader
def load_user(user_id):
    return db_session.query(User).get(int(user_id))

# --- Rutes web ---
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

@app.route("/bank")
@login_required
def bank():
    return render_template("bank.html")

@app.route("/hotel")
@login_required
def hotel():
    return render_template("hotel.html")

@app.route("/globo")
@login_required
def globo():
    return render_template("globo.html")

@app.route("/creator")
@login_required
def creator():
    return render_template("creator.html")

@app.route("/admin")
@login_required
def admin_panel():
    if current_user.username != "joan":
        return "Accés denegat"
    return render_template("admin.html")

# --- SocketIO / xat ---
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

# --- Esdeveniments SIM (trucades) ---
@socketio.on("call")
def handle_call(data):
    emit("incoming_call", data, broadcast=True)

# --- Execució ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, debug=False, allow_unsafe_werkzeug=True)
