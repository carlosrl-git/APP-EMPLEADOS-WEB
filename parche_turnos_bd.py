import os
import sys
from sqlalchemy import create_engine, text

url = os.environ.get("DATABASE_URL", "").strip()

if not url.startswith("postgres"):
    print("[ERROR] URL PostgreSQL no valida.")
    sys.exit(1)

if url.startswith("postgres://"):
    url = "postgresql://" + url[len("postgres://"):]

engine = create_engine(url, pool_pre_ping=True, future=True)

sql = """
ALTER TABLE turnos ADD COLUMN IF NOT EXISTS total_horas NUMERIC(6,2) DEFAULT 0;
ALTER TABLE turnos ADD COLUMN IF NOT EXISTS observaciones_generales TEXT;
ALTER TABLE turnos ADD COLUMN IF NOT EXISTS creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE turnos ADD COLUMN IF NOT EXISTS actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE turnos ADD COLUMN IF NOT EXISTS hora_entrada TIME;
ALTER TABLE turnos ADD COLUMN IF NOT EXISTS hora_salida TIME;
ALTER TABLE turnos ADD COLUMN IF NOT EXISTS tipo VARCHAR(100) DEFAULT 'jornada';
ALTER TABLE turnos ADD COLUMN IF NOT EXISTS estado VARCHAR(50) DEFAULT 'pendiente';

UPDATE turnos SET total_horas = COALESCE(total_horas, 0);
UPDATE turnos SET observaciones_generales = COALESCE(observaciones_generales, observaciones);
UPDATE turnos SET creado_en = COALESCE(creado_en, created_at, CURRENT_TIMESTAMP);
UPDATE turnos SET actualizado_en = COALESCE(actualizado_en, updated_at, CURRENT_TIMESTAMP);
UPDATE turnos SET hora_entrada = COALESCE(hora_entrada, hora_inicio, inicio_jornada, hora_inicio_jornada);
UPDATE turnos SET hora_salida = COALESCE(hora_salida, hora_fin, fin_jornada, hora_fin_jornada);
UPDATE turnos SET tipo = COALESCE(tipo, 'jornada');
UPDATE turnos SET estado = COALESCE(estado, 'pendiente');

CREATE INDEX IF NOT EXISTS idx_turnos_empresa ON turnos(empresa_id);
CREATE INDEX IF NOT EXISTS idx_turnos_trabajador ON turnos(trabajador_id);
CREATE INDEX IF NOT EXISTS idx_turnos_fecha ON turnos(fecha);
"""

with engine.begin() as conn:
    conn.execute(text(sql))

with engine.connect() as conn:
    cols = conn.execute(text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema='public'
        AND table_name='turnos'
        ORDER BY ordinal_position
    """)).scalars().all()

print("[OK] Tabla turnos revisada.")
print("Columnas actuales:")
for c in cols:
    print(" -", c)
