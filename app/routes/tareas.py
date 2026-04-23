from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import text

from app.core.db import engine
from app.core.security import require_login, require_admin
from app.core.utils import render_template

router = APIRouter()

@router.get("/tareas", response_class=HTMLResponse)
def ver_tareas(request: Request):
    username, rol, response = require_login(request)
    if response:
        return response

    with engine.begin() as conn:
        tareas = conn.execute(text("""
            SELECT ta.id, ta.titulo, ta.estado, tr.nombre
            FROM tareas ta
            LEFT JOIN trabajadores tr ON tr.id = ta.trabajador_id
        """)).mappings().all()

    return render_template(request, "tareas.html", {
        "tareas": tareas,
        "username": username,
        "rol": rol
    })
