from sqlalchemy import text
from app.core.database import engine

def log_ai_action(usuario: str, accion: str, detalle: str):
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO ai_logs (usuario, accion, detalle)
                VALUES (:usuario, :accion, :detalle)
            """), {
                "usuario": usuario or "desconocido",
                "accion": accion,
                "detalle": detalle
            })
    except Exception as e:
        print(f"[AI LOG ERROR] {e}")
