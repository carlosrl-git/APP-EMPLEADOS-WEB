from sqlalchemy import text
from app.core.database import engine

def create_absence(trabajador_id, tipo, fecha_inicio, fecha_fin, motivo, estado):
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO ausencias (
                    trabajador_id, tipo, fecha_inicio, fecha_fin, motivo, estado
                ) VALUES (
                    :trabajador_id, :tipo, :fecha_inicio, :fecha_fin, :motivo, :estado
                )
            """), {
                "trabajador_id": trabajador_id,
                "tipo": tipo,
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
                "motivo": motivo,
                "estado": estado
            })
        return True, "Ausencia creada correctamente."
    except Exception as e:
        return False, f"Error al crear ausencia: {e}"
