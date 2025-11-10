from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()
engine = create_engine("sqlite:///database/sim.db", echo=False)
Session = sessionmaker(bind=engine)
session = Session()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    password_hash = Column(String)
    sim_id = Column(String, unique=True)
    role = Column(String, default="user")
    balance = Column(Float, default=100.0)

class App(Base):
    __tablename__ = 'apps'
    id = Column(Integer, primary_key=True)
    owner_sim = Column(String)
    name = Column(String)
    html_code = Column(String)
    js_code = Column(String)
    css_code = Column(String)
    status = Column(String, default="pending")
