from sqlalchemy import text
from passlib.hash import pbkdf2_sha256
from app.core.database import engine

def get_total_employees() -> int:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) AS total FROM trabajadores"))
        row = result.mappings().first()
        return int(row["total"]) if row and row["total"] is not None else 0

def get_employees_with_most_incidents(limit: int = 5):
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT t.nombre, COUNT(i.id) AS total_incidencias FROM trabajadores t LEFT JOIN incidencias i ON t.id = i.trabajador_id GROUP BY t.nombre ORDER BY total_incidencias DESC LIMIT :limit"),
            {"limit": limit}
        )
        return [dict(row) for row in result.mappings().all()]

def get_open_incidents_count() -> int:
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT COUNT(*) AS total FROM incidencias WHERE LOWER(estado) = :estado"),
            {"estado": "abierta"}
        )
        row = result.mappings().first()
        return int(row["total"]) if row and row["total"] is not None else 0

def create_user(username: str, email: str, password: str, rol: str) -> tuple[bool, str]:
    try:
        password_hash = pbkdf2_sha256.hash(password)
        with engine.begin() as conn:
            exists = conn.execute(
                text("SELECT id FROM usuarios WHERE username = :username OR email = :email"),
                {"username": username, "email": email}
            ).mappings().first()

            if exists:
                return False, "Ya existe un usuario con ese username o email."

            conn.execute(
                text("""
                    INSERT INTO usuarios (username, email, password_hash, rol, activo)
                    VALUES (:username, :email, :password_hash, :rol, true)
                """),
                {
                    "username": username,
                    "email": email,
                    "password_hash": password_hash,
                    "rol": rol
                }
            )
        return True, "Usuario creado correctamente."
    except Exception as e:
        return False, f"Error al crear usuario: {e}"
from sqlalchemy import text
from passlib.hash import pbkdf2_sha256
from app.core.database import engine

def create_worker(nombre, apellidos, email, telefono, puesto, departamento_id):
    try:
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO trabajadores
                    (nombre, apellidos, email, telefono, puesto, departamento_id, activo)
                    VALUES (:nombre, :apellidos, :email, :telefono, :puesto, :departamento_id, true)
                """),
                {
                    "nombre": nombre,
                    "apellidos": apellidos or None,
                    "email": email or None,
                    "telefono": telefono or None,
                    "puesto": puesto or None,
                    "departamento_id": departamento_id
                }
            )
        return True, "Trabajador creado correctamente."
    except Exception as e:
        return False, f"Error al crear trabajador: {e}"
def create_incident(descripcion, trabajador_id, estado="abierta"):
    try:
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO incidencias (descripcion, trabajador_id, estado)
                    VALUES (:descripcion, :trabajador_id, :estado)
                """),
                {
                    "descripcion": descripcion,
                    "trabajador_id": int(trabajador_id),
                    "estado": estado or "abierta"
                }
            )
        return True, "Incidencia creada correctamente."
    except Exception as e:
        return False, f"Error al crear incidencia: {e}"
