from pathlib import Path
import re

p = Path("app/main.py")
txt = p.read_text(encoding="utf-8")

nuevo_bloque = '''@app.get("/incidencias/estado/{id}/{nuevo_estado}")
def cambiar_estado_incidencia(request: Request, id: int, nuevo_estado: str):
    username, rol, response = require_admin(request)
    if response:
        return response

    estados_validos = ["abierta", "en_proceso", "completada"]

    if nuevo_estado not in estados_validos:
        return RedirectResponse(url="/incidencias", status_code=303)

    with engine.begin() as conn:
        conn.execute(
            text("""UPDATE incidencias
                    SET estado = :estado
                    WHERE id = :id AND empresa_id = :empresa_id"""),
            {"estado": nuevo_estado, "id": id, "empresa_id": get_current_empresa_id(request)}
        )

    return RedirectResponse(url="/incidencias", status_code=303)


'''

txt = re.sub(
    r'@app\.get\("/incidencias/estado/\{id\}/\{nuevo_estado\}"\).*?@app\.get\("/tareas", response_class=HTMLResponse\)',
    nuevo_bloque + '@app.get("/tareas", response_class=HTMLResponse)',
    txt,
    count=1,
    flags=re.S
)

p.write_text(txt, encoding="utf-8")
print("OK_REBUILD_CAMBIAR_ESTADO_INCIDENCIA")
