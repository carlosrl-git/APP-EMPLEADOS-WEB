from sqlalchemy import text

def db_crear_ticket(nombre_usuario, email_usuario, titulo, descripcion, tipo="peticion", prioridad="media"):
    with engine.begin() as conn:
        result = conn.execute(
            text("""
                INSERT INTO tickets (
                    nombre_usuario,
                    email_usuario,
                    titulo,
                    descripcion,
                    tipo,
                    prioridad
                )
                VALUES (
                    :nombre_usuario,
                    :email_usuario,
                    :titulo,
                    :descripcion,
                    :tipo,
                    :prioridad
                )
                RETURNING id, nombre_usuario, email_usuario, titulo, descripcion, tipo, prioridad, estado, fecha_creacion
            """),
            {
                "nombre_usuario": nombre_usuario,
                "email_usuario": email_usuario,
                "titulo": titulo,
                "descripcion": descripcion,
                "tipo": tipo,
                "prioridad": prioridad,
            }
        )
        row = result.mappings().first()
        return dict(row) if row else None