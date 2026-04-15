from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

departamentos = [
    "Administración",
    "Limpieza",
    "Mantenimiento",
    "Recepción",
    "Recursos Humanos"
]

with engine.begin() as conn:
    for nombre in departamentos:
        conn.execute(
            text("""
                INSERT INTO departamentos (nombre, activo)
                SELECT :nombre, true
                WHERE NOT EXISTS (
                    SELECT 1 FROM departamentos WHERE nombre = :nombre
                )
            """),
            {"nombre": nombre}
        )

print("DEPARTAMENTOS CREADOS")