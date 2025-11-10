# app.py
import os
import random
from flask import Flask, render_template, request, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_socketio import SocketIO, send
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import sessionmaker, declarative_base

# ---------------------
# Configuració
# ---------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_DIR = os.path.join(BASE_DIR, 'database')
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, 'sim.db')
SECRET_KEY = "canvia_a_alguna_clau_llarga_i_secreta"

# ---------------------
# Flask + SocketIO
# ---------------------
app = Flask(__name__)
app.secret_key = SECRET_KEY

# ⚡ Async mode threading per evitar errors a Python 3.13
socketio = SocketIO(app, async_mode='threading')  

login_manager = LoginManager()
login_manager.init_app(app)

# ---------------------
# Base de dades
# ---------------------
Base = declarative_base()
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
Session = sessionmaker(bind=engine)
db_session = Session()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    password_hash = Column(String)
    sim_id = Column(String, unique=True)
    role = Column(String, default="user")
    balance = Column(Float, default=100.0)

class AppModel(Base):
    __tablename__ = 'apps'
    id = Column(Integer, primary_key=True)
    owner_sim = Column(String)
    name = Column(String)
    html_code = Column(String)
    js_code = Column(String)
    css_code = Column(String)
    status = Column(String, default="pending")

# Inicialitza la BD si no existeix
Base.metadata.create_all(engine)

# ---------------------
# Flask-Login
# ---------------------
class UserLogin(UserMixin):
    def __init__(self, user):
        self.id = user.id
        self.sim_id = user.sim_id
        self.username = user.username
        self.role = user.role

@login_manager.user_loader
def load_user(user_id):
    user = db_session.query(User).filter_by(id=int(user_id)).first()
    if user:
        return UserLogin(user)
    return None

# ---------------------
# Rutes principals
# ---------------------
@app.route('/')
@login_required
def index():
    return render_template('index.html', sim_id=current_user.sim_id, username=current_user.username)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = db_session.query(User).filter_by(username=username, password_hash=password).first()
        if user:
            login_user(UserLogin(user))
            return redirect(url_for('index'))
        return "Usuari o contrasenya incorrecta"
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        existing = db_session.query(User).filter_by(username=username).first()
        if existing:
            return "Usuari ja existeix"
        sim_id = f"SIM-CA-{random.randint(100,999)}-{random.randint(1000,9999)}"
        new_user = User(username=username, password_hash=password, sim_id=sim_id)
        db_session.add(new_user)
        db_session.commit()
        return redirect(url_for('login'))
    return render_template('login.html')

# ---------------------
# Xat bàsic WebSocket
# ---------------------
@socketio.on('message')
def handle_message(msg):
    send(msg, broadcast=True)

# ---------------------
# Apps estàtiques
# ---------------------
@app.route('/bank')
@login_required
def bank():
    return render_template('bank.html', sim_id=current_user.sim_id, balance=current_user.balance)

@app.route('/creator')
@login_required
def creator():
    return render_template('creator.html', sim_id=current_user.sim_id)

# ---------------------
# Arrencada Render
# ---------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, debug=True)
