from sqlalchemy import text
from app.core.database import engine

def create_task(trabajador_id, titulo, descripcion, prioridad, estado, fecha_asignacion, fecha_vencimiento):
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO tareas (
                    trabajador_id, titulo, descripcion, prioridad, estado,
                    fecha_asignacion, fecha_vencimiento
                ) VALUES (
                    :trabajador_id, :titulo, :descripcion, :prioridad, :estado,
                    :fecha_asignacion, :fecha_vencimiento
                )
            """), {
                "trabajador_id": int(trabajador_id),
                "titulo": titulo.strip(),
                "descripcion": descripcion.strip() if descripcion else None,
                "prioridad": prioridad or "media",
                "estado": estado or "pendiente",
                "fecha_asignacion": fecha_asignacion,
                "fecha_vencimiento": fecha_vencimiento or None
            })
        return True, "Tarea creada correctamente."
    except Exception as e:
        return False, f"Error al crear tarea: {e}"
