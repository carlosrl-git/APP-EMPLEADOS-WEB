import os
from sqlalchemy import create_engine, text

with open('.env') as f:
    for line in f:
        if line.startswith('DATABASE_URL='):
            db = line.strip().split('=', 1)[1]
            break

engine = create_engine(db)

with engine.begin() as conn:
    # crear empresa si no existe
    empresa = conn.execute(text("""
        INSERT INTO empresas (nombre, plan, estado)
        VALUES ('Empresa Demo', 'pro', 'activa')
        ON CONFLICT (nombre) DO UPDATE SET nombre=EXCLUDED.nombre
        RETURNING id
    """)).fetchone()

    empresa_id = empresa[0]

    # asignar a usuarios sin empresa
    conn.execute(text("""
        UPDATE usuarios
        SET empresa_id = :eid
        WHERE empresa_id IS NULL
    """), {"eid": empresa_id})

    print(f'OK_ASIGNADO_EMPRESA_{empresa_id}')
