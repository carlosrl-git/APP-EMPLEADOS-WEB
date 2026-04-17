from sqlalchemy import text
from app.core.database import engine

def create_hours(trabajador_id, fecha, horas, horas_extra, tipo):
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO horas_trabajadas (trabajador_id, fecha, horas, horas_extra, tipo)
                VALUES (:trabajador_id, :fecha, :horas, :horas_extra, :tipo)
            """), {
                "trabajador_id": int(trabajador_id),
                "fecha": fecha,
                "horas": float(horas),
                "horas_extra": float(horas_extra or 0),
                "tipo": tipo or "normal"
            })
        return True, "Horas creadas correctamente."
    except Exception as e:
        return False, f"Error al crear horas: {e}"
