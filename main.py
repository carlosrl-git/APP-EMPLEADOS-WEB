from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request

templates = Jinja2Templates(directory="app/templates")

@app.get("/departamentos", response_class=HTMLResponse)
def ver_departamentos(request: Request):
    with engine.connect() as conn:
        departamentos = conn.execute(text("""
            SELECT id, nombre
            FROM departamentos
            WHERE activo = true
            ORDER BY nombre ASC
        """)).mappings().all()

    return templates.TemplateResponse("departamentos.html", {
        "request": request,
        "departamentos": departamentos
    })