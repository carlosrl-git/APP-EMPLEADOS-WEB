from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import text

from app.core.db import engine
from app.core.security import require_login
from app.core.utils import render_template

router = APIRouter()

@router.get("/turnos", response_class=HTMLResponse)
def ver_turnos(request: Request):
    username, rol, response = require_login(request)
    if response:
        return response

    with engine.begin() as conn:
        turnos = conn.execute(text("""
            SELECT tu.id, tu.fecha, tr.nombre
            FROM turnos tu
            LEFT JOIN trabajadores tr ON tr.id = tu.trabajador_id
        """)).mappings().all()

    return render_template(request, "turnos.html", {
        "turnos": turnos,
        "username": username,
        "rol": rol
    })
