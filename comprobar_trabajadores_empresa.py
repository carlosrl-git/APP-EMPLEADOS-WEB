import os
from sqlalchemy import create_engine, text

with open('.env') as f:
    for line in f:
        if line.startswith('DATABASE_URL='):
            db = line.strip().split('=', 1)[1]
            break

engine = create_engine(db)

with engine.connect() as conn:
    rows = conn.execute(text("SELECT id, nombre, apellidos, empresa_id FROM trabajadores ORDER BY id DESC LIMIT 10"))
    for r in rows:
        print(f"{r[0]} | {r[1]} | {r[2]} | empresa_id={r[3]}")
