from pathlib import Path
import re

p = Path("app/main.py")
txt = p.read_text(encoding="utf-8")

nuevo_get = '''@app.get("/trabajadores/editar/{id}", response_class=HTMLResponse)
def editar_trabajador_page(request: Request, id: int):
    username, rol, response = require_admin(request)
    if response:
        return response

    with engine.begin() as conn:
        t = conn.execute(
            text("""SELECT * FROM trabajadores WHERE id = :id AND empresa_id = :empresa_id"""),
            {"id": id, "empresa_id": get_current_empresa_id(request)}
        ).mappings().first()

        if not t:
            return RedirectResponse(url="/trabajadores", status_code=303)

        departamentos = conn.execute(
            text("SELECT id, nombre FROM departamentos WHERE activo = true")
        ).mappings().all()

    return render_template(request, "trabajador_editar.html", {
        "username": username,
        "rol": rol,
        "t": t,
        "departamentos": departamentos,
        "active_page": "trabajadores",
    })


'''

nuevo_post = '''@app.post("/trabajadores/editar/{id}")
def editar_trabajador(
    request: Request,
    id: int,
    nombre: str = Form(...),
    apellidos: str = Form(""),
    email: str = Form(""),
    telefono: str = Form(""),
    puesto: str = Form(""),
    departamento_id: str = Form(""),
):
    username, rol, response = require_admin(request)
    if response:
        return response

    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE trabajadores SET
                nombre = :nombre,
                apellidos = :apellidos,
                email = :email,
                telefono = :telefono,
                puesto = :puesto,
                departamento_id = :departamento_id
            WHERE id = :id AND empresa_id = :empresa_id
        """), {
            "id": id,
            "nombre": nombre.strip(),
            "apellidos": apellidos.strip() or None,
            "email": email.strip() or None,
            "telefono": telefono.strip() or None,
            "puesto": puesto.strip() or None,
            "departamento_id": int(departamento_id) if departamento_id else None,
            "empresa_id": get_current_empresa_id(request),
        })

    return RedirectResponse(url="/trabajadores", status_code=303)


'''

nuevo_delete = '''@app.get("/trabajadores/eliminar/{id}")
def eliminar_trabajador(request: Request, id: int):
    username, rol, response = require_admin(request)
    if response:
        return response

    with engine.begin() as conn:
        conn.execute(
            text("""DELETE FROM trabajadores WHERE id = :id AND empresa_id = :empresa_id"""),
            {"id": id, "empresa_id": get_current_empresa_id(request)}
        )

    return RedirectResponse(url="/trabajadores", status_code=303)


'''

txt = re.sub(
    r'@app\.get\("/trabajadores/editar/\{id\}", response_class=HTMLResponse\).*?@app\.post\("/trabajadores/editar/\{id\}"\)',
    nuevo_get + '@app.post("/trabajadores/editar/{id}")',
    txt,
    count=1,
    flags=re.S
)

txt = re.sub(
    r'@app\.post\("/trabajadores/editar/\{id\}"\).*?@app\.get\("/trabajadores/eliminar/\{id\}"\)',
    nuevo_post + '@app.get("/trabajadores/eliminar/{id}")',
    txt,
    count=1,
    flags=re.S
)

txt = re.sub(
    r'@app\.get\("/trabajadores/eliminar/\{id\}"\).*?@app\.get\("/incidencias", response_class=HTMLResponse\)',
    nuevo_delete + '@app.get("/incidencias", response_class=HTMLResponse)',
    txt,
    count=1,
    flags=re.S
)

p.write_text(txt, encoding="utf-8")
print("OK_REBUILD_TRABAJADORES_EDIT_DELETE")
