from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import text

from app.core.db import engine
from app.core.security import require_login, require_admin, get_current_empresa_id
from app.core.utils import render_template

router = APIRouter()

@router.get("/incidencias", response_class=HTMLResponse)
def ver_incidencias(request: Request):
    username, rol, response = require_login(request)
    if response:
        return response

    with engine.begin() as conn:
        incidencias = conn.execute(text("""
            SELECT i.id, i.descripcion, i.estado, i.fecha, t.nombre, t.apellidos
            FROM incidencias i
            LEFT JOIN trabajadores t ON t.id = i.trabajador_id
            WHERE i.empresa_id = :empresa_id
            ORDER BY i.fecha DESC
        """), {"empresa_id": get_current_empresa_id(request)}).mappings().all()

    return render_template(request, "incidencias.html", {
        "username": username,
        "rol": rol,
        "incidencias": incidencias
    })
