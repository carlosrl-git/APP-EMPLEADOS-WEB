def analyze_question(question: str) -> dict:
    q = question.lower().strip()

    result = {
        'module': None,
        'action': None,
        'status': None,
        'ranking': None,
        'time': None,
        'raw_question': question
    }

    # Detectar modulo
    if 'empleado' in q or 'empleados' in q or 'trabajador' in q or 'trabajadores' in q:
        result['module'] = 'employees'
    elif 'usuario' in q or 'usuarios' in q:
        result['module'] = 'users'
    elif 'tarea' in q or 'tareas' in q:
        result['module'] = 'tasks'
    elif 'incidencia' in q or 'incidencias' in q:
        result['module'] = 'incidents'
    elif 'hora' in q or 'horas' in q:
        result['module'] = 'hours'
    elif 'departamento' in q or 'departamentos' in q:
        result['module'] = 'departments'

    # Detectar accion
    if 'crear' in q or 'crea' in q or 'agregar' in q or 'anadir' in q:
        result['action'] = 'create'
    elif 'cuanto' in q or 'cuantos' in q or 'total' in q or 'hay' in q:
        result['action'] = 'count'
    elif 'lista' in q or 'dime' in q or 'muestrame' in q or 'ver' in q:
        result['action'] = 'list'
    elif 'resumen' in q:
        result['action'] = 'summary'

    # Estado
    if 'pendiente' in q:
        result['status'] = 'pending'
    elif 'abierta' in q:
        result['status'] = 'open'
    elif 'completada' in q:
        result['status'] = 'completed'

    # Ranking
    if 'mas' in q or 'top' in q:
        result['ranking'] = 'top'
    elif 'menos' in q:
        result['ranking'] = 'bottom'

    # Tiempo
    if 'hoy' in q:
        result['time'] = 'today'
    elif 'esta semana' in q:
        result['time'] = 'week'
    elif 'este mes' in q:
        result['time'] = 'month'

    return result
