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
CREATE TABLE IF NOT EXISTS roles (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) UNIQUE NOT NULL,
    descripcion TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO roles (id, nombre, descripcion)
VALUES
(1, 'admin', 'Administrador del sistema'),
(2, 'user', 'Usuario estándar')
ON CONFLICT (id) DO NOTHING;

INSERT INTO roles (nombre, descripcion)
VALUES
('admin', 'Administrador del sistema'),
('user', 'Usuario estándar')
ON CONFLICT (nombre) DO NOTHING;

ALTER TABLE usuarios
ADD COLUMN IF NOT EXISTS rol_id INTEGER DEFAULT 1;

ALTER TABLE users
ADD COLUMN IF NOT EXISTS rol_id INTEGER DEFAULT 1;

UPDATE usuarios
SET rol_id = CASE
    WHEN rol = 'admin' THEN 1
    ELSE 2
END
WHERE rol_id IS NULL;

UPDATE users
SET rol_id = CASE
    WHEN rol = 'admin' THEN 1
    ELSE 2
END
WHERE rol_id IS NULL;

SELECT setval(
    pg_get_serial_sequence('roles', 'id'),
    COALESCE((SELECT MAX(id) FROM roles), 1)
);
"""

print("Aplicando parche rol_id en usuarios...")

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
print("Columnas actuales en usuarios:")
for c in cols:
    print(" -", c)

print("")
print("[OK] Ahora prueba otra vez crear usuario.")
