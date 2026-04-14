from sqlalchemy import create_engine, text
from passlib.context import CryptContext
from app.core.config import settings

pwd = CryptContext(schemes=['bcrypt'], deprecated='auto')
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
username='admin'
email='ramoslealcarlosmiguel@gmail.com'
password_hash=pwd.hash('Yeshuamirey1.')
with engine.begin() as conn:
    conn.execute(text('INSERT INTO users (username, email, password) VALUES (:u, :e, :p)'), {'u': username, 'e': email, 'p': password_hash})
print('usuario creado')
