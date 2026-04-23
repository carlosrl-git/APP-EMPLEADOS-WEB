from fastapi import Request, HTTPException, status

SESSION_USER_ID = "user_id"
SESSION_USERNAME = "username"
SESSION_ROL = "rol"
SESSION_NIVEL = "nivel"
SESSION_EMPRESA_ID = "empresa_id"


def set_session(
    request: Request,
    user_id: int,
    username: str,
    rol: str,
    nivel: int,
    empresa_id: int,
):
    request.session[SESSION_USER_ID] = user_id
    request.session[SESSION_USERNAME] = username
    request.session[SESSION_ROL] = rol
    request.session[SESSION_NIVEL] = nivel
    request.session[SESSION_EMPRESA_ID] = empresa_id


def clear_session(request: Request):
    request.session.clear()


def require_login(request: Request):
    if SESSION_USER_ID not in request.session:
        raise HTTPException(status_code=401, detail="No autenticado")


def get_empresa_id(request: Request) -> int:
    empresa_id = request.session.get(SESSION_EMPRESA_ID)
    if empresa_id is None:
        raise HTTPException(status_code=401, detail="Empresa no encontrada en sesión")
    return int(empresa_id)


def get_user_id(request: Request) -> int:
    user_id = request.session.get(SESSION_USER_ID)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Usuario no autenticado")
    return int(user_id)


def get_user_level(request: Request) -> int:
    nivel = request.session.get(SESSION_NIVEL)
    if nivel is None:
        raise HTTPException(status_code=401, detail="Nivel no encontrado")
    return int(nivel)


def require_admin(request: Request, min_level: int = 100):
    require_login(request)
    nivel = get_user_level(request)
    if nivel < min_level:
        raise HTTPException(status_code=403, detail="No autorizado")