import os
import sys
from sqlalchemy import create_engine, text

url = os.environ.get("DATABASE_URL", "").strip()

if not url.startswith("postgres"):
    print("[ERROR] No has pegado una URL PostgreSQL valida.")
    print("Pega la EXTERNAL DATABASE URL entre @' y '@")
    sys.exit(1)

if url.startswith("postgres://"):
    url = "postgresql://" + url[len("postgres://"):]

engine = create_engine(url, pool_pre_ping=True, future=True)

sql = """

-- ==========================================================
-- PARCHE TABLA TAREAS
-- ==========================================================

ALTER TABLE tareas
ADD COLUMN IF NOT EXISTS fecha_asignacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE tareas
ADD COLUMN IF NOT EXISTS fecha_vencimiento DATE;

UPDATE tareas
SET fecha_asignacion = COALESCE(fecha_asignacion, fecha_creacion, created_at, CURRENT_TIMESTAMP);

UPDATE tareas
SET fecha_vencimiento = COALESCE(fecha_vencimiento, fecha_limite, fecha);


-- ==========================================================
-- PARCHE TABLA TURNOS
-- ==========================================================

ALTER TABLE turnos
ADD COLUMN IF NOT EXISTS total_horas NUMERIC(6,2) DEFAULT 0;

ALTER TABLE turnos
ADD COLUMN IF NOT EXISTS observaciones_generales TEXT;

UPDATE turnos
SET total_horas = COALESCE(total_horas, 0);

UPDATE turnos
SET observaciones_generales = COALESCE(observaciones_generales, observaciones);


-- ==========================================================
-- PARCHE TABLA RUTAS
-- ==========================================================

ALTER TABLE rutas
ADD COLUMN IF NOT EXISTS total_horas NUMERIC(6,2) DEFAULT 0;

ALTER TABLE rutas
ADD COLUMN IF NOT EXISTS observaciones_generales TEXT;

UPDATE rutas
SET total_horas = COALESCE(total_horas, 0);

UPDATE rutas
SET observaciones_generales = COALESCE(observaciones_generales, observaciones);


-- ==========================================================
-- PARCHE TABLA HORAS_TRABAJADAS
-- ==========================================================

ALTER TABLE horas_trabajadas
ADD COLUMN IF NOT EXISTS horas_extra NUMERIC(6,2) DEFAULT 0;

ALTER TABLE horas_trabajadas
ADD COLUMN IF NOT EXISTS tipo VARCHAR(100) DEFAULT 'ordinarias';

UPDATE horas_trabajadas
SET horas_extra = COALESCE(horas_extra, 0);

UPDATE horas_trabajadas
SET tipo = COALESCE(tipo, 'ordinarias');


-- ==========================================================
-- PARCHE TABLA ZONAS
-- ==========================================================

ALTER TABLE zonas
ADD COLUMN IF NOT EXISTS tipo VARCHAR(100) DEFAULT 'general';

UPDATE zonas
SET tipo = COALESCE(tipo, 'general');


-- ==========================================================
-- PARCHE TABLA TICKETS
-- ==========================================================

ALTER TABLE tickets
ADD COLUMN IF NOT EXISTS nombre_usuario VARCHAR(150);

ALTER TABLE tickets
ADD COLUMN IF NOT EXISTS email_usuario VARCHAR(150);

ALTER TABLE tickets
ADD COLUMN IF NOT EXISTS titulo VARCHAR(200);

ALTER TABLE tickets
ADD COLUMN IF NOT EXISTS tipo VARCHAR(100) DEFAULT 'general';

ALTER TABLE tickets
ADD COLUMN IF NOT EXISTS fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

UPDATE tickets
SET nombre_usuario = COALESCE(nombre_usuario, nombre);

UPDATE tickets
SET email_usuario = COALESCE(email_usuario, email);

UPDATE tickets
SET titulo = COALESCE(titulo, asunto);

UPDATE tickets
SET tipo = COALESCE(tipo, 'general');

UPDATE tickets
SET fecha_creacion = COALESCE(fecha_creacion, created_at, CURRENT_TIMESTAMP);

"""

checks = {
    "tareas": ["fecha_asignacion", "fecha_vencimiento"],
    "turnos": ["total_horas", "observaciones_generales"],
    "rutas": ["total_horas", "observaciones_generales"],
    "horas_trabajadas": ["horas_extra", "tipo"],
    "zonas": ["tipo"],
    "tickets": ["nombre_usuario", "email_usuario", "titulo", "tipo", "fecha_creacion"],
}

print("====================================================")
print("APLICANDO PARCHE DE COLUMNAS FALTANTES")
print("====================================================")

try:
    with engine.begin() as conn:
        conn.execute(text(sql))

    print("[OK] Parche aplicado correctamente.")
except Exception as e:
    print("[ERROR] Fallo aplicando el parche:")
    print(type(e).__name__, e)
    sys.exit(1)

print("")
print("VERIFICANDO COLUMNAS:")

with engine.connect() as conn:
    for table, columns in checks.items():
        print("")
        print(f"--- {table} ---")
        existing = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = :table
            ORDER BY ordinal_position
        """), {"table": table}).scalars().all()

        existing_set = set(existing)

        for col in columns:
            if col in existing_set:
                print(f"[OK] {col}")
            else:
                print(f"[FALTA] {col}")

print("")
print("====================================================")
print("[OK] REVISION TERMINADA")
print("Ahora haz Manual Deploy en Render y prueba la web.")
print("====================================================")
