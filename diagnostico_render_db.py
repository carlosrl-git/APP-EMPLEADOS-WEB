import os
import re
import sys
from pathlib import Path
from sqlalchemy import create_engine, text

ROOT = Path.cwd()
url = os.environ.get("RENDER_DB_URL", "").strip()

print("\n=== DIAGNOSTICO BASE NUEVA RENDER ===")
print("Proyecto:", ROOT)

if not url.startswith("postgresql://") and not url.startswith("postgres://"):
    print("[ERROR] La URL no parece PostgreSQL.")
    sys.exit(1)

if url.startswith("postgres://"):
    url = "postgresql://" + url[len("postgres://"):]

try:
    engine = create_engine(url, pool_pre_ping=True, future=True)
    with engine.connect() as conn:
        r = conn.execute(text("""
            SELECT current_database() AS db, current_user AS usuario, current_schema() AS schema
        """)).mappings().first()
        print("[OK] Conexion correcta")
        print("Base:", r["db"])
        print("Usuario:", r["usuario"])
        print("Schema:", r["schema"])
except Exception as e:
    print("[ERROR] No conecta con PostgreSQL:")
    print(type(e).__name__, e)
    sys.exit(1)

print("\n[1] Tablas existentes en la BD nueva:")
with engine.connect() as conn:
    tablas = conn.execute(text("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema='public'
        AND table_type='BASE TABLE'
        ORDER BY table_name
    """)).scalars().all()

if not tablas:
    print(" - No hay tablas. La base esta vacia.")
else:
    for t in tablas:
        print(" -", t)

print("\n[2] Buscando CREATE TABLE / tablas usadas en el codigo...")

ignore = {"venv", ".git", "__pycache__", ".pytest_cache", "site-packages"}
py_files = [
    p for p in ROOT.rglob("*.py")
    if not any(part in ignore for part in p.parts)
]

patrones = {
    "FROM": re.compile(r"\bFROM\s+([a-zA-Z_][a-zA-Z0-9_]*)", re.I),
    "JOIN": re.compile(r"\bJOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)", re.I),
    "INSERT": re.compile(r"\bINSERT\s+INTO\s+([a-zA-Z_][a-zA-Z0-9_]*)", re.I),
    "UPDATE": re.compile(r"\bUPDATE\s+([a-zA-Z_][a-zA-Z0-9_]*)", re.I),
    "DELETE": re.compile(r"\bDELETE\s+FROM\s+([a-zA-Z_][a-zA-Z0-9_]*)", re.I),
    "CREATE": re.compile(r"\bCREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([a-zA-Z_][a-zA-Z0-9_]*)", re.I),
}

tablas_codigo = {}
creates = []

for p in py_files:
    try:
        txt = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue

    rel = str(p.relative_to(ROOT))

    for tipo, rgx in patrones.items():
        for m in rgx.finditer(txt):
            tabla = m.group(1)
            if tabla.lower() in {"select", "where", "set", "values", "information_schema"}:
                continue

            tablas_codigo.setdefault(tabla, set()).add(rel)

            if tipo == "CREATE":
                linea = txt[:m.start()].count("\n") + 1
                creates.append((rel, linea, tabla))

print("\nTablas usadas por el codigo:")
if tablas_codigo:
    for tabla in sorted(tablas_codigo):
        archivos = ", ".join(sorted(tablas_codigo[tabla])[:4])
        print(f" - {tabla:25} -> {archivos}")
else:
    print(" - No se detectaron tablas.")

print("\nCREATE TABLE encontrados:")
if creates:
    for rel, linea, tabla in creates:
        print(f" - {rel}:{linea} -> {tabla}")
else:
    print(" - No encontre CREATE TABLE en el codigo.")

faltan = sorted(set(tablas_codigo.keys()) - set(tablas))

print("\n[3] Tablas que el codigo usa pero NO existen en la BD:")
if faltan:
    for t in faltan:
        print(" -", t)
else:
    print(" - Ninguna.")

print("\n[4] Columnas de tablas existentes:")
with engine.connect() as conn:
    for tabla in tablas:
        print(f"\n--- {tabla} ---")
        cols = conn.execute(text("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema='public'
            AND table_name=:tabla
            ORDER BY ordinal_position
        """), {"tabla": tabla}).mappings().all()

        for c in cols:
            print(f"{c['column_name']:25} {c['data_type']:25} nullable={c['is_nullable']}")

print("\n=== FIN ===")
print("Pegame desde [1] hasta [4]. No pegues la URL.")
