from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import text

from app.core.db import engine
from app.core.security import require_login
from app.core.utils import render_template

router = APIRouter()

@router.get("/rutas", response_class=HTMLResponse)
def ver_rutas(request: Request):
    username, rol, response = require_login(request)
    if response:
        return response

    with engine.begin() as conn:
        rutas = conn.execute(text("""
            SELECT r.id, r.fecha, t.nombre
            FROM rutas r
            LEFT JOIN trabajadores t ON t.id = r.trabajador_id
        """)).mappings().all()

    return render_template(request, "rutas.html", {
        "rutas": rutas,
        "username": username,
        "rol": rol
    })
