from datetime import datetime, timedelta
from email.mime.text import MIMEText
import os
import random
import smtplib

from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import StreamingResponse
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from passlib.hash import pbkdf2_sha256
from sqlalchemy import create_engine, text

from app.core.config import settings

load_dotenv()

app = FastAPI(title="App Empleados Web")
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, future=True)

def render_template(request: Request, name: str, context: dict, status_code: int = 200):
    context["request"] = request
    return templates.TemplateResponse(request=request, name=name, context=context, status_code=status_code)

def send_reset_email(to_email: str, code: str) -> None:
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = os.getenv("SMTP_PORT")
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("FROM_EMAIL")

    if not all([smtp_host, smtp_port, smtp_user, smtp_password, from_email]):
        print("[MAIL] Variables SMTP incompletas. No se envió el correo.")
        print(f"[MAIL] Código para {to_email}: {code}")
        return

    msg = MIMEText(f"Tu código de recuperación es: {code}")
    msg["Subject"] = "Recuperación de contraseña - AppEmpleados"
    msg["From"] = from_email
    msg["To"] = to_email

    server = smtplib.SMTP(smtp_host, int(smtp_port))
    server.starttls()
    server.login(smtp_user, smtp_password)
    server.sendmail(from_email, [to_email], msg.as_string())
    server.quit()

def get_current_username(request: Request):
    return request.cookies.get("session_user")

def get_current_role(username: str):
    if not username:
        return None
    with engine.begin() as conn:
        user = conn.execute(
            text("SELECT rol FROM usuarios WHERE username = :u AND activo = true"),
            {"u": username}
        ).mappings().first()
    return user["rol"] if user else None

def require_login(request: Request):
    username = get_current_username(request)
    if not username:
        return None, None, RedirectResponse(url="/", status_code=303)
    rol = get_current_role(username)
    if not rol:
        response = RedirectResponse(url="/", status_code=303)
        response.delete_cookie("session_user")
        return None, None, response
    return username, rol, None

def require_admin(request: Request):
    username, rol, response = require_login(request)
    if response:
        return None, None, response
    if rol != "admin":
        return username, rol, RedirectResponse(url="/dashboard", status_code=303)
    return username, rol, None

@app.get("/", response_class=HTMLResponse)
def login_page(request: Request):
    if request.cookies.get("session_user"):
        return RedirectResponse(url="/dashboard", status_code=303)
    return render_template(request, "login.html", {"error": ""})

@app.post("/login", response_class=HTMLResponse)
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    now = datetime.utcnow()

    try:
        with engine.begin() as conn:
            attempt = conn.execute(
                text("SELECT username, attempts, last_attempt FROM login_attempts WHERE username = :u"),
                {"u": username},
            ).mappings().first()

            if (
                attempt
                and attempt["attempts"] >= 5
                and attempt["last_attempt"] is not None
                and (now - attempt["last_attempt"]).total_seconds() < 300
            ):
                return render_template(request, "login.html", {"error": "Usuario bloqueado 5 minutos por demasiados intentos"}, 429)

            user = conn.execute(
                text(""" SELECT id, username, email, password_hash, rol, activo FROM usuarios WHERE username = :u """),
                {"u": username},
            ).mappings().first()

            if user and user["activo"] and pbkdf2_sha256.verify(password, user["password_hash"]):
                conn.execute(text("DELETE FROM login_attempts WHERE username = :u"), {"u": username})
                response = RedirectResponse(url="/dashboard", status_code=303)
                response.set_cookie(key="session_user", value=username, httponly=True, samesite="lax", secure=False, max_age=60 * 60 * 8)
                return response

            if attempt:
                conn.execute(
                    text("UPDATE login_attempts SET attempts = attempts + 1, last_attempt = :t WHERE username = :u"),
                    {"t": now, "u": username},
                )
            else:
                conn.execute(
                    text("INSERT INTO login_attempts (username, attempts, last_attempt) VALUES (:u, 1, :t)"),
                    {"u": username, "t": now},
                )

        return render_template(request, "login.html", {"error": "Usuario o contraseña incorrectos"}, 401)

    except Exception as e:
        print(f"[LOGIN ERROR] {e}")
        return render_template(request, "login.html", {"error": "Error interno al iniciar sesión"}, 500)

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    username, rol, response = require_login(request)
    if response:
        return response

    with engine.begin() as conn:
        total_users = conn.execute(text("SELECT COUNT(*) FROM usuarios")).scalar()
        blocked = conn.execute(text("SELECT COUNT(*) FROM login_attempts WHERE attempts >= 5")).scalar()
        resets = conn.execute(text("SELECT COUNT(*) FROM password_resets WHERE used = false")).scalar()
        total_trabajadores = conn.execute(text("SELECT COUNT(*) FROM trabajadores")).scalar()
        incidencias_abiertas = conn.execute(text("SELECT COUNT(*) FROM incidencias WHERE estado = 'abierta'")).scalar()
        tareas_pendientes = conn.execute(text("SELECT COUNT(*) FROM tareas WHERE estado IN ('pendiente','en_progreso')")).scalar()

    return render_template(request, "dashboard.html", {
        "username": username,
        "rol": rol,
        "total_users": total_users,
        "blocked": blocked,
        "resets": resets,
        "total_trabajadores": total_trabajadores,
        "incidencias_abiertas": incidencias_abiertas,
        "tareas_pendientes": tareas_pendientes,
        "active_page": "inicio"
    })

@app.get("/trabajadores", response_class=HTMLResponse)
def ver_trabajadores(request: Request, q: str = "", departamento_id: str = ""):
    username, rol, response = require_login(request)
    if response:
        return response

    q = (q or "").strip()
    departamento_id = (departamento_id or "").strip()

    sql = """
        SELECT t.id, t.nombre, t.apellidos, t.puesto, t.email, d.nombre AS departamento
        FROM trabajadores t
        LEFT JOIN departamentos d ON d.id = t.departamento_id
        WHERE 1=1
    """
    params = {}

    if q:
        sql += " AND (LOWER(t.nombre) LIKE LOWER(:q) OR LOWER(COALESCE(t.apellidos, '')) LIKE LOWER(:q))"
        params["q"] = f"%{q}%"

    if departamento_id:
        sql += " AND t.departamento_id = :departamento_id"
        params["departamento_id"] = int(departamento_id)

    sql += " ORDER BY t.id"

    with engine.begin() as conn:
        trabajadores = conn.execute(text(sql), params).mappings().all()
        departamentos = conn.execute(text("SELECT id, nombre FROM departamentos WHERE activo = true ORDER BY nombre")).mappings().all()

    return render_template(request, "trabajadores.html", {
        "username": username,
        "rol": rol,
        "trabajadores": trabajadores,
        "departamentos": departamentos,
        "q": q,
        "departamento_id": departamento_id,
        "active_page": "trabajadores"
    })

@app.get("/trabajadores/nuevo", response_class=HTMLResponse)
def nuevo_trabajador_page(request: Request):
    username, rol, response = require_admin(request)
    if response:
        return response

    with engine.begin() as conn:
        departamentos = conn.execute(text("SELECT id, nombre FROM departamentos WHERE activo = true ORDER BY nombre")).mappings().all()

    return render_template(request, "trabajador_nuevo.html", {
        "username": username,
        "rol": rol,
        "departamentos": departamentos,
        "error": "",
        "msg": "",
        "active_page": "trabajadores"
    })

@app.post("/trabajadores/guardar2")
def guardar_trabajador_2(request: Request, nombre: str = Form(...), apellidos: str = Form(""), email: str = Form(""), telefono: str = Form(""), puesto: str = Form(""), departamento_id: str = Form("")):
    username, rol, response = require_admin(request)
    if response:
        return response

    try:
        dep_id = int(departamento_id) if str(departamento_id).strip() else None

        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO trabajadores (nombre, apellidos, email, telefono, puesto, departamento_id, activo) VALUES (:nombre, :apellidos, :email, :telefono, :puesto, :departamento_id, true)"),
                {
                    "nombre": nombre.strip(),
                    "apellidos": apellidos.strip() or None,
                    "email": email.strip() or None,
                    "telefono": telefono.strip() or None,
                    "puesto": puesto.strip() or None,
                    "departamento_id": dep_id
                }
            )

        return RedirectResponse(url="/trabajadores", status_code=303)

    except Exception as e:
        print(f"[GUARDAR TRABAJADOR 2 ERROR] {e}")
        return RedirectResponse(url="/trabajadores/nuevo", status_code=303)

@app.get("/trabajadores/{id}", response_class=HTMLResponse)
def ficha_trabajador(request: Request, id: int):
    username, rol, response = require_login(request)
    if response:
        return response

    with engine.begin() as conn:
        t = conn.execute(text("""
            SELECT t.*, d.nombre AS departamento
            FROM trabajadores t
            LEFT JOIN departamentos d ON d.id = t.departamento_id
            WHERE t.id = :id
        """), {"id": id}).mappings().first()

        if not t:
            return RedirectResponse(url="/trabajadores", status_code=303)

        ausencias = conn.execute(text("""
            SELECT id, tipo, fecha_inicio, fecha_fin, motivo, estado
            FROM ausencias
            WHERE trabajador_id = :id
            ORDER BY fecha_inicio DESC
        """), {"id": id}).mappings().all()

        horas = conn.execute(text("""
            SELECT id, fecha, horas, horas_extra, tipo
            FROM horas_trabajadas
            WHERE trabajador_id = :id
            ORDER BY fecha DESC
        """), {"id": id}).mappings().all()

        incidencias = conn.execute(text("""
            SELECT id, descripcion, estado, fecha
            FROM incidencias
            WHERE trabajador_id = :id
            ORDER BY fecha DESC
        """), {"id": id}).mappings().all()

        tareas = conn.execute(text("""
            SELECT id, descripcion, estado, resultado, evaluacion, fecha_asignacion, fecha_realizacion
            FROM tareas_extra
            WHERE trabajador_id = :id
            ORDER BY fecha_asignacion DESC
        """), {"id": id}).mappings().all()

        turnos = conn.execute(text("""
            SELECT tu.id, tu.fecha, tu.turno, tu.hora_inicio, tu.hora_fin, tu.estado, tu.observaciones, z.nombre AS zona
            FROM turnos tu
            LEFT JOIN zonas z ON tu.zona_id = z.id
            WHERE tu.trabajador_id = :id
            ORDER BY tu.fecha DESC, tu.hora_inicio DESC
        """), {"id": id}).mappings().all()

        rutas = conn.execute(text("""
            SELECT r.id, r.fecha, r.hora_inicio_jornada, r.hora_fin_jornada, r.total_horas, r.observaciones_generales
            FROM rutas r
            WHERE r.trabajador_id = :id
            ORDER BY r.fecha DESC, r.hora_inicio_jornada ASC
        """), {"id": id}).mappings().all()

    return render_template(request, "trabajador_ficha.html", {
        "username": username,
        "rol": rol,
        "t": t,
        "ausencias": ausencias,
        "horas": horas,
        "incidencias": incidencias,
        "tareas": tareas,
        "turnos": turnos,
        "rutas": rutas,
        "active_page": "trabajadores"
    })

@app.get("/trabajadores/editar/{id}", response_class=HTMLResponse)
def editar_trabajador_page(request: Request, id: int):
    username, rol, response = require_admin(request)
    if response:
        return response

    with engine.begin() as conn:
        t = conn.execute(text("SELECT * FROM trabajadores WHERE id = :id"), {"id": id}).mappings().first()
        departamentos = conn.execute(text("SELECT id, nombre FROM departamentos WHERE activo = true")).mappings().all()

    return render_template(request, "trabajador_editar.html", {
        "username": username,
        "rol": rol,
        "t": t,
        "departamentos": departamentos,
        "active_page": "trabajadores"
    })

@app.post("/trabajadores/editar/{id}")
def editar_trabajador(request: Request, id: int, nombre: str = Form(...), apellidos: str = Form(""), email: str = Form(""), telefono: str = Form(""), puesto: str = Form(""), departamento_id: str = Form("")):
    username, rol, response = require_admin(request)
    if response:
        return response

    dep_id = int(departamento_id) if str(departamento_id).strip() else None

    with engine.begin() as conn:
        conn.execute(
            text("UPDATE trabajadores SET nombre=:nombre, apellidos=:apellidos, email=:email, telefono=:telefono, puesto=:puesto, departamento_id=:dep WHERE id=:id"),
            {"id": id, "nombre": nombre, "apellidos": apellidos or None, "email": email or None, "telefono": telefono or None, "puesto": puesto or None, "dep": dep_id}
        )

    return RedirectResponse(url="/trabajadores", status_code=303)

@app.get("/trabajadores/eliminar/{id}")
def eliminar_trabajador(request: Request, id: int):
    username, rol, response = require_admin(request)
    if response:
        return response

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM trabajadores WHERE id = :id"), {"id": id})

    return RedirectResponse(url="/trabajadores", status_code=303)

@app.get("/incidencias", response_class=HTMLResponse)
def ver_incidencias(request: Request, estado: str = ""):
    username, rol, response = require_login(request)
    if response:
        return response

    estado = (estado or "").strip()

    sql = """
        SELECT i.id, i.descripcion, i.estado, i.fecha, t.nombre, t.apellidos
        FROM incidencias i
        LEFT JOIN trabajadores t ON t.id = i.trabajador_id
        WHERE 1=1
    """
    params = {}

    if estado:
        sql += " AND i.estado = :estado"
        params["estado"] = estado

    sql += " ORDER BY i.fecha DESC"

    with engine.begin() as conn:
        incidencias = conn.execute(text(sql), params).mappings().all()

    return render_template(request, "incidencias.html", {
        "username": username,
        "rol": rol,
        "incidencias": incidencias,
        "estado": estado,
        "active_page": "incidencias"
    })

@app.get("/incidencias/nueva", response_class=HTMLResponse)
def nueva_incidencia_page(request: Request):
    username, rol, response = require_admin(request)
    if response:
        return response

    with engine.begin() as conn:
        trabajadores = conn.execute(text("SELECT id, nombre, apellidos FROM trabajadores ORDER BY nombre, apellidos")).mappings().all()

    return render_template(request, "incidencia_nueva.html", {
        "username": username,
        "rol": rol,
        "trabajadores": trabajadores,
        "error": "",
        "msg": "",
        "active_page": "incidencias"
    })

@app.post("/incidencias/nueva")
def guardar_incidencia(request: Request, descripcion: str = Form(...), trabajador_id: str = Form(""), estado: str = Form("abierta")):
    username, rol, response = require_admin(request)
    if response:
        return response

    try:
        trabajador = int(trabajador_id) if str(trabajador_id).strip() else None

        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO incidencias (descripcion, trabajador_id, estado) VALUES (:descripcion, :trabajador_id, :estado)"),
                {
                    "descripcion": descripcion.strip(),
                    "trabajador_id": trabajador,
                    "estado": estado.strip() or "abierta"
                }
            )

        return RedirectResponse(url="/incidencias", status_code=303)

    except Exception as e:
        print(f"[NUEVA INCIDENCIA ERROR] {e}")
        with engine.begin() as conn:
            trabajadores = conn.execute(text("SELECT id, nombre, apellidos FROM trabajadores ORDER BY nombre, apellidos")).mappings().all()
        return render_template(request, "incidencia_nueva.html", {
            "username": username,
            "rol": rol,
            "trabajadores": trabajadores,
            "error": "Error al crear la incidencia",
            "msg": "",
            "active_page": "incidencias"
        })

@app.get("/incidencias/estado/{id}/{nuevo_estado}")
def cambiar_estado_incidencia(request: Request, id: int, nuevo_estado: str):
    username, rol, response = require_admin(request)
    if response:
        return response

    estados_validos = ["abierta", "en_proceso", "completada"]

    if nuevo_estado not in estados_validos:
        return RedirectResponse(url="/incidencias", status_code=303)

    with engine.begin() as conn:
        conn.execute(
            text("UPDATE incidencias SET estado = :estado WHERE id = :id"),
            {"estado": nuevo_estado, "id": id}
        )

    return RedirectResponse(url="/incidencias", status_code=303)

@app.get("/tareas", response_class=HTMLResponse)
def ver_tareas(request: Request, estado: str = "", prioridad: str = ""):
    username, rol, response = require_login(request)
    if response:
        return response

    estado = (estado or "").strip()
    prioridad = (prioridad or "").strip()

    sql = """
        SELECT ta.id, ta.titulo, ta.estado, ta.prioridad, ta.fecha_asignacion, ta.fecha_vencimiento,
               tr.nombre, tr.apellidos
        FROM tareas ta
        LEFT JOIN trabajadores tr ON tr.id = ta.trabajador_id
        WHERE 1=1
    """
    params = {}

    if estado:
        sql += " AND ta.estado = :estado"
        params["estado"] = estado

    if prioridad:
        sql += " AND ta.prioridad = :prioridad"
        params["prioridad"] = prioridad

    sql += " ORDER BY ta.fecha_asignacion DESC, ta.id DESC"

    with engine.begin() as conn:
        tareas = conn.execute(text(sql), params).mappings().all()

    return render_template(request, "tareas.html", {
        "username": username,
        "rol": rol,
        "tareas": tareas,
        "estado": estado,
        "prioridad": prioridad,
        "active_page": "tareas"
    })

@app.get("/tareas/nueva", response_class=HTMLResponse)
def nueva_tarea_page(request: Request):
    username, rol, response = require_admin(request)
    if response:
        return response

    with engine.begin() as conn:
        trabajadores = conn.execute(text("SELECT id, nombre, apellidos FROM trabajadores ORDER BY nombre, apellidos")).mappings().all()

    return render_template(request, "tarea_nueva.html", {
        "username": username,
        "rol": rol,
        "trabajadores": trabajadores,
        "error": "",
        "msg": "",
        "active_page": "tareas"
    })

@app.post("/tareas/nueva")
def guardar_tarea(request: Request, titulo: str = Form(...), descripcion: str = Form(""), trabajador_id: str = Form(...), prioridad: str = Form("media"), estado: str = Form("pendiente"), fecha_asignacion: str = Form(...), fecha_vencimiento: str = Form("")):
    username, rol, response = require_admin(request)
    if response:
        return response

    try:
        with engine.begin() as conn:
            conn.execute(
                text("""
                INSERT INTO tareas (
                    trabajador_id, titulo, descripcion, prioridad, estado,
                    fecha_asignacion, fecha_vencimiento
                ) VALUES (
                    :trabajador_id, :titulo, :descripcion, :prioridad, :estado,
                    :fecha_asignacion, :fecha_vencimiento
                )
                """),
                {
                    "trabajador_id": int(trabajador_id),
                    "titulo": titulo.strip(),
                    "descripcion": descripcion.strip() or None,
                    "prioridad": prioridad.strip() or "media",
                    "estado": estado.strip() or "pendiente",
                    "fecha_asignacion": fecha_asignacion,
                    "fecha_vencimiento": fecha_vencimiento or None
                }
            )

        return RedirectResponse(url="/tareas", status_code=303)

    except Exception as e:
        print(f"[NUEVA TAREA ERROR] {e}")
        with engine.begin() as conn:
            trabajadores = conn.execute(text("SELECT id, nombre, apellidos FROM trabajadores ORDER BY nombre, apellidos")).mappings().all()
        return render_template(request, "tarea_nueva.html", {
            "username": username,
            "rol": rol,
            "trabajadores": trabajadores,
            "error": "Error al crear la tarea",
            "msg": "",
            "active_page": "tareas"
        })

@app.get("/tareas/estado/{id}/{nuevo_estado}")
def cambiar_estado_tarea(request: Request, id: int, nuevo_estado: str):
    username, rol, response = require_admin(request)
    if response:
        return response

    estados_validos = ["pendiente", "en_progreso", "finalizada", "cancelada"]

    if nuevo_estado not in estados_validos:
        return RedirectResponse(url="/tareas", status_code=303)

    with engine.begin() as conn:
        conn.execute(
            text("UPDATE tareas SET estado = :estado WHERE id = :id"),
            {"estado": nuevo_estado, "id": id}
        )

    return RedirectResponse(url="/tareas", status_code=303)

@app.get("/tareas/editar/{id}", response_class=HTMLResponse)
def editar_tarea_page(request: Request, id: int):
    username, rol, response = require_admin(request)
    if response:
        return response

    with engine.begin() as conn:
        tarea = conn.execute(text("SELECT * FROM tareas WHERE id = :id"), {"id": id}).mappings().first()
        trabajadores = conn.execute(text("SELECT id, nombre, apellidos FROM trabajadores ORDER BY nombre")).mappings().all()

    return render_template(request, "tarea_editar.html", {
        "username": username,
        "rol": rol,
        "t": tarea,
        "trabajadores": trabajadores,
        "active_page": "tareas"
    })

@app.post("/tareas/editar/{id}")
def editar_tarea(request: Request, id: int, titulo: str = Form(...), descripcion: str = Form(""), trabajador_id: str = Form(...), prioridad: str = Form(...), estado: str = Form(...), fecha_asignacion: str = Form(...), fecha_vencimiento: str = Form("")):
    username, rol, response = require_admin(request)
    if response:
        return response

    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE tareas SET
                titulo=:titulo,
                descripcion=:descripcion,
                trabajador_id=:trabajador_id,
                prioridad=:prioridad,
                estado=:estado,
                fecha_asignacion=:fecha_asignacion,
                fecha_vencimiento=:fecha_vencimiento
            WHERE id=:id
        """), {
            "id": id,
            "titulo": titulo,
            "descripcion": descripcion or None,
            "trabajador_id": int(trabajador_id),
            "prioridad": prioridad,
            "estado": estado,
            "fecha_asignacion": fecha_asignacion,
            "fecha_vencimiento": fecha_vencimiento or None
        })

    return RedirectResponse(url="/tareas", status_code=303)

@app.get("/tareas/eliminar/{id}")
def eliminar_tarea(request: Request, id: int):
    username, rol, response = require_admin(request)
    if response:
        return response

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM tareas WHERE id = :id"), {"id": id})

    return RedirectResponse(url="/tareas", status_code=303)

@app.get("/usuarios", response_class=HTMLResponse)
def ver_usuarios(request: Request):
    username, rol, response = require_admin(request)
    if response:
        return response

    with engine.begin() as conn:
        usuarios = conn.execute(text("SELECT id, username, email, rol, activo, creado_en FROM usuarios ORDER BY id")).mappings().all()

    return render_template(request, "usuarios.html", {
        "username": username,
        "rol": rol,
        "usuarios": usuarios,
        "active_page": "usuarios"
    })

@app.get("/usuarios/nuevo", response_class=HTMLResponse)
def nuevo_usuario_page(request: Request):
    username, rol, response = require_admin(request)
    if response:
        return response

    return render_template(request, "usuario_nuevo.html", {
        "username": username,
        "rol": rol,
        "error": "",
        "msg": "",
        "active_page": "usuarios"
    })

@app.post("/usuarios/nuevo")
def guardar_usuario(request: Request, username_nuevo: str = Form(...), email: str = Form(...), password: str = Form(...), rol: str = Form("usuario")):
    username, rol_actual, response = require_admin(request)
    if response:
        return response

    try:
        password_hash = pbkdf2_sha256.hash(password)

        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO usuarios (username, email, password_hash, rol, activo, rol_id) VALUES (:username, :email, :password_hash, :rol, true, 1)"),
                {
                    "username": username_nuevo.strip(),
                    "email": email.strip(),
                    "password_hash": password_hash,
                    "rol": rol.strip() or "usuario"
                }
            )

        return RedirectResponse(url="/usuarios", status_code=303)

    except Exception as e:
        print(f"[NUEVO USUARIO ERROR] {e}")
        return render_template(request, "usuario_nuevo.html", {
            "username": username,
            "rol": rol_actual,
            "error": "Error al crear el usuario",
            "msg": "",
            "active_page": "usuarios"
        })

@app.get("/usuarios/editar/{id}", response_class=HTMLResponse)
def editar_usuario_page(request: Request, id: int):
    username, rol, response = require_admin(request)
    if response:
        return response

    with engine.begin() as conn:
        u = conn.execute(text("SELECT * FROM usuarios WHERE id = :id"), {"id": id}).mappings().first()

    return render_template(request, "usuario_editar.html", {
        "username": username,
        "rol": rol,
        "u": u,
        "active_page": "usuarios"
    })

@app.post("/usuarios/editar/{id}")
def editar_usuario(request: Request, id: int, username_nuevo: str = Form(...), email: str = Form(...), rol: str = Form(...)):
    username, rol_actual, response = require_admin(request)
    if response:
        return response

    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE usuarios SET
                username = :username,
                email = :email,
                rol = :rol
            WHERE id = :id
        """), {
            "id": id,
            "username": username_nuevo,
            "email": email,
            "rol": rol
        })

    return RedirectResponse(url="/usuarios", status_code=303)

@app.get("/usuarios/toggle/{id}")
def toggle_usuario(request: Request, id: int):
    username, rol, response = require_admin(request)
    if response:
        return response

    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE usuarios
            SET activo = NOT activo
            WHERE id = :id
        """), {"id": id})

    return RedirectResponse(url="/usuarios", status_code=303)

@app.get("/logout")
def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("session_user")
    return response

@app.get("/forgot-password", response_class=HTMLResponse)
def forgot_password_page(request: Request):
    return render_template(request, "forgot_password.html", {"msg": "", "error": ""})

@app.post("/forgot-password", response_class=HTMLResponse)
def forgot_password(request: Request, email: str = Form(...)):
    code = str(random.randint(100000, 999999))
    expires_at = datetime.utcnow() + timedelta(minutes=10)

    try:
        with engine.begin() as conn:
            user = conn.execute(text("SELECT id FROM usuarios WHERE email = :e AND activo = true"), {"e": email}).mappings().first()
            if user:
                conn.execute(text("DELETE FROM password_resets WHERE email = :e AND used = false"), {"e": email})
                conn.execute(text("INSERT INTO password_resets (email, code, expires_at, used) VALUES (:e, :c, :x, false)"), {"e": email, "c": code, "x": expires_at})
                send_reset_email(email, code)

        return render_template(request, "forgot_password.html", {"msg": "Si el correo existe, se enviará un código.", "error": ""})

    except Exception as e:
        print(f"[FORGOT PASSWORD ERROR] {e}")
        return render_template(request, "forgot_password.html", {"msg": "", "error": "Error al procesar la solicitud"}, 500)

@app.get("/reset-password", response_class=HTMLResponse)
def reset_password_page(request: Request):
    return render_template(request, "reset_password.html", {"msg": "", "error": ""})

@app.post("/reset-password", response_class=HTMLResponse)
def reset_password(request: Request, email: str = Form(...), code: str = Form(...), new_password: str = Form(...)):
    if len(new_password) < 8:
        return render_template(request, "reset_password.html", {"msg": "", "error": "La contraseña debe tener al menos 8 caracteres"}, 400)

    try:
        with engine.begin() as conn:
            row = conn.execute(text("SELECT id, email, code, expires_at, used FROM password_resets WHERE email = :e AND code = :c AND used = false ORDER BY id DESC LIMIT 1"), {"e": email, "c": code}).mappings().first()

            if not row:
                return render_template(request, "reset_password.html", {"msg": "", "error": "Código inválido"}, 400)

            if datetime.utcnow() > row["expires_at"]:
                return render_template(request, "reset_password.html", {"msg": "", "error": "Código caducado"}, 400)

            new_hash = pbkdf2_sha256.hash(new_password)
            conn.execute(text("UPDATE usuarios SET password_hash = :p WHERE email = :e"), {"p": new_hash, "e": email})
            conn.execute(text("UPDATE password_resets SET used = true WHERE id = :id"), {"id": row["id"]})

        return render_template(request, "reset_password.html", {"msg": "Contraseña cambiada correctamente", "error": ""})

    except Exception as e:
        print(f"[RESET PASSWORD ERROR] {e}")
        return render_template(request, "reset_password.html", {"msg": "", "error": "Error al cambiar la contraseña"}, 500)

@app.get("/turnos", response_class=HTMLResponse)
def ver_turnos(request: Request):
    username, rol, response = require_login(request)
    if response: return response
    with engine.begin() as conn:
        turnos = conn.execute(text("SELECT tu.id, tu.fecha, tu.inicio_jornada, tu.fin_jornada, tu.total_horas, tr.nombre, tr.apellidos FROM turnos tu LEFT JOIN trabajadores tr ON tr.id = tu.trabajador_id ORDER BY tu.fecha DESC")).mappings().all()
        trabajadores = conn.execute(text("SELECT id, nombre, apellidos FROM trabajadores ORDER BY nombre")).mappings().all()
    return render_template(request, "turnos.html", {"turnos":turnos,"trabajadores":trabajadores,"username":username,"rol":rol,"active_page":"turnos"})

@app.post("/turnos/nuevo")
def crear_turno(request: Request, trabajador_id: str = Form(...), fecha: str = Form(...), inicio: str = Form(""), fin: str = Form(""), horas: str = Form(""), observaciones: str = Form("")):
    username, rol, response = require_admin(request)
    if response: return response
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO turnos (trabajador_id, fecha, inicio_jornada, fin_jornada, total_horas, observaciones) VALUES (:t,:f,:i,:fi,:h,:o)"),{"t":int(trabajador_id),"f":fecha,"i":inicio or None,"fi":fin or None,"h":horas or None,"o":observaciones})
    return RedirectResponse(url="/turnos", status_code=303)


@app.get("/turnos/exportar-excel")
def exportar_turnos_excel(request: Request):
    username, rol, response = require_login(request)
    if response:
        return response

    with engine.begin() as conn:
        turnos = conn.execute(text("""
            SELECT tu.id, tu.fecha, tu.turno, tu.hora_inicio, tu.hora_fin, tu.estado, tu.observaciones,
                   z.nombre AS zona, tr.nombre, tr.apellidos
            FROM turnos tu
            LEFT JOIN trabajadores tr ON tr.id = tu.trabajador_id
            LEFT JOIN zonas z ON z.id = tu.zona_id
            ORDER BY tu.fecha DESC, tu.hora_inicio ASC, tu.id DESC
        """)).mappings().all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Turnos"

    rojo = PatternFill("solid", fgColor="C00000")
    negro = PatternFill("solid", fgColor="111111")
    gris = PatternFill("solid", fgColor="F2F2F2")
    blanca = Font(color="FFFFFF", bold=True)
    negra = Font(color="000000", bold=True)
    titulo = Font(size=16, bold=True)
    borde = Border(
        left=Side(style="thin", color="000000"),
        right=Side(style="thin", color="000000"),
        top=Side(style="thin", color="000000"),
        bottom=Side(style="thin", color="000000")
    )
    centrado = Alignment(horizontal="center", vertical="center")
    izquierda = Alignment(horizontal="left", vertical="center", wrap_text=True)

    ws.merge_cells("A1:H1")
    ws["A1"] = "LISTADO DE TURNOS"
    ws["A1"].font = titulo
    ws["A1"].alignment = centrado

    ws["A3"] = "Total turnos"
    ws["B3"] = len(turnos)

    ws["A3"].fill = negro
    ws["A3"].font = blanca
    ws["A3"].border = borde
    ws["A3"].alignment = izquierda

    ws["B3"].fill = gris
    ws["B3"].font = negra
    ws["B3"].border = borde
    ws["B3"].alignment = izquierda

    encabezados = ["ID", "Empleado", "Fecha", "Turno", "Inicio", "Fin", "Zona", "Estado"]
    fila = 5
    for i, e in enumerate(encabezados, start=1):
        c = ws.cell(row=fila, column=i, value=e)
        c.fill = rojo
        c.font = blanca
        c.border = borde
        c.alignment = centrado

    fila += 1
    for tu in turnos:
        empleado = f"{tu['nombre'] or ''} {tu['apellidos'] or ''}".strip()
        valores = [
            tu["id"],
            empleado,
            str(tu["fecha"] or ""),
            tu["turno"] or "",
            str(tu["hora_inicio"] or ""),
            str(tu["hora_fin"] or ""),
            tu["zona"] or "",
            tu["estado"] or ""
        ]
        for col, val in enumerate(valores, start=1):
            c = ws.cell(row=fila, column=col, value=val)
            c.border = borde
            c.alignment = centrado if col in (1, 3, 4, 5, 6, 8) else izquierda
        fila += 1

    ws.column_dimensions["A"].width = 10
    ws.column_dimensions["B"].width = 28
    ws.column_dimensions["C"].width = 16
    ws.column_dimensions["D"].width = 16
    ws.column_dimensions["E"].width = 14
    ws.column_dimensions["F"].width = 14
    ws.column_dimensions["G"].width = 24
    ws.column_dimensions["H"].width = 16

    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)

    return StreamingResponse(
        bio,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=turnos.xlsx"}
    )

@app.get("/turnos/{id}", response_class=HTMLResponse)
def detalle_turno(request: Request, id: int):
    username, rol, response = require_login(request)
    if response: return response
    with engine.begin() as conn:
        turno = conn.execute(text("SELECT tu.*, tr.nombre, tr.apellidos FROM turnos tu LEFT JOIN trabajadores tr ON tr.id = tu.trabajador_id WHERE tu.id=:id"),{"id":id}).mappings().first()
        lineas = conn.execute(text("SELECT * FROM turno_lineas WHERE turno_id=:id"),{"id":id}).mappings().all()
    return render_template(request,"turno_detalle.html",{"turno":turno,"lineas":lineas,"username":username,"rol":rol,"active_page":"turnos"})

@app.post("/turnos/{id}/add_linea")
def add_linea(request: Request, id:int, hora_inicio:str=Form(...), hora_fin:str=Form(...), tarea:str=Form(...)):
    username, rol, response = require_admin(request)
    if response: return response
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO turno_lineas (turno_id,hora_inicio,hora_fin,tarea) VALUES (:t,:hi,:hf,:ta)"),{"t":id,"hi":hora_inicio,"hf":hora_fin,"ta":tarea})
    return RedirectResponse(url=f"/turnos/{id}", status_code=303)

@app.get("/turnos/{id}/del_linea/{lid}")
def del_linea(request: Request, id:int, lid:int):
    username, rol, response = require_admin(request)
    if response: return response
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM turno_lineas WHERE id=:id"),{"id":lid})
    return RedirectResponse(url=f"/turnos/{id}", status_code=303)

@app.get("/turnos/delete/{id}")
def eliminar_turno(request: Request, id:int):
    username, rol, response = require_admin(request)
    if response: return response
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM turnos WHERE id=:id"),{"id":id})
    return RedirectResponse(url="/turnos", status_code=303)
@app.get("/turnos", response_class=HTMLResponse)
def ver_turnos(request: Request):
    username, rol, response = require_login(request)
    if response: return response
    with engine.begin() as conn:
        turnos = conn.execute(text("SELECT tu.id, tu.fecha, tu.inicio_jornada, tu.fin_jornada, tu.total_horas, tr.nombre, tr.apellidos FROM turnos tu LEFT JOIN trabajadores tr ON tr.id = tu.trabajador_id ORDER BY tu.fecha DESC")).mappings().all()
        trabajadores = conn.execute(text("SELECT id, nombre, apellidos FROM trabajadores ORDER BY nombre")).mappings().all()
    return render_template(request, "turnos.html", {"turnos":turnos,"trabajadores":trabajadores,"username":username,"rol":rol,"active_page":"turnos"})

@app.post("/turnos/nuevo")
def crear_turno(request: Request, trabajador_id: str = Form(...), fecha: str = Form(...), inicio: str = Form(""), fin: str = Form(""), horas: str = Form(""), observaciones: str = Form("")):
    username, rol, response = require_admin(request)
    if response: return response
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO turnos (trabajador_id, fecha, inicio_jornada, fin_jornada, total_horas, observaciones) VALUES (:t,:f,:i,:fi,:h,:o)"),{"t":int(trabajador_id),"f":fecha,"i":inicio or None,"fi":fin or None,"h":horas or None,"o":observaciones})
    return RedirectResponse(url="/turnos", status_code=303)


@app.get("/turnos/exportar-excel")
def exportar_turnos_excel(request: Request):
    username, rol, response = require_login(request)
    if response:
        return response

    with engine.begin() as conn:
        turnos = conn.execute(text("""
            SELECT tu.id, tu.fecha, tu.turno, tu.hora_inicio, tu.hora_fin, tu.estado, tu.observaciones,
                   z.nombre AS zona, tr.nombre, tr.apellidos
            FROM turnos tu
            LEFT JOIN trabajadores tr ON tr.id = tu.trabajador_id
            LEFT JOIN zonas z ON z.id = tu.zona_id
            ORDER BY tu.fecha DESC, tu.hora_inicio ASC, tu.id DESC
        """)).mappings().all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Turnos"

    rojo = PatternFill("solid", fgColor="C00000")
    negro = PatternFill("solid", fgColor="111111")
    gris = PatternFill("solid", fgColor="F2F2F2")
    blanca = Font(color="FFFFFF", bold=True)
    negra = Font(color="000000", bold=True)
    titulo = Font(size=16, bold=True)
    borde = Border(
        left=Side(style="thin", color="000000"),
        right=Side(style="thin", color="000000"),
        top=Side(style="thin", color="000000"),
        bottom=Side(style="thin", color="000000")
    )
    centrado = Alignment(horizontal="center", vertical="center")
    izquierda = Alignment(horizontal="left", vertical="center", wrap_text=True)

    ws.merge_cells("A1:H1")
    ws["A1"] = "LISTADO DE TURNOS"
    ws["A1"].font = titulo
    ws["A1"].alignment = centrado

    ws["A3"] = "Total turnos"
    ws["B3"] = len(turnos)

    ws["A3"].fill = negro
    ws["A3"].font = blanca
    ws["A3"].border = borde
    ws["A3"].alignment = izquierda

    ws["B3"].fill = gris
    ws["B3"].font = negra
    ws["B3"].border = borde
    ws["B3"].alignment = izquierda

    encabezados = ["ID", "Empleado", "Fecha", "Turno", "Inicio", "Fin", "Zona", "Estado"]
    fila = 5
    for i, e in enumerate(encabezados, start=1):
        c = ws.cell(row=fila, column=i, value=e)
        c.fill = rojo
        c.font = blanca
        c.border = borde
        c.alignment = centrado

    fila += 1
    for tu in turnos:
        empleado = f"{tu['nombre'] or ''} {tu['apellidos'] or ''}".strip()
        valores = [
            tu["id"],
            empleado,
            str(tu["fecha"] or ""),
            tu["turno"] or "",
            str(tu["hora_inicio"] or ""),
            str(tu["hora_fin"] or ""),
            tu["zona"] or "",
            tu["estado"] or ""
        ]
        for col, val in enumerate(valores, start=1):
            c = ws.cell(row=fila, column=col, value=val)
            c.border = borde
            c.alignment = centrado if col in (1, 3, 4, 5, 6, 8) else izquierda
        fila += 1

    ws.column_dimensions["A"].width = 10
    ws.column_dimensions["B"].width = 28
    ws.column_dimensions["C"].width = 16
    ws.column_dimensions["D"].width = 16
    ws.column_dimensions["E"].width = 14
    ws.column_dimensions["F"].width = 14
    ws.column_dimensions["G"].width = 24
    ws.column_dimensions["H"].width = 16

    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)

    return StreamingResponse(
        bio,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=turnos.xlsx"}
    )

@app.get("/turnos/{id}", response_class=HTMLResponse)
def detalle_turno(request: Request, id: int):
    username, rol, response = require_login(request)
    if response: return response
    with engine.begin() as conn:
        turno = conn.execute(text("SELECT tu.*, tr.nombre, tr.apellidos FROM turnos tu LEFT JOIN trabajadores tr ON tr.id = tu.trabajador_id WHERE tu.id=:id"),{"id":id}).mappings().first()
        lineas = conn.execute(text("SELECT * FROM turno_lineas WHERE turno_id=:id"),{"id":id}).mappings().all()
    return render_template(request,"turno_detalle.html",{"turno":turno,"lineas":lineas,"username":username,"rol":rol,"active_page":"turnos"})

@app.post("/turnos/{id}/add_linea")
def add_linea(request: Request, id:int, hora_inicio:str=Form(...), hora_fin:str=Form(...), tarea:str=Form(...)):
    username, rol, response = require_admin(request)
    if response: return response
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO turno_lineas (turno_id,hora_inicio,hora_fin,tarea) VALUES (:t,:hi,:hf,:ta)"),{"t":id,"hi":hora_inicio,"hf":hora_fin,"ta":tarea})
    return RedirectResponse(url=f"/turnos/{id}", status_code=303)

@app.get("/turnos/{id}/del_linea/{lid}")
def del_linea(request: Request, id:int, lid:int):
    username, rol, response = require_admin(request)
    if response: return response
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM turno_lineas WHERE id=:id"),{"id":lid})
    return RedirectResponse(url=f"/turnos/{id}", status_code=303)

@app.get("/turnos/delete/{id}")
def eliminar_turno(request: Request, id:int):
    username, rol, response = require_admin(request)
    if response: return response
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM turnos WHERE id=:id"),{"id":id})
    return RedirectResponse(url="/turnos", status_code=303)



@app.get("/rutas", response_class=HTMLResponse)
def ver_rutas(request: Request):
    username, rol, response = require_login(request)
    if response:
        return response

    with engine.begin() as conn:
        rutas = conn.execute(text("""
            SELECT r.id, r.trabajador_id, t.nombre AS trabajador_nombre, t.apellidos AS trabajador_apellidos,
                   r.fecha, r.hora_inicio_jornada, r.hora_fin_jornada, r.total_horas, r.observaciones_generales
            FROM rutas r
            INNER JOIN trabajadores t ON r.trabajador_id = t.id
            ORDER BY r.fecha DESC, r.hora_inicio_jornada ASC
        """)).mappings().all()

        trabajadores = conn.execute(text("""
            SELECT id, nombre, apellidos
            FROM trabajadores
            ORDER BY nombre, apellidos
        """)).mappings().all()

    return render_template(request, "rutas.html", {
        "username": username,
        "rol": rol,
        "rutas": rutas,
        "trabajadores": trabajadores,
        "active_page": "rutas"
    })

@app.post("/rutas/nueva")
def crear_ruta_web(request: Request, trabajador_id: str = Form(...), fecha: str = Form(...), inicio_jornada: str = Form(...), fin_jornada: str = Form(...), total_horas: str = Form("8.00"), observaciones: str = Form("")):
    username, rol, response = require_admin(request)
    if response:
        return response

    try:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO rutas (
                    trabajador_id,
                    fecha,
                    hora_inicio_jornada,
                    hora_fin_jornada,
                    total_horas,
                    observaciones_generales
                ) VALUES (
                    :trabajador_id,
                    :fecha,
                    :inicio,
                    :fin,
                    :total_horas,
                    :observaciones
                )
            """), {
                "trabajador_id": int(trabajador_id),
                "fecha": fecha,
                "inicio": inicio_jornada,
                "fin": fin_jornada,
                "total_horas": float(total_horas),
                "observaciones": observaciones.strip() or None
            })
        return RedirectResponse(url="/rutas", status_code=303)
    except Exception as e:
        print(f"[RUTAS NUEVA ERROR] {e}")
        return RedirectResponse(url="/rutas", status_code=303)

@app.get("/rutas/{id}", response_class=HTMLResponse)
def detalle_ruta(request: Request, id: int):
    username, rol, response = require_login(request)
    if response:
        return response

    with engine.begin() as conn:
        ruta = conn.execute(text("""
            SELECT r.id, r.trabajador_id, t.nombre AS trabajador_nombre, t.apellidos AS trabajador_apellidos,
                   r.fecha, r.hora_inicio_jornada, r.hora_fin_jornada, r.total_horas, r.observaciones_generales
            FROM rutas r
            INNER JOIN trabajadores t ON r.trabajador_id = t.id
            WHERE r.id = :id
        """), {"id": id}).mappings().first()

        if not ruta:
            return RedirectResponse(url="/rutas", status_code=303)

        lineas = conn.execute(text("""
            SELECT id, ruta_id, zona, hora_inicio, hora_fin, duracion_minutos, estado, observaciones
            FROM rutas_detalle
            WHERE ruta_id = :id
            ORDER BY hora_inicio ASC
        """), {"id": id}).mappings().all()

    return render_template(request, "ruta_detalle.html", {
        "username": username,
        "rol": rol,
        "ruta": ruta,
        "lineas": lineas,
        "active_page": "rutas"
    })

@app.post("/rutas/{id}/lineas/nueva")
def crear_ruta_linea_web(request: Request, id: int, hora_inicio: str = Form(...), hora_fin: str = Form(...), tarea: str = Form(...)):
    username, rol, response = require_admin(request)
    if response:
        return response

    try:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO rutas_detalle (
                    ruta_id,
                    zona,
                    hora_inicio,
                    hora_fin,
                    duracion_minutos,
                    estado,
                    observaciones
                ) VALUES (
                    :ruta_id,
                    :zona,
                    :hora_inicio,
                    :hora_fin,
                    0,
                    'pendiente',
                    NULL
                )
            """), {
                "ruta_id": id,
                "zona": tarea.strip(),
                "hora_inicio": hora_inicio,
                "hora_fin": hora_fin
            })
        return RedirectResponse(url=f"/rutas/{id}", status_code=303)
    except Exception as e:
        print(f"[RUTAS LINEA ERROR] {e}")
        return RedirectResponse(url=f"/rutas/{id}", status_code=303)

@app.get("/rutas/{id}/lineas/eliminar/{linea_id}")
def eliminar_ruta_linea_web(request: Request, id: int, linea_id: int):
    username, rol, response = require_admin(request)
    if response:
        return response

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM rutas_detalle WHERE id = :id"), {"id": linea_id})

    return RedirectResponse(url=f"/rutas/{id}", status_code=303)

@app.get("/rutas/eliminar/{id}")
def eliminar_ruta_web(request: Request, id: int):
    username, rol, response = require_admin(request)
    if response:
        return response

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM rutas WHERE id = :id"), {"id": id})

    return RedirectResponse(url="/rutas", status_code=303)



@app.get("/horas", response_class=HTMLResponse)
def ver_horas(request: Request):
    username, rol, response = require_login(request)
    if response:
        return response

    with engine.begin() as conn:
        horas = conn.execute(text("""
            SELECT h.id, t.nombre, t.apellidos, h.fecha, h.horas, h.horas_extra, h.tipo
            FROM horas_trabajadas h
            JOIN trabajadores t ON h.trabajador_id = t.id
            ORDER BY h.fecha DESC, h.id DESC
        """)).mappings().all()

        trabajadores = conn.execute(text("""
            SELECT id, nombre, apellidos
            FROM trabajadores
            ORDER BY nombre, apellidos
        """)).mappings().all()

    return render_template(request, "horas.html", {
        "username": username,
        "rol": rol,
        "horas": horas,
        "trabajadores": trabajadores,
        "active_page": "horas"
    })

@app.post("/horas/nueva")
def crear_horas_web(
    request: Request,
    trabajador_id: str = Form(...),
    fecha: str = Form(...),
    horas: str = Form(...),
    horas_extra: str = Form("0"),
    tipo: str = Form("normal")
):
    username, rol, response = require_admin(request)
    if response:
        return response

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
                "tipo": tipo.strip() or "normal"
            })
        return RedirectResponse(url="/horas", status_code=303)
    except Exception as e:
        print(f"[HORAS NUEVA ERROR] {e}")
        return RedirectResponse(url="/horas", status_code=303)

@app.get("/horas/eliminar/{id}")
def eliminar_horas_web(request: Request, id: int):
    username, rol, response = require_admin(request)
    if response:
        return response

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM horas_trabajadas WHERE id = :id"), {"id": id})

    return RedirectResponse(url="/horas", status_code=303)



@app.get("/ausencias", response_class=HTMLResponse)
def ver_ausencias(request: Request):
    username, rol, response = require_login(request)
    if response:
        return response

    with engine.begin() as conn:
        ausencias = conn.execute(text("""
            SELECT a.id, t.nombre, t.apellidos, a.tipo, a.fecha_inicio, a.fecha_fin, a.motivo, a.estado
            FROM ausencias a
            JOIN trabajadores t ON a.trabajador_id = t.id
            ORDER BY a.fecha_inicio DESC, a.id DESC
        """)).mappings().all()

        trabajadores = conn.execute(text("""
            SELECT id, nombre, apellidos
            FROM trabajadores
            ORDER BY nombre, apellidos
        """)).mappings().all()

    return render_template(request, "ausencias.html", {
        "username": username,
        "rol": rol,
        "ausencias": ausencias,
        "trabajadores": trabajadores,
        "active_page": "ausencias"
    })

@app.post("/ausencias/nueva")
def crear_ausencia_web(
    request: Request,
    trabajador_id: str = Form(...),
    tipo: str = Form(...),
    fecha_inicio: str = Form(...),
    fecha_fin: str = Form(...),
    motivo: str = Form(""),
    estado: str = Form("pendiente")
):
    username, rol, response = require_admin(request)
    if response:
        return response

    try:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO ausencias (trabajador_id, tipo, fecha_inicio, fecha_fin, motivo, estado)
                VALUES (:trabajador_id, :tipo, :fecha_inicio, :fecha_fin, :motivo, :estado)
            """), {
                "trabajador_id": int(trabajador_id),
                "tipo": tipo.strip(),
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
                "motivo": motivo.strip() or None,
                "estado": estado.strip() or "pendiente"
            })
        return RedirectResponse(url="/ausencias", status_code=303)
    except Exception as e:
        print(f"[AUSENCIAS NUEVA ERROR] {e}")
        return RedirectResponse(url="/ausencias", status_code=303)

@app.get("/ausencias/eliminar/{id}")
def eliminar_ausencia_web(request: Request, id: int):
    username, rol, response = require_admin(request)
    if response:
        return response

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM ausencias WHERE id = :id"), {"id": id})

    return RedirectResponse(url="/ausencias", status_code=303)



@app.get("/productos", response_class=HTMLResponse)
def ver_productos(request: Request):
    username, rol, response = require_login(request)
    if response:
        return response

    with engine.begin() as conn:
        productos = conn.execute(text("""
            SELECT id, nombre, categoria, stock
            FROM productos
            ORDER BY id DESC
        """)).mappings().all()

    return render_template(request, "productos.html", {
        "username": username,
        "rol": rol,
        "productos": productos,
        "active_page": "productos"
    })

@app.post("/productos/nuevo")
def crear_producto_web(
    request: Request,
    nombre: str = Form(...),
    categoria: str = Form(""),
    stock: str = Form("0")
):
    username, rol, response = require_admin(request)
    if response:
        return response

    try:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO productos (nombre, categoria, stock)
                VALUES (:nombre, :categoria, :stock)
            """), {
                "nombre": nombre.strip(),
                "categoria": categoria.strip() or None,
                "stock": int(stock or 0)
            })
        return RedirectResponse(url="/productos", status_code=303)
    except Exception as e:
        print(f"[PRODUCTOS NUEVO ERROR] {e}")
        return RedirectResponse(url="/productos", status_code=303)

@app.get("/productos/eliminar/{id}")
def eliminar_producto_web(request: Request, id: int):
    username, rol, response = require_admin(request)
    if response:
        return response

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM productos WHERE id = :id"), {"id": id})

    return RedirectResponse(url="/productos", status_code=303)



@app.get("/productos/restar/{id}")
def restar_producto(request: Request, id: int):
    username, rol, response = require_admin(request)
    if response:
        return response

    with engine.begin() as conn:
        conn.execute(text("UPDATE productos SET stock = GREATEST(stock - 1, 0) WHERE id = :id"), {"id": id})

    return RedirectResponse(url="/productos", status_code=303)



@app.get("/zonas", response_class=HTMLResponse)
def ver_zonas(request: Request):
    username, rol, response = require_login(request)
    if response:
        return response

    with engine.begin() as conn:
        zonas = conn.execute(text("""
            SELECT id, nombre, tipo, activo
            FROM zonas
            ORDER BY nombre ASC, id DESC
        """)).mappings().all()

    return render_template(request, "zonas.html", {
        "username": username,
        "rol": rol,
        "zonas": zonas,
        "active_page": "zonas"
    })

@app.post("/zonas/nueva")
def crear_zona_web(
    request: Request,
    nombre: str = Form(...),
    tipo: str = Form(""),
    activo: str = Form("true")
):
    username, rol, response = require_admin(request)
    if response:
        return response

    try:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO zonas (nombre, tipo, activo)
                VALUES (:nombre, :tipo, :activo)
            """), {
                "nombre": nombre.strip(),
                "tipo": tipo.strip() or None,
                "activo": activo.lower() == "true"
            })
        return RedirectResponse(url="/zonas", status_code=303)
    except Exception as e:
        print(f"[ZONAS NUEVA ERROR] {e}")
        return RedirectResponse(url="/zonas", status_code=303)

@app.get("/zonas/toggle/{id}")
def toggle_zona_web(request: Request, id: int):
    username, rol, response = require_admin(request)
    if response:
        return response

    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE zonas
            SET activo = NOT activo
            WHERE id = :id
        """), {"id": id})

    return RedirectResponse(url="/zonas", status_code=303)

@app.get("/zonas/eliminar/{id}")
def eliminar_zona_web(request: Request, id: int):
    username, rol, response = require_admin(request)
    if response:
        return response

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM zonas WHERE id = :id"), {"id": id})

    return RedirectResponse(url="/zonas", status_code=303)



@app.get("/productos/exportar")
def exportar_productos_excel(request: Request):
    username, rol, response = require_login(request)
    if response:
        return response

    with engine.begin() as conn:
        productos = conn.execute(text("""
            SELECT id, nombre, categoria, stock
            FROM productos
            ORDER BY id DESC
        """)).mappings().all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Productos"

    rojo = PatternFill("solid", fgColor="C00000")
    negro = PatternFill("solid", fgColor="111111")
    gris = PatternFill("solid", fgColor="F2F2F2")
    blanca = Font(color="FFFFFF", bold=True)
    negra = Font(color="000000", bold=True)
    titulo = Font(size=16, bold=True)
    borde = Border(
        left=Side(style="thin", color="000000"),
        right=Side(style="thin", color="000000"),
        top=Side(style="thin", color="000000"),
        bottom=Side(style="thin", color="000000")
    )
    centrado = Alignment(horizontal="center", vertical="center")
    izquierda = Alignment(horizontal="left", vertical="center")

    ws.merge_cells("A1:D1")
    ws["A1"] = "LISTADO DE PRODUCTOS"
    ws["A1"].font = titulo
    ws["A1"].alignment = centrado

    ws["A3"] = "Total productos"
    ws["B3"] = len(productos)

    ws["A3"].fill = negro
    ws["A3"].font = blanca
    ws["A3"].border = borde
    ws["A3"].alignment = izquierda

    ws["B3"].fill = gris
    ws["B3"].font = negra
    ws["B3"].border = borde
    ws["B3"].alignment = izquierda

    encabezados = ["ID", "Nombre", "Categoría", "Stock"]
    fila = 5
    for i, e in enumerate(encabezados, start=1):
        c = ws.cell(row=fila, column=i, value=e)
        c.fill = rojo
        c.font = blanca
        c.border = borde
        c.alignment = centrado

    fila += 1
    for prod in productos:
        valores = [
            prod["id"],
            prod["nombre"],
            prod["categoria"] or "",
            prod["stock"]
        ]
        for col, val in enumerate(valores, start=1):
            c = ws.cell(row=fila, column=col, value=val)
            c.border = borde
            c.alignment = izquierda if col in (2, 3) else centrado
        fila += 1

    ws.column_dimensions["A"].width = 10
    ws.column_dimensions["B"].width = 35
    ws.column_dimensions["C"].width = 25
    ws.column_dimensions["D"].width = 12

    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)

    return StreamingResponse(
        bio,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=productos.xlsx"}
    )



@app.get("/tareas/exportar")
def exportar_tareas_excel(request: Request):
    username, rol, response = require_login(request)
    if response:
        return response

    with engine.begin() as conn:
        tareas = conn.execute(text("""
            SELECT ta.id, ta.titulo, ta.descripcion, ta.estado, ta.prioridad,
                   ta.fecha_asignacion, ta.fecha_vencimiento,
                   tr.nombre, tr.apellidos
            FROM tareas ta
            LEFT JOIN trabajadores tr ON tr.id = ta.trabajador_id
            ORDER BY ta.fecha_asignacion DESC, ta.id DESC
        """)).mappings().all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Tareas"

    rojo = PatternFill("solid", fgColor="C00000")
    negro = PatternFill("solid", fgColor="111111")
    gris = PatternFill("solid", fgColor="F2F2F2")
    blanca = Font(color="FFFFFF", bold=True)
    negra = Font(color="000000", bold=True)
    titulo = Font(size=16, bold=True)
    borde = Border(
        left=Side(style="thin", color="000000"),
        right=Side(style="thin", color="000000"),
        top=Side(style="thin", color="000000"),
        bottom=Side(style="thin", color="000000")
    )
    centrado = Alignment(horizontal="center", vertical="center")
    izquierda = Alignment(horizontal="left", vertical="center", wrap_text=True)

    ws.merge_cells("A1:H1")
    ws["A1"] = "LISTADO DE TAREAS"
    ws["A1"].font = titulo
    ws["A1"].alignment = centrado

    ws["A3"] = "Total tareas"
    ws["B3"] = len(tareas)

    ws["A3"].fill = negro
    ws["A3"].font = blanca
    ws["A3"].border = borde
    ws["A3"].alignment = izquierda

    ws["B3"].fill = gris
    ws["B3"].font = negra
    ws["B3"].border = borde
    ws["B3"].alignment = izquierda

    encabezados = ["ID", "Título", "Descripción", "Trabajador", "Estado", "Prioridad", "Asignación", "Vencimiento"]
    fila = 5
    for i, e in enumerate(encabezados, start=1):
        c = ws.cell(row=fila, column=i, value=e)
        c.fill = rojo
        c.font = blanca
        c.border = borde
        c.alignment = centrado

    fila += 1
    for t in tareas:
        trabajador = f"{t['nombre'] or ''} {t['apellidos'] or ''}".strip()
        valores = [
            t["id"],
            t["titulo"] or "",
            t["descripcion"] or "",
            trabajador,
            t["estado"] or "",
            t["prioridad"] or "",
            str(t["fecha_asignacion"] or ""),
            str(t["fecha_vencimiento"] or "")
        ]
        for col, val in enumerate(valores, start=1):
            c = ws.cell(row=fila, column=col, value=val)
            c.border = borde
            c.alignment = centrado if col in (1, 5, 6, 7, 8) else izquierda
        fila += 1

    ws.column_dimensions["A"].width = 10
    ws.column_dimensions["B"].width = 28
    ws.column_dimensions["C"].width = 40
    ws.column_dimensions["D"].width = 26
    ws.column_dimensions["E"].width = 16
    ws.column_dimensions["F"].width = 14
    ws.column_dimensions["G"].width = 16
    ws.column_dimensions["H"].width = 16

    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)

    return StreamingResponse(
        bio,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=tareas.xlsx"}
    )



