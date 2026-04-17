from sqlalchemy import text
from app.core.database import engine

def create_zone(nombre, tipo, activo):
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO zonas (nombre, tipo, activo)
                VALUES (:nombre, :tipo, :activo)
            """), {
                "nombre": nombre.strip(),
                "tipo": tipo.strip() if tipo else None,
                "activo": activo.lower() == "true"
            })
        return True, "Zona creada correctamente."
    except Exception as e:
        return False, f"Error al crear zona: {e}"
