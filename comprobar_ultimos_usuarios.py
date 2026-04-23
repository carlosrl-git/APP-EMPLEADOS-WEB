import os
from sqlalchemy import create_engine, text

with open('.env') as f:
    for line in f:
        if line.startswith('DATABASE_URL='):
            db = line.strip().split('=', 1)[1]
            break

engine = create_engine(db)

with engine.connect() as conn:
    rows = conn.execute(text("SELECT id, username, rol, empresa_id FROM usuarios ORDER BY id DESC LIMIT 5"))
    for r in rows:
        print(f"{r[0]} | {r[1]} | {r[2]} | empresa_id={r[3]}")
