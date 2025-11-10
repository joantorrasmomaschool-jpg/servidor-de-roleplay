from models import Base, engine

Base.metadata.create_all(engine)
print("Base de dades inicialitzada.")
