from pathlib import Path
import re

base = Path(r"C:\APP-EMPLEADOS-WEB\app")
main = base / "main.py"
templates = base / "templates"

s = main.read_text(encoding="utf-8")
backup = base / "main_backup_ficha_rutas.py"
backup.write_text(s, encoding="utf-8")

pat = r'@app\.get\("/trabajadores/\{id\}", response_class=HTMLResponse\)\s*def ficha_trabajador\(request: Request, id: int\):.*?(?=\n@app\.|\Z)'

nuevo_bloque = '''@app.get("/trabajadores/{id}", response_class=HTMLResponse)
def ficha_trabajador(request: Request, id: int):
    username, rol, response = require_login(request)
    if response:
        return response

    with engine.begin() as conn:
        t = conn.execute(text("""
            SELECT t.*, d.nombre AS departamento
            FROM trabajadores t
            LEFT JOIN departamentos d ON d.id = t.departamento_id
            WHERE t.id = :id
        """), {"id": id}).mappings().first()

        if not t:
            return RedirectResponse(url="/trabajadores", status_code=303)

        ausencias = conn.execute(text("""
            SELECT id, tipo, fecha_inicio, fecha_fin, motivo, estado
            FROM ausencias
            WHERE trabajador_id = :id
            ORDER BY fecha_inicio DESC
        """), {"id": id}).mappings().all()

        horas = conn.execute(text("""
            SELECT id, fecha, horas, horas_extra, tipo
            FROM horas_trabajadas
            WHERE trabajador_id = :id
            ORDER BY fecha DESC
        """), {"id": id}).mappings().all()

        incidencias = conn.execute(text("""
            SELECT id, descripcion, estado, fecha
            FROM incidencias
            WHERE trabajador_id = :id
            ORDER BY fecha DESC
        """), {"id": id}).mappings().all()

        tareas = conn.execute(text("""
            SELECT id, descripcion, estado, resultado, evaluacion, fecha_asignacion, fecha_realizacion
            FROM tareas_extra
            WHERE trabajador_id = :id
            ORDER BY fecha_asignacion DESC
        """), {"id": id}).mappings().all()

        turnos = conn.execute(text("""
            SELECT tu.id, tu.fecha, tu.turno, tu.hora_inicio, tu.hora_fin, tu.estado, tu.observaciones, z.nombre AS zona
            FROM turnos tu
            LEFT JOIN zonas z ON tu.zona_id = z.id
            WHERE tu.trabajador_id = :id
            ORDER BY tu.fecha DESC, tu.hora_inicio DESC
        """), {"id": id}).mappings().all()

        rutas = conn.execute(text("""
            SELECT r.id, r.fecha, r.hora_inicio_jornada, r.hora_fin_jornada, r.total_horas, r.observaciones_generales
            FROM rutas r
            WHERE r.trabajador_id = :id
            ORDER BY r.fecha DESC, r.hora_inicio_jornada ASC
        """), {"id": id}).mappings().all()

    return render_template(request, "trabajador_ficha.html", {
        "username": username,
        "rol": rol,
        "t": t,
        "ausencias": ausencias,
        "horas": horas,
        "incidencias": incidencias,
        "tareas": tareas,
        "turnos": turnos,
        "rutas": rutas,
        "active_page": "trabajadores"
    })
'''

s, n = re.subn(pat, nuevo_bloque, s, flags=re.S)
if n == 0:
    raise SystemExit("NO SE ENCONTRO LA FUNCION ficha_trabajador EN main.py")

if '@app.get("/rutas", response_class=HTMLResponse)' not in s:
    s += '''

@app.get("/rutas", response_class=HTMLResponse)
def ver_rutas(request: Request):
    username, rol, response = require_login(request)
    if response:
        return response

    with engine.begin() as conn:
        rutas = conn.execute(text("""
            SELECT r.id, r.trabajador_id, t.nombre AS trabajador_nombre, t.apellidos AS trabajador_apellidos,
                   r.fecha, r.hora_inicio_jornada, r.hora_fin_jornada, r.total_horas, r.observaciones_generales
            FROM rutas r
            INNER JOIN trabajadores t ON r.trabajador_id = t.id
            ORDER BY r.fecha DESC, r.hora_inicio_jornada ASC
        """)).mappings().all()

        trabajadores = conn.execute(text("""
            SELECT id, nombre, apellidos
            FROM trabajadores
            ORDER BY nombre, apellidos
        """)).mappings().all()

    return render_template(request, "rutas.html", {
        "username": username,
        "rol": rol,
        "rutas": rutas,
        "trabajadores": trabajadores,
        "active_page": "rutas"
    })

@app.post("/rutas/nueva")
def crear_ruta_web(request: Request, trabajador_id: str = Form(...), fecha: str = Form(...), inicio_jornada: str = Form(...), fin_jornada: str = Form(...), total_horas: str = Form("8.00"), observaciones: str = Form("")):
    username, rol, response = require_admin(request)
    if response:
        return response

    try:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO rutas (
                    trabajador_id,
                    fecha,
                    hora_inicio_jornada,
                    hora_fin_jornada,
                    total_horas,
                    observaciones_generales
                ) VALUES (
                    :trabajador_id,
                    :fecha,
                    :inicio,
                    :fin,
                    :total_horas,
                    :observaciones
                )
            """), {
                "trabajador_id": int(trabajador_id),
                "fecha": fecha,
                "inicio": inicio_jornada,
                "fin": fin_jornada,
                "total_horas": float(total_horas),
                "observaciones": observaciones.strip() or None
            })
        return RedirectResponse(url="/rutas", status_code=303)
    except Exception as e:
        print(f"[RUTAS NUEVA ERROR] {e}")
        return RedirectResponse(url="/rutas", status_code=303)

@app.get("/rutas/{id}", response_class=HTMLResponse)
def detalle_ruta(request: Request, id: int):
    username, rol, response = require_login(request)
    if response:
        return response

    with engine.begin() as conn:
        ruta = conn.execute(text("""
            SELECT r.id, r.trabajador_id, t.nombre AS trabajador_nombre, t.apellidos AS trabajador_apellidos,
                   r.fecha, r.hora_inicio_jornada, r.hora_fin_jornada, r.total_horas, r.observaciones_generales
            FROM rutas r
            INNER JOIN trabajadores t ON r.trabajador_id = t.id
            WHERE r.id = :id
        """), {"id": id}).mappings().first()

        if not ruta:
            return RedirectResponse(url="/rutas", status_code=303)

        lineas = conn.execute(text("""
            SELECT id, ruta_id, zona, hora_inicio, hora_fin, duracion_minutos, estado, observaciones
            FROM rutas_detalle
            WHERE ruta_id = :id
            ORDER BY hora_inicio ASC
        """), {"id": id}).mappings().all()

    return render_template(request, "ruta_detalle.html", {
        "username": username,
        "rol": rol,
        "ruta": ruta,
        "lineas": lineas,
        "active_page": "rutas"
    })

@app.post("/rutas/{id}/lineas/nueva")
def crear_ruta_linea_web(request: Request, id: int, hora_inicio: str = Form(...), hora_fin: str = Form(...), tarea: str = Form(...)):
    username, rol, response = require_admin(request)
    if response:
        return response

    try:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO rutas_detalle (
                    ruta_id,
                    zona,
                    hora_inicio,
                    hora_fin,
                    duracion_minutos,
                    estado,
                    observaciones
                ) VALUES (
                    :ruta_id,
                    :zona,
                    :hora_inicio,
                    :hora_fin,
                    0,
                    'pendiente',
                    NULL
                )
            """), {
                "ruta_id": id,
                "zona": tarea.strip(),
                "hora_inicio": hora_inicio,
                "hora_fin": hora_fin
            })
        return RedirectResponse(url=f"/rutas/{id}", status_code=303)
    except Exception as e:
        print(f"[RUTAS LINEA ERROR] {e}")
        return RedirectResponse(url=f"/rutas/{id}", status_code=303)

@app.get("/rutas/{id}/lineas/eliminar/{linea_id}")
def eliminar_ruta_linea_web(request: Request, id: int, linea_id: int):
    username, rol, response = require_admin(request)
    if response:
        return response

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM rutas_detalle WHERE id = :id"), {"id": linea_id})

    return RedirectResponse(url=f"/rutas/{id}", status_code=303)

@app.get("/rutas/eliminar/{id}")
def eliminar_ruta_web(request: Request, id: int):
    username, rol, response = require_admin(request)
    if response:
        return response

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM rutas WHERE id = :id"), {"id": id})

    return RedirectResponse(url="/rutas", status_code=303)
'''

main.write_text(s, encoding="utf-8")

templates.joinpath("trabajador_ficha.html").write_text("""{% extends 'base.html' %}
{% block title %}Ficha trabajador | App Empleados{% endblock %}
{% block content %}
<div class="top-actions">
  <div>
    <h1 class="page-title">{{ t.nombre }} {{ t.apellidos or '' }}</h1>
    <p class="page-subtitle">{{ t.departamento or 'Sin departamento' }}</p>
  </div>
  <div style="display:flex; gap:12px; flex-wrap:wrap;">
    <a href="/trabajadores" class="btn-inline secondary">Volver</a>
  </div>
</div>

<div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:20px;">
  <div class="card" style="padding:22px;">
    <h2 style="margin:0 0 14px 0;">Datos personales</h2>
    <p><strong>ID:</strong> {{ t.id }}</p>
    <p><strong>Nombre:</strong> {{ t.nombre or '-' }} {{ t.apellidos or '' }}</p>
    <p><strong>DNI:</strong> {{ t.dni or '-' }}</p>
    <p><strong>Email:</strong> {{ t.email or '-' }}</p>
    <p><strong>Departamento:</strong> {{ t.departamento or '-' }}</p>
  </div>

  <div class="card" style="padding:22px;">
    <h2 style="margin:0 0 14px 0;">Ausencias</h2>
    {% if ausencias %}
      <div style="display:flex; flex-direction:column; gap:10px;">
        {% for a in ausencias %}
        <div style="padding:12px 14px; background:#161616; border:1px solid #2a2a2a; border-radius:12px;">
          <div style="font-weight:700; margin-bottom:6px;">{{ a.tipo or '-' }}</div>
          <div class="muted">{{ a.fecha_inicio }} → {{ a.fecha_fin }} · Estado: {{ a.estado or '-' }}</div>
          <div>{{ a.motivo or '' }}</div>
        </div>
        {% endfor %}
      </div>
    {% else %}
      <p class="muted">No hay ausencias registradas.</p>
    {% endif %}
  </div>

  <div class="card" style="padding:22px;">
    <h2 style="margin:0 0 14px 0;">Horas</h2>
    {% if horas %}
      <div style="display:flex; flex-direction:column; gap:10px;">
        {% for h in horas %}
        <div style="padding:12px 14px; background:#161616; border:1px solid #2a2a2a; border-radius:12px;">
          <div style="font-weight:700; margin-bottom:6px;">{{ h.fecha }}</div>
          <div class="muted">Horas: {{ h.horas or 0 }} · Extra: {{ h.horas_extra or 0 }} · Tipo: {{ h.tipo or '-' }}</div>
        </div>
        {% endfor %}
      </div>
    {% else %}
      <p class="muted">No hay horas registradas.</p>
    {% endif %}
  </div>

  <div class="card" style="padding:22px;">
    <h2 style="margin:0 0 14px 0;">Incidencias</h2>
    {% if incidencias %}
      <div style="display:flex; flex-direction:column; gap:10px;">
        {% for i in incidencias %}
        <div style="padding:12px 14px; background:#161616; border:1px solid #2a2a2a; border-radius:12px;">
          <div style="font-weight:700; margin-bottom:6px;">{{ i.descripcion }}</div>
          <div class="muted">Estado: {{ i.estado }} · Fecha: {{ i.fecha }}</div>
        </div>
        {% endfor %}
      </div>
    {% else %}
      <p class="muted">No hay incidencias registradas.</p>
    {% endif %}
  </div>
</div>

<div class="card" style="padding:22px; margin-top:20px;">
  <h2 style="margin:0 0 14px 0;">Tareas</h2>
  {% if tareas %}
    <div style="overflow-x:auto;">
      <table style="width:100%; border-collapse:collapse; min-width:1000px;">
        <thead>
          <tr style="background:#161616;">
            <th style="text-align:left; padding:14px; border-bottom:1px solid #2f2f2f;">Descripción</th>
            <th style="text-align:left; padding:14px; border-bottom:1px solid #2f2f2f;">Estado</th>
            <th style="text-align:left; padding:14px; border-bottom:1px solid #2f2f2f;">Resultado</th>
            <th style="text-align:left; padding:14px; border-bottom:1px solid #2f2f2f;">Evaluación</th>
            <th style="text-align:left; padding:14px; border-bottom:1px solid #2f2f2f;">Asignación</th>
          </tr>
        </thead>
        <tbody>
          {% for tarea in tareas %}
          <tr>
            <td style="padding:14px; border-bottom:1px solid #242424;">{{ tarea.descripcion or '-' }}</td>
            <td style="padding:14px; border-bottom:1px solid #242424;">{{ tarea.estado or '-' }}</td>
            <td style="padding:14px; border-bottom:1px solid #242424;">{{ tarea.resultado or '-' }}</td>
            <td style="padding:14px; border-bottom:1px solid #242424;">{{ tarea.evaluacion or '-' }}</td>
            <td style="padding:14px; border-bottom:1px solid #242424;">{{ tarea.fecha_asignacion or '-' }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  {% else %}
    <p class="muted">No hay tareas registradas.</p>
  {% endif %}
</div>

<div class="card" style="padding:22px; margin-top:20px;">
  <h2 style="margin:0 0 14px 0;">Turnos</h2>
  {% if turnos %}
    <div style="overflow-x:auto;">
      <table style="width:100%; border-collapse:collapse; min-width:1000px;">
        <thead>
          <tr style="background:#161616;">
            <th style="text-align:left; padding:14px; border-bottom:1px solid #2f2f2f;">Fecha</th>
            <th style="text-align:left; padding:14px; border-bottom:1px solid #2f2f2f;">Turno</th>
            <th style="text-align:left; padding:14px; border-bottom:1px solid #2f2f2f;">Inicio</th>
            <th style="text-align:left; padding:14px; border-bottom:1px solid #2f2f2f;">Fin</th>
            <th style="text-align:left; padding:14px; border-bottom:1px solid #2f2f2f;">Zona</th>
            <th style="text-align:left; padding:14px; border-bottom:1px solid #2f2f2f;">Estado</th>
          </tr>
        </thead>
        <tbody>
          {% for tu in turnos %}
          <tr>
            <td style="padding:14px; border-bottom:1px solid #242424;">{{ tu.fecha }}</td>
            <td style="padding:14px; border-bottom:1px solid #242424;">{{ tu.turno or '-' }}</td>
            <td style="padding:14px; border-bottom:1px solid #242424;">{{ tu.hora_inicio or '-' }}</td>
            <td style="padding:14px; border-bottom:1px solid #242424;">{{ tu.hora_fin or '-' }}</td>
            <td style="padding:14px; border-bottom:1px solid #242424;">{{ tu.zona or '-' }}</td>
            <td style="padding:14px; border-bottom:1px solid #242424;">{{ tu.estado or '-' }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  {% else %}
    <p class="muted">No hay turnos registrados.</p>
  {% endif %}
</div>

<div class="card" style="padding:22px; margin-top:20px;">
  <h2 style="margin:0 0 14px 0;">Rutas / Jornadas</h2>
  {% if rutas %}
    <div style="overflow-x:auto;">
      <table style="width:100%; border-collapse:collapse; min-width:1000px;">
        <thead>
          <tr style="background:#161616;">
            <th style="text-align:left; padding:14px; border-bottom:1px solid #2f2f2f;">Fecha</th>
            <th style="text-align:left; padding:14px; border-bottom:1px solid #2f2f2f;">Inicio</th>
            <th style="text-align:left; padding:14px; border-bottom:1px solid #2f2f2f;">Fin</th>
            <th style="text-align:left; padding:14px; border-bottom:1px solid #2f2f2f;">Horas</th>
            <th style="text-align:left; padding:14px; border-bottom:1px solid #2f2f2f;">Observaciones</th>
            <th style="text-align:left; padding:14px; border-bottom:1px solid #2f2f2f;">Acciones</th>
          </tr>
        </thead>
        <tbody>
          {% for r in rutas %}
          <tr>
            <td style="padding:14px; border-bottom:1px solid #242424;">{{ r.fecha }}</td>
            <td style="padding:14px; border-bottom:1px solid #242424;">{{ r.hora_inicio_jornada or '-' }}</td>
            <td style="padding:14px; border-bottom:1px solid #242424;">{{ r.hora_fin_jornada or '-' }}</td>
            <td style="padding:14px; border-bottom:1px solid #242424;">{{ r.total_horas or '-' }}</td>
            <td style="padding:14px; border-bottom:1px solid #242424;">{{ r.observaciones_generales or '-' }}</td>
            <td style="padding:14px; border-bottom:1px solid #242424; white-space:nowrap;">
              <a href="/rutas/{{ r.id }}" class="btn-inline">Abrir jornada</a>
            </td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  {% else %}
    <p class="muted">No hay rutas o jornadas registradas.</p>
  {% endif %}
</div>
{% endblock %}
""", encoding="utf-8")

templates.joinpath("rutas.html").write_text("""{% extends 'base.html' %}
{% block title %}Rutas | App Empleados{% endblock %}
{% block content %}
<div class="top-actions">
  <div>
    <h1 class="page-title">Planificación de Rutas</h1>
    <p class="page-subtitle">Crea jornadas y abre la ficha detallada de cada una.</p>
  </div>
  <div style="display:flex; gap:12px;">
    <a href="/dashboard" class="btn-inline secondary">Volver</a>
  </div>
</div>

<div class="card" style="padding:22px; margin-bottom:22px;">
  <h2 style="margin:0 0 16px 0;">Crear jornada</h2>
  <form method="post" action="/rutas/nueva" style="display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:14px; align-items:end;">
    <div>
      <label style="display:block; margin-bottom:8px;">Empleado</label>
      <select name="trabajador_id" class="input" required>
        <option value="">Selecciona un empleado</option>
        {% for t in trabajadores %}
        <option value="{{ t.id }}">{{ t.id }} - {{ t.nombre }} {{ t.apellidos or '' }}</option>
        {% endfor %}
      </select>
    </div>
    <div>
      <label style="display:block; margin-bottom:8px;">Fecha</label>
      <input type="date" name="fecha" class="input" required>
    </div>
    <div>
      <label style="display:block; margin-bottom:8px;">Inicio jornada</label>
      <input type="time" name="inicio_jornada" class="input" required>
    </div>
    <div>
      <label style="display:block; margin-bottom:8px;">Fin jornada</label>
      <input type="time" name="fin_jornada" class="input" required>
    </div>
    <div>
      <label style="display:block; margin-bottom:8px;">Total horas</label>
      <input type="number" step="0.01" name="total_horas" class="input" value="8.00">
    </div>
    <div style="grid-column:1/-1;">
      <label style="display:block; margin-bottom:8px;">Observaciones</label>
      <input type="text" name="observaciones" class="input" placeholder="Observaciones generales">
    </div>
    <div style="grid-column:1/-1;">
      <button type="submit" class="btn" style="width:auto; min-width:180px;">Crear jornada</button>
    </div>
  </form>
</div>

<div class="card" style="padding:22px;">
  <h2 style="margin:0 0 16px 0;">Jornadas creadas</h2>
  <div style="overflow-x:auto;">
    <table style="width:100%; border-collapse:collapse; min-width:1100px;">
      <thead>
        <tr style="background:#161616;">
          <th style="text-align:left; padding:14px; border-bottom:1px solid #2f2f2f;">ID</th>
          <th style="text-align:left; padding:14px; border-bottom:1px solid #2f2f2f;">Empleado</th>
          <th style="text-align:left; padding:14px; border-bottom:1px solid #2f2f2f;">Fecha</th>
          <th style="text-align:left; padding:14px; border-bottom:1px solid #2f2f2f;">Inicio</th>
          <th style="text-align:left; padding:14px; border-bottom:1px solid #2f2f2f;">Fin</th>
          <th style="text-align:left; padding:14px; border-bottom:1px solid #2f2f2f;">Horas</th>
          <th style="text-align:left; padding:14px; border-bottom:1px solid #2f2f2f;">Acciones</th>
        </tr>
      </thead>
      <tbody>
        {% for r in rutas %}
        <tr>
          <td style="padding:14px; border-bottom:1px solid #242424;">{{ r.id }}</td>
          <td style="padding:14px; border-bottom:1px solid #242424;">{{ r.trabajador_nombre or '-' }} {{ r.trabajador_apellidos or '' }}</td>
          <td style="padding:14px; border-bottom:1px solid #242424;">{{ r.fecha }}</td>
          <td style="padding:14px; border-bottom:1px solid #242424;">{{ r.hora_inicio_jornada or '-' }}</td>
          <td style="padding:14px; border-bottom:1px solid #242424;">{{ r.hora_fin_jornada or '-' }}</td>
          <td style="padding:14px; border-bottom:1px solid #242424;">{{ r.total_horas or '-' }}</td>
          <td style="padding:14px; border-bottom:1px solid #242424; white-space:nowrap;">
            <a href="/rutas/{{ r.id }}" class="btn-inline">Abrir jornada</a>
            {% if rol == 'admin' %}
            <a href="/rutas/eliminar/{{ r.id }}" class="btn-inline secondary">Eliminar</a>
            {% endif %}
          </td>
        </tr>
        {% endfor %}
        {% if not rutas %}
        <tr>
          <td colspan="7" style="padding:18px; border-bottom:1px solid #242424;">No hay jornadas creadas.</td>
        </tr>
        {% endif %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
""", encoding="utf-8")

templates.joinpath("ruta_detalle.html").write_text("""{% extends 'base.html' %}
{% block title %}Ficha de la jornada abierta | App Empleados{% endblock %}
{% block content %}
<div class="card" style="padding:22px;">
  <h1 class="page-title" style="font-size:30px; margin-bottom:8px;">Ficha de la jornada abierta</h1>
  <p style="color:#ff4d4f; font-weight:800; margin:0 0 26px 0;">
    Jornada abierta: {{ ruta.trabajador_nombre or '-' }} {{ ruta.trabajador_apellidos or '' }} | {{ ruta.fecha }} | {{ ruta.hora_inicio_jornada or '-' }} - {{ ruta.hora_fin_jornada or '-' }}
  </p>

  <form method="post" action="/rutas/{{ ruta.id }}/lineas/nueva" style="display:grid; grid-template-columns:180px 180px 1fr; gap:18px; align-items:end; margin-bottom:24px;">
    <div>
      <label style="display:block; margin-bottom:8px;">Hora inicio</label>
      <input type="time" name="hora_inicio" class="input" required>
    </div>
    <div>
      <label style="display:block; margin-bottom:8px;">Hora fin</label>
      <input type="time" name="hora_fin" class="input" required>
    </div>
    <div style="grid-column:1 / span 2;">
      <label style="display:block; margin-bottom:8px;">Tarea</label>
      <input type="text" name="tarea" class="input" required placeholder="Escribe la tarea">
    </div>
    <div style="grid-column:1 / -1; display:flex; gap:12px; margin-top:6px;">
      <button type="submit" class="btn" style="width:auto; min-width:150px;">Añadir línea</button>
      <a href="/rutas" class="btn-inline secondary">Volver a jornadas</a>
    </div>
  </form>

  <div style="overflow-x:auto;">
    <table style="width:100%; border-collapse:collapse; min-width:1050px;">
      <thead>
        <tr style="background:#161616;">
          <th style="text-align:left; padding:14px; border-bottom:1px solid #2f2f2f;">ID</th>
          <th style="text-align:left; padding:14px; border-bottom:1px solid #2f2f2f;">Hora inicio</th>
          <th style="text-align:left; padding:14px; border-bottom:1px solid #2f2f2f;">Hora fin</th>
          <th style="text-align:left; padding:14px; border-bottom:1px solid #2f2f2f;">Duración</th>
          <th style="text-align:left; padding:14px; border-bottom:1px solid #2f2f2f;">Tarea</th>
          <th style="text-align:left; padding:14px; border-bottom:1px solid #2f2f2f;">Acciones</th>
        </tr>
      </thead>
      <tbody>
        {% for l in lineas %}
        <tr>
          <td style="padding:14px; border-bottom:1px solid #242424;">{{ l.id }}</td>
          <td style="padding:14px; border-bottom:1px solid #242424;">{{ l.hora_inicio or '-' }}</td>
          <td style="padding:14px; border-bottom:1px solid #242424;">{{ l.hora_fin or '-' }}</td>
          <td style="padding:14px; border-bottom:1px solid #242424;">{{ l.duracion_minutos or 0 }} min</td>
          <td style="padding:14px; border-bottom:1px solid #242424;">{{ l.zona or '-' }}</td>
          <td style="padding:14px; border-bottom:1px solid #242424; white-space:nowrap;">
            {% if rol == 'admin' %}
            <a href="/rutas/{{ ruta.id }}/lineas/eliminar/{{ l.id }}" class="btn-inline secondary">Eliminar línea</a>
            {% endif %}
          </td>
        </tr>
        {% endfor %}
        {% if not lineas %}
        <tr>
          <td colspan="6" style="padding:18px; border-bottom:1px solid #242424;">No hay líneas añadidas todavía en esta jornada.</td>
        </tr>
        {% endif %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
""", encoding="utf-8")

print("OK PATCH APLICADO")
