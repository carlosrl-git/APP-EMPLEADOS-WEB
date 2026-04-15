from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

sql = """

CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE,
    email TEXT,
    password_hash TEXT,
    rol TEXT,
    activo BOOLEAN DEFAULT true,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

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

CREATE TABLE IF NOT EXISTS departamentos (
    id SERIAL PRIMARY KEY,
    nombre TEXT,
    activo BOOLEAN DEFAULT true
);

CREATE TABLE IF NOT EXISTS incidencias (
    id SERIAL PRIMARY KEY,
    descripcion TEXT,
    trabajador_id INTEGER,
    estado TEXT,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

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

CREATE TABLE IF NOT EXISTS turnos (
    id SERIAL PRIMARY KEY,
    trabajador_id INTEGER,
    fecha DATE,
    inicio_jornada TIME,
    fin_jornada TIME,
    total_horas FLOAT,
    observaciones TEXT
);

CREATE TABLE IF NOT EXISTS password_resets (
    id SERIAL PRIMARY KEY,
    email TEXT,
    code TEXT,
    expires_at TIMESTAMP,
    used BOOLEAN DEFAULT false
);

CREATE TABLE IF NOT EXISTS login_attempts (
    username TEXT PRIMARY KEY,
    attempts INTEGER,
    last_attempt TIMESTAMP
);

"""

with engine.begin() as conn:
    conn.execute(text(sql))

print("BASE DE DATOS CREADA CORRECTAMENTE")