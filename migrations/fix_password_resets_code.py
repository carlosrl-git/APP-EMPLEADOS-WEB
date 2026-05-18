from sqlalchemy import create_engine, text
import os

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise Exception("Falta DATABASE_URL")

engine = create_engine(DATABASE_URL)

with engine.begin() as conn:
    conn.execute(text("""
        ALTER TABLE password_resets
        ALTER COLUMN code TYPE VARCHAR(255)
    """))

print("OK: password_resets.code cambiado a VARCHAR(255)")
