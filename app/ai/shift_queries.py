from sqlalchemy import text
from app.core.database import engine

def create_shift(trabajador_id, fecha, inicio_jornada, fin_jornada, total_horas, observaciones):
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO turnos (trabajador_id, fecha, inicio_jornada, fin_jornada, total_horas, observaciones)
                VALUES (:t, :f, :i, :fi, :h, :o)
            """), {
                "t": int(trabajador_id),
                "f": fecha,
                "i": inicio_jornada or None,
                "fi": fin_jornada or None,
                "h": total_horas or None,
                "o": observaciones.strip() if observaciones else None
            })
        return True, "Turno creado correctamente."
    except Exception as e:
        return False, f"Error al crear turno: {e}"
