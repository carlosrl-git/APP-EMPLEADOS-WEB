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
        UPDATE incidencias i
        SET empresa_id = t.empresa_id
        FROM trabajadores t
        WHERE i.trabajador_id = t.id
    """))

print("OK_FILL_EMPRESA_INCIDENCIAS")
