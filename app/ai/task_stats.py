from sqlalchemy import text
from app.core.database import engine

def get_pending_tasks():
    with engine.begin() as conn:
        result = conn.execute(text("""
            SELECT t.id, t.titulo, tr.nombre, tr.apellidos, t.fecha_vencimiento
            FROM tareas t
            LEFT JOIN trabajadores tr ON tr.id = t.trabajador_id
            WHERE t.estado = 'pendiente'
            ORDER BY t.fecha_vencimiento ASC
        """)).mappings().all()

    return result
