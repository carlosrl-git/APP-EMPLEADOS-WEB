from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, future=True)

def existe(conn, tabla):
    r = conn.execute(text("""
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = :t
        )
    """), {"t": tabla}).scalar()
    return bool(r)

with engine.begin() as conn:
    tablas = ["users", "usuarios", "roles", "login_attempts", "password_resets"]
    for t in tablas:
        print(f"{t}: {'SI' if existe(conn, t) else 'NO'}")

    if existe(conn, "users"):
        print("\nUSERS:")
        rows = conn.execute(text("SELECT id, username, email FROM users ORDER BY id")).mappings().all()
        for r in rows:
            print(dict(r))

    if existe(conn, "usuarios"):
        print("\nUSUARIOS:")
        rows = conn.execute(text("SELECT * FROM usuarios ORDER BY id")).mappings().all()
        for r in rows:
            print(dict(r))

    if existe(conn, "roles"):
        print("\nROLES:")
        rows = conn.execute(text("SELECT * FROM roles ORDER BY id")).mappings().all()
        for r in rows:
            print(dict(r))
