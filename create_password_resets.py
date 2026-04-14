from sqlalchemy import create_engine, text
from app.core.config import settings
engine=create_engine(settings.DATABASE_URL, pool_pre_ping=True)
sql='CREATE TABLE IF NOT EXISTS password_resets (id SERIAL PRIMARY KEY, email VARCHAR(255) NOT NULL, code VARCHAR(20) NOT NULL, expires_at TIMESTAMP NOT NULL, used BOOLEAN DEFAULT FALSE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)'
with engine.begin() as conn:
    conn.execute(text(sql))
print('tabla password_resets creada')
