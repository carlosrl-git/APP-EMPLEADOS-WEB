import secrets
import string
import unicodedata

from app.ai.query_analyzer import analyze_question
from app.ai.data_extractor import extract_user_data
from app.ai.worker_extractor import extract_worker_data
from app.ai.incident_extractor import extract_incident_data
from app.ai.absence_extractor import extract_absence_data
from app.ai.hours_extractor import extract_hours_data
from app.ai.shift_extractor import extract_shift_data
from app.ai.product_extractor import extract_product_data
from app.ai.zone_extractor import extract_zone_data
from app.ai.task_extractor import extract_task_data
from app.ai.incident_state import save_incident_state, get_incident_state, clear_incident_state
from app.ai.ai_logger import log_ai_action
from app.ai.agent_queries import (
    get_total_employees,
    get_employees_with_most_incidents,
    get_open_incidents_count,
    create_user,
    create_worker,
    create_incident,
)
from app.ai.absence_queries import create_absence
from app.ai.hours_queries import create_hours
from app.ai.shift_queries import create_shift
from app.ai.product_queries import create_product
from app.ai.zone_queries import create_zone
from app.ai.task_queries import create_task
from app.ai.task_stats import get_pending_tasks
from app.ai.memory import save_last_action, get_last_action


def normalize_username(name: str) -> str:
    return name.lower().replace(" ", ".")


def normalize_email(name: str) -> str:
    return name.lower().replace(" ", ".") + "@empresa.local"


def generate_password(length: int = 12) -> str:
    chars = string.ascii_letters + string.digits + "!@#$%*_-"
    return "".join(secrets.choice(chars) for _ in range(length))


def can_manage(session_role: str | None) -> bool:
    return (session_role or "").strip().lower() == "admin"


def normalize_text(text: str) -> str:
    text = (text or "").strip().lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    for ch in ["¿", "?", "¡", "!", ".", ",", ";", ":", "(", ")", "[", "]", "{", "}", '"', "'"]:
        text = text.replace(ch, " ")
    text = " ".join(text.split())
    return text


def contains_any(text: str, options: list[str]) -> bool:
    return any(opt in text for opt in options)


def is_confirmation(text: str) -> bool:
    return text in ["si", "sí", "confirmar", "ok", "vale", "de acuerdo"]


def is_employee_count_question(q: str) -> bool:
    return (
        contains_any(q, ["cuantos empleados", "cuantas empleados", "numero de empleados", "cantidad de empleados"])
        or ("empleados" in q and contains_any(q, ["hay", "registrados", "actualmente", "total"]))
    )


def is_open_incidents_count_question(q: str) -> bool:
    return (
        contains_any(
            q,
            [
                "cuantas incidencias abiertas",
                "cuantos incidencias abiertas",
                "incidencias abiertas hay",
                "numero de incidencias abiertas",
                "cantidad de incidencias abiertas",
            ],
        )
        or ("incidencias" in q and "abiertas" in q)
        or ("incidencia" in q and "abierta" in q and contains_any(q, ["hay", "cuantas", "cuantos", "numero", "cantidad"]))
    )


def is_summary_question(q: str) -> bool:
    return contains_any(
        q,
        [
            "hazme un resumen",
            "dame un resumen",
            "resumen general",
            "resumen del estado actual",
            "resumen de la situacion actual",
            "resumen de empleados incidencias y tareas",
            "estado actual de empleados incidencias y tareas",
        ],
    )


def is_top_incidents_question(q: str) -> bool:
    return (
        ("empleados" in q or "trabajadores" in q)
        and "incidenc" in q
        and contains_any(
            q,
            [
                "mas incidencias",
                "más incidencias",
                "tienen mas incidencias",
                "tienen más incidencias",
                "con mas incidencias",
                "con más incidencias",
            ],
        )
    )


def format_pending_tasks() -> str:
    tasks = get_pending_tasks()
    if not tasks:
        return "No hay tareas pendientes."

    response = "Tareas pendientes:\n"
    for t in tasks[:10]:
        nombre = ((t["nombre"] or "") + " " + (t["apellidos"] or "")).strip() or "Sin asignar"
        venc = t["fecha_vencimiento"] if t["fecha_vencimiento"] else "-"
        response += f'- [{t["id"]}] {t["titulo"]} | {nombre} | vence: {venc}\n'
    return response


def format_top_incidents() -> str:
    rows = get_employees_with_most_incidents()

    if not rows:
        return "No hay incidencias registradas."

    response = "Empleados con más incidencias:\n"
    for r in rows[:10]:
        nombre = ((r.get("nombre") or "") + " " + (r.get("apellidos") or "")).strip() or "Sin nombre"
        total = r.get("total_incidencias") or r.get("incidencias") or r.get("total") or 0
        response += f"- {nombre}: {total}\n"
    return response.strip()


def run_agent(question: str, session_role: str | None = None, session_user: str | None = None):
    q = normalize_text(question)

    if is_confirmation(q):
        last = get_last_action()

        if last and last.get("action") in [
            "create_user",
            "create_worker",
            "create_incident",
            "create_absence",
            "create_hours",
            "create_shift",
            "create_product",
            "create_zone",
            "create_task",
        ] and not can_manage(session_role):
            return "No tienes permisos para ejecutar esta accion desde la IA."

        if last and last.get("action") == "create_task":
            ok, msg = create_task(
                trabajador_id=last["trabajador_id"],
                titulo=last["titulo"],
                descripcion=last["descripcion"],
                prioridad=last["prioridad"],
                estado=last["estado"],
                fecha_asignacion=last["fecha_asignacion"],
                fecha_vencimiento=last["fecha_vencimiento"],
            )
            if ok:
                log_ai_action(session_user, "crear_tarea", last["titulo"])
            return msg

        if last and last.get("action") == "create_zone":
            ok, msg = create_zone(
                nombre=last["nombre"],
                tipo=last["tipo"],
                activo=last["activo"],
            )
            if ok:
                log_ai_action(session_user, "crear_zona", last["nombre"])
            return msg

        if last and last.get("action") == "create_product":
            ok, msg = create_product(
                nombre=last["nombre"],
                categoria=last["categoria"],
                stock=last["stock"],
            )
            if ok:
                log_ai_action(session_user, "crear_producto", last["nombre"])
            return msg

        if last and last.get("action") == "create_shift":
            ok, msg = create_shift(
                trabajador_id=last["trabajador_id"],
                fecha=last["fecha"],
                inicio_jornada=last["inicio_jornada"],
                fin_jornada=last["fin_jornada"],
                total_horas=last["total_horas"],
                observaciones=last["observaciones"],
            )
            if ok:
                log_ai_action(session_user, "crear_turno", f'{last["trabajador_id"]} {last["fecha"]}')
            return msg

        if last and last.get("action") == "create_hours":
            ok, msg = create_hours(
                trabajador_id=last["trabajador_id"],
                fecha=last["fecha"],
                horas=last["horas"],
                horas_extra=last["horas_extra"],
                tipo=last["tipo"],
            )
            if ok:
                log_ai_action(session_user, "crear_horas", f'{last["trabajador_id"]} {last["fecha"]}')
            return msg

        if last and last.get("action") == "create_absence":
            ok, msg = create_absence(
                trabajador_id=last["trabajador_id"],
                tipo=last["tipo"],
                fecha_inicio=last["fecha_inicio"],
                fecha_fin=last["fecha_fin"],
                motivo=last["motivo"],
                estado=last["estado"],
            )
            if ok:
                log_ai_action(session_user, "crear_ausencia", last["tipo"])
            return msg

        if last and last.get("action") == "create_incident":
            ok, msg = create_incident(
                descripcion=last["descripcion"],
                trabajador_id=last["trabajador_id"],
                estado=last["estado"],
            )
            if ok:
                log_ai_action(session_user, "crear_incidencia", last["descripcion"])
            clear_incident_state()
            return msg

        if last and last.get("action") == "create_user":
            ok, msg = create_user(
                username=last["username"],
                email=last["email"],
                password=last["password"],
                rol=last["role"],
            )
            if ok:
                log_ai_action(session_user, "crear_usuario", last["username"])
            return msg

        if last and last.get("action") == "create_worker":
            ok, msg = create_worker(
                nombre=last["nombre"],
                apellidos=last["apellidos"],
                email=last["email"],
                telefono=last["telefono"],
                puesto=last["puesto"],
                departamento_id=last["departamento_id"],
            )
            if ok:
                log_ai_action(session_user, "crear_trabajador", last["nombre"])
            return msg

        return "No hay ninguna accion pendiente."

    state = get_incident_state()
    if state:
        if not can_manage(session_role):
            clear_incident_state()
            return "No tienes permisos para crear incidencias desde la IA."

        if not state.get("descripcion"):
            state["descripcion"] = question
            save_incident_state(state)
            return "Indica el ID del trabajador."

        if not state.get("trabajador_id"):
            try:
                state["trabajador_id"] = int(q)
            except Exception:
                return "El trabajador debe ser un numero (ID)."
            save_incident_state(state)
            return "Indica el estado (o escribe 'abierta')."

        if not state.get("estado"):
            state["estado"] = q or "abierta"

            save_last_action({
                "action": "create_incident",
                "descripcion": state["descripcion"],
                "trabajador_id": state["trabajador_id"],
                "estado": state["estado"],
            })

            clear_incident_state()

            return f"""Preparada incidencia:
- Descripcion: {state["descripcion"]}
- Trabajador ID: {state["trabajador_id"]}
- Estado: {state["estado"]}

Escribe 'confirmar' para crearla."""

    if "tareas pendientes" in q or "tarea pendiente" in q:
        return format_pending_tasks()

    if "tarea" in q or "tareas" in q:
        if "crear" in q or "crea" in q:
            if not can_manage(session_role):
                return "No tienes permisos para crear tareas."

            data = extract_task_data(question)

            if data["trabajador_id"] and data["titulo"] and data["fecha_asignacion"]:
                save_last_action({
                    "action": "create_task",
                    **data,
                })

                return f"""Preparada tarea:
- Trabajador: {data["trabajador_id"]}
- Titulo: {data["titulo"]}
- Descripcion: {data["descripcion"]}
- Prioridad: {data["prioridad"]}
- Estado: {data["estado"]}
- Fecha asignacion: {data["fecha_asignacion"]}
- Fecha vencimiento: {data["fecha_vencimiento"]}

Escribe 'confirmar' para crearla."""

            return "Faltan datos: trabajador, titulo o fecha_asignacion."

    if "zona" in q or "zonas" in q:
        if "crear" in q or "crea" in q:
            if not can_manage(session_role):
                return "No tienes permisos para crear zonas."

            data = extract_zone_data(question)

            if data["nombre"]:
                save_last_action({
                    "action": "create_zone",
                    **data,
                })

                return f"""Preparada zona:
- Nombre: {data["nombre"]}
- Tipo: {data["tipo"]}
- Activo: {data["activo"]}

Escribe 'confirmar' para crearla."""

            return "Falta el nombre de la zona."

    if "producto" in q or "productos" in q:
        if "crear" in q or "crea" in q:
            if not can_manage(session_role):
                return "No tienes permisos para crear productos."

            data = extract_product_data(question)

            if data["nombre"]:
                save_last_action({
                    "action": "create_product",
                    **data,
                })

                return f"""Preparado producto:
- Nombre: {data["nombre"]}
- Categoria: {data["categoria"]}
- Stock: {data["stock"]}

Escribe 'confirmar' para crearlo."""

            return "Falta el nombre del producto."

    if "turno" in q or "turnos" in q:
        if "crear" in q or "crea" in q:
            if not can_manage(session_role):
                return "No tienes permisos para crear turnos."

            data = extract_shift_data(question)

            if data["trabajador_id"] and data["fecha"]:
                save_last_action({
                    "action": "create_shift",
                    **data,
                })

                return f"""Preparado turno:
- Trabajador: {data["trabajador_id"]}
- Fecha: {data["fecha"]}
- Inicio: {data["inicio_jornada"]}
- Fin: {data["fin_jornada"]}
- Horas totales: {data["total_horas"]}
- Observaciones: {data["observaciones"]}

Escribe 'confirmar' para crearlo."""

            return "Faltan datos: trabajador o fecha."

    if "horas" in q and ("crear" in q or "crea" in q or "registrar" in q):
        if not can_manage(session_role):
            return "No tienes permisos para crear horas."

        data = extract_hours_data(question)

        if data["trabajador_id"] and data["fecha"] and data["horas"] is not None:
            save_last_action({
                "action": "create_hours",
                **data,
            })

            return f"""Preparadas horas:
- Trabajador: {data["trabajador_id"]}
- Fecha: {data["fecha"]}
- Horas: {data["horas"]}
- Horas extra: {data["horas_extra"]}
- Tipo: {data["tipo"]}

Escribe 'confirmar' para crearlas."""

        return "Faltan datos: trabajador, fecha o horas."

    if "ausencia" in q or "vacaciones" in q:
        if "crear" in q or "crea" in q:
            if not can_manage(session_role):
                return "No tienes permisos para crear ausencias."

            data = extract_absence_data(question)

            if data["trabajador_id"] and data["tipo"] and data["fecha_inicio"]:
                save_last_action({
                    "action": "create_absence",
                    **data,
                })

                return f"""Preparada ausencia:
- Trabajador: {data["trabajador_id"]}
- Tipo: {data["tipo"]}
- Desde: {data["fecha_inicio"]}
- Hasta: {data["fecha_fin"]}
- Motivo: {data["motivo"]}
- Estado: {data["estado"]}

Escribe 'confirmar' para crearla."""

            return "Faltan datos: trabajador, tipo o fecha_inicio."

    if "incidencia" in q or "problema" in q:
        if "crear" in q or "crea" in q:
            if not can_manage(session_role):
                return "No tienes permisos para crear incidencias desde la IA."

            data = extract_incident_data(question)

            if data["descripcion"] and data["trabajador_id"]:
                save_last_action({
                    "action": "create_incident",
                    "descripcion": data["descripcion"],
                    "trabajador_id": data["trabajador_id"],
                    "estado": data["estado"] or "abierta",
                })

                return f"""Preparada incidencia:
- Descripcion: {data["descripcion"]}
- Trabajador ID: {data["trabajador_id"]}
- Estado: {data["estado"] or "abierta"}

Escribe 'confirmar' para crearla."""

            save_incident_state({
                "descripcion": data["descripcion"],
                "trabajador_id": data["trabajador_id"],
                "estado": None,
            })

            if not data["descripcion"]:
                return "¿Que descripcion tiene la incidencia?"
            if not data["trabajador_id"]:
                return "¿A que trabajador pertenece? (ID)"

    if ("trabajador" in q or "trabajadores" in q) and ("crear" in q or "crea" in q):
        if not can_manage(session_role):
            return "No tienes permisos para crear trabajadores desde la IA."

        data = extract_worker_data(question)

        if not data["nombre"]:
            return "Falta el nombre del trabajador."

        save_last_action({
            "action": "create_worker",
            **data,
        })

        return f"""Preparado trabajador:
- Nombre: {data["nombre"]}
- Apellidos: {data["apellidos"]}
- Email: {data["email"]}
- Telefono: {data["telefono"]}
- Puesto: {data["puesto"]}
- Departamento: {data["departamento_id"]}

Escribe 'confirmar' para crearlo."""

    if "usuario" in q and ("crear" in q or "crea" in q):
        if not can_manage(session_role):
            return "No tienes permisos para crear usuarios desde la IA."

        data = extract_user_data(question)

        if not data["name"] or not data["role"]:
            return "Faltan datos para crear el usuario."

        if not data["password"] and not data["generate_password"]:
            return "Indica una clave o pide generar una."

        username = normalize_username(data["name"])
        email = data["email"] or normalize_email(data["name"])
        password = data["password"] or generate_password()

        save_last_action({
            "action": "create_user",
            "username": username,
            "email": email,
            "password": password,
            "role": data["role"],
        })

        return f"""Preparado usuario:
- Username: {username}
- Email: {email}
- Rol: {data["role"]}
- Clave: {password}

Escribe 'confirmar' para crearlo."""

    if is_top_incidents_question(q):
        return format_top_incidents()

    if is_open_incidents_count_question(q):
        return f"Hay {get_open_incidents_count()} incidencias abiertas."

    if is_employee_count_question(q):
        return f"Actualmente hay {get_total_employees()} empleados."

    if is_summary_question(q):
        return (
            f"Resumen:\n"
            f"- Empleados: {get_total_employees()}\n"
            f"- Incidencias abiertas: {get_open_incidents_count()}\n"
            f"- Tareas pendientes: {len(get_pending_tasks())}"
        )

    analysis = analyze_question(question)

    if analysis["module"] == "employees" and analysis["action"] == "count":
        return f"Actualmente hay {get_total_employees()} empleados."

    if analysis["module"] == "incidents" and analysis["action"] == "count":
        return f"Hay {get_open_incidents_count()} incidencias abiertas."

    if analysis["action"] == "summary":
        return (
            f"Resumen:\n"
            f"- Empleados: {get_total_employees()}\n"
            f"- Incidencias abiertas: {get_open_incidents_count()}\n"
            f"- Tareas pendientes: {len(get_pending_tasks())}"
        )

    return "No he podido interpretar la consulta."