from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import text
from passlib.hash import pbkdf2_sha256

from app.core.db import engine
from app.core.security import require_admin, get_current_empresa_id
from app.core.utils import render_template

router = APIRouter()

@router.get("/usuarios", response_class=HTMLResponse)
def ver_usuarios(request: Request):
    username, rol, response = require_admin(request)
    if response:
        return response

    with engine.begin() as conn:
        usuarios = conn.execute(text("""
            SELECT id, username, email, rol, activo
            FROM usuarios
            WHERE empresa_id = :empresa_id
        """), {"empresa_id": get_current_empresa_id(request)}).mappings().all()

    return render_template(request, "usuarios.html", {
        "usuarios": usuarios,
        "username": username,
        "rol": rol
    })
