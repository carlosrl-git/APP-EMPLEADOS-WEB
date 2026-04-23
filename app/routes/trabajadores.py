from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.core.db import fetch_all, execute
from app.core.security import require_login, get_empresa_id

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# ===============================
# LISTADO
# ===============================
@router.get("/trabajadores", response_class=HTMLResponse)
def listar_trabajadores(request: Request):
    require_login(request)
    empresa_id = get_empresa_id(request)

    trabajadores = fetch_all(
        """
        SELECT id, nombre, apellido, email, telefono
        FROM trabajadores
        WHERE empresa_id = :empresa_id
        ORDER BY id DESC
        """,
        {"empresa_id": empresa_id},
    )

    return templates.TemplateResponse(
        "trabajadores/list.html",
        {
            "request": request,
            "trabajadores": trabajadores,
        },
    )


# ===============================
# FORM CREAR
# ===============================
@router.get("/trabajadores/nuevo", response_class=HTMLResponse)
def form_nuevo_trabajador(request: Request):
    require_login(request)

    return templates.TemplateResponse(
        "trabajadores/form.html",
        {"request": request},
    )


# ===============================
# CREAR
# ===============================
@router.post("/trabajadores/nuevo")
def crear_trabajador(
    request: Request,
    nombre: str = Form(...),
    apellido: str = Form(...),
    email: str = Form(...),
    telefono: str = Form(...),
):
    require_login(request)
    empresa_id = get_empresa_id(request)

    execute(
        """
        INSERT INTO trabajadores (empresa_id, nombre, apellido, email, telefono)
        VALUES (:empresa_id, :nombre, :apellido, :email, :telefono)
        """,
        {
            "empresa_id": empresa_id,
            "nombre": nombre,
            "apellido": apellido,
            "email": email,
            "telefono": telefono,
        },
    )

    return RedirectResponse(url="/trabajadores", status_code=303)