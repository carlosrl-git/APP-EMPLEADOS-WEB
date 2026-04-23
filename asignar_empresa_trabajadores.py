import os
from sqlalchemy import create_engine, text

with open('.env') as f:
    for line in f:
        if line.startswith('DATABASE_URL='):
            db = line.strip().split('=', 1)[1]
            break

engine = create_engine(db)

with engine.begin() as conn:
    conn.execute(text("""
        UPDATE trabajadores
        SET empresa_id = 1
        WHERE empresa_id IS NULL
    """))
    print("OK_TRABAJADORES_ASIGNADOS")
