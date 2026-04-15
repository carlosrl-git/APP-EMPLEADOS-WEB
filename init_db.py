from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

sql = """
-- =========================
-- USUARIOS
-- =========================
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS username TEXT;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS email TEXT;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS password_hash TEXT;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS rol TEXT;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS activo BOOLEAN DEFAULT true;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP;



-- =========================
-- DEPARTAMENTOS
-- =========================
CREATE TABLE IF NOT EXISTS departamentos (
    id SERIAL PRIMARY KEY,
    nombre TEXT,
    activo BOOLEAN DEFAULT true
);

-- =========================
-- TRABAJADORES
-- =========================
CREATE TABLE IF NOT EXISTS trabajadores (
    id SERIAL PRIMARY KEY,
    nombre TEXT,
    apellidos TEXT,
    email TEXT,
    telefono TEXT,
    puesto TEXT,
    departamento_id INTEGER,
    activo BOOLEAN DEFAULT true
);

-- =========================
-- INCIDENCIAS
-- =========================
CREATE TABLE IF NOT EXISTS incidencias (
    id SERIAL PRIMARY KEY,
    descripcion TEXT,
    trabajador_id INTEGER,
    estado TEXT,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================
-- TAREAS
-- =========================
CREATE TABLE IF NOT EXISTS tareas (
    id SERIAL PRIMARY KEY,
    trabajador_id INTEGER,
    titulo TEXT,
    descripcion TEXT,
    prioridad TEXT,
    estado TEXT,
    fecha_asignacion DATE,
    fecha_vencimiento DATE
);

-- =========================
-- TAREAS EXTRA
-- =========================
CREATE TABLE IF NOT EXISTS tareas_extra (
    id SERIAL PRIMARY KEY,
    trabajador_id INTEGER,
    descripcion TEXT,
    estado TEXT,
    resultado TEXT,
    evaluacion TEXT,
    fecha_asignacion TIMESTAMP,
    fecha_realizacion TIMESTAMP
);

-- =========================
-- TURNOS
-- =========================
CREATE TABLE IF NOT EXISTS turnos (
    id SERIAL PRIMARY KEY,
    trabajador_id INTEGER,
    fecha DATE,
    turno TEXT,
    hora_inicio TIME,
    hora_fin TIME,
    inicio_jornada TIME,
    fin_jornada TIME,
    total_horas FLOAT,
    estado TEXT,
    observaciones TEXT,
    observaciones_generales TEXT,
    zona_id INTEGER
);

CREATE TABLE IF NOT EXISTS turno_lineas (
    id SERIAL PRIMARY KEY,
    turno_id INTEGER,
    hora_inicio TIME,
    hora_fin TIME,
    tarea TEXT
);

-- =========================
-- RUTAS
-- =========================
CREATE TABLE IF NOT EXISTS rutas (
    id SERIAL PRIMARY KEY,
    trabajador_id INTEGER,
    fecha DATE,
    hora_inicio_jornada TIME,
    hora_fin_jornada TIME,
    total_horas FLOAT,
    observaciones_generales TEXT
);

CREATE TABLE IF NOT EXISTS rutas_detalle (
    id SERIAL PRIMARY KEY,
    ruta_id INTEGER,
    zona TEXT,
    hora_inicio TIME,
    hora_fin TIME,
    duracion_minutos INTEGER DEFAULT 0,
    estado TEXT DEFAULT 'pendiente',
    observaciones TEXT
);

-- =========================
-- HORAS
-- =========================
CREATE TABLE IF NOT EXISTS horas_trabajadas (
    id SERIAL PRIMARY KEY,
    trabajador_id INTEGER,
    fecha DATE,
    horas FLOAT,
    horas_extra FLOAT DEFAULT 0,
    tipo TEXT
);

-- =========================
-- AUSENCIAS
-- =========================
CREATE TABLE IF NOT EXISTS ausencias (
    id SERIAL PRIMARY KEY,
    trabajador_id INTEGER,
    tipo TEXT,
    fecha_inicio DATE,
    fecha_fin DATE,
    motivo TEXT,
    estado TEXT
);

-- =========================
-- PRODUCTOS
-- =========================
CREATE TABLE IF NOT EXISTS productos (
    id SERIAL PRIMARY KEY,
    nombre TEXT,
    categoria TEXT,
    stock INTEGER DEFAULT 0
);

-- =========================
-- ZONAS
-- =========================
CREATE TABLE IF NOT EXISTS zonas (
    id SERIAL PRIMARY KEY,
    nombre TEXT,
    tipo TEXT,
    activo BOOLEAN DEFAULT true
);

-- =========================
-- LOGIN ATTEMPTS
-- =========================
CREATE TABLE IF NOT EXISTS login_attempts (
    username TEXT PRIMARY KEY,
    attempts INTEGER DEFAULT 0,
    last_attempt TIMESTAMP
);

-- =========================
-- PASSWORD RESETS
-- =========================
CREATE TABLE IF NOT EXISTS password_resets (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL,
    code TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN NOT NULL DEFAULT false
);
"""

with engine.begin() as conn:
    for statement in sql.split(";"):
        stmt = statement.strip()
        if stmt:
            conn.execute(text(stmt))

print("BASE REMOTA ACTUALIZADA")