import os
import sys
from sqlalchemy import create_engine, text

url = os.environ.get("DATABASE_URL", "").strip()

if not url.startswith("postgres"):
    print("[ERROR] No hay URL PostgreSQL valida.")
    sys.exit(1)

if url.startswith("postgres://"):
    url = "postgresql://" + url[len("postgres://"):]

engine = create_engine(url, pool_pre_ping=True, future=True)

sql = """
ALTER TABLE usuarios
ADD COLUMN IF NOT EXISTS creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE usuarios
ADD COLUMN IF NOT EXISTS actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

UPDATE usuarios
SET creado_en = COALESCE(creado_en, created_at, CURRENT_TIMESTAMP);

UPDATE usuarios
SET actualizado_en = COALESCE(actualizado_en, updated_at, CURRENT_TIMESTAMP);

ALTER TABLE users
ADD COLUMN IF NOT EXISTS creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE users
ADD COLUMN IF NOT EXISTS actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

UPDATE users
SET creado_en = COALESCE(creado_en, created_at, CURRENT_TIMESTAMP);

UPDATE users
SET actualizado_en = COALESCE(actualizado_en, created_at, CURRENT_TIMESTAMP);
"""

print("Aplicando parche tabla usuarios...")

try:
    with engine.begin() as conn:
        conn.execute(text(sql))

    print("[OK] Parche aplicado correctamente.")
except Exception as e:
    print("[ERROR] Fallo aplicando parche:")
    print(type(e).__name__, e)
    sys.exit(1)

with engine.connect() as conn:
    cols = conn.execute(text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'usuarios'
        ORDER BY ordinal_position
    """)).scalars().all()

print("")
print("COLUMNAS ACTUALES EN usuarios:")
for c in cols:
    print(" -", c)

print("")
print("[OK] Ya puedes probar /usuarios otra vez.")
