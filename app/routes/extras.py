from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import text

from app.core.db import engine
from app.core.security import require_login
from app.core.utils import render_template

router = APIRouter()

@router.get("/horas", response_class=HTMLResponse)
def ver_horas(request: Request):
    username, rol, response = require_login(request)
    if response:
        return response

    with engine.begin() as conn:
        horas = conn.execute(text("SELECT * FROM horas_trabajadas")).mappings().all()

    return render_template(request, "horas.html", {
        "horas": horas,
        "username": username,
        "rol": rol
    })


@router.get("/ausencias", response_class=HTMLResponse)
def ver_ausencias(request: Request):
    username, rol, response = require_login(request)
    if response:
        return response

    with engine.begin() as conn:
        ausencias = conn.execute(text("SELECT * FROM ausencias")).mappings().all()

    return render_template(request, "ausencias.html", {
        "ausencias": ausencias,
        "username": username,
        "rol": rol
    })


@router.get("/productos", response_class=HTMLResponse)
def ver_productos(request: Request):
    username, rol, response = require_login(request)
    if response:
        return response

    with engine.begin() as conn:
        productos = conn.execute(text("SELECT * FROM productos")).mappings().all()

    return render_template(request, "productos.html", {
        "productos": productos,
        "username": username,
        "rol": rol
    })


@router.get("/zonas", response_class=HTMLResponse)
def ver_zonas(request: Request):
    username, rol, response = require_login(request)
    if response:
        return response

    with engine.begin() as conn:
        zonas = conn.execute(text("SELECT * FROM zonas")).mappings().all()

    return render_template(request, "zonas.html", {
        "zonas": zonas,
        "username": username,
        "rol": rol
    })
