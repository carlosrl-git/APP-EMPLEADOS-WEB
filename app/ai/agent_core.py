from app.ai.schemas import AgentIntent

def detect_intent(question: str) -> AgentIntent:
    q = question.lower().strip()

    if 'empleado' in q or 'trabajador' in q:
        return AgentIntent(intent='query_employees', table='trabajadores', filters=[], metric=None, raw_question=question)

    if 'incidencia' in q or 'problema' in q or 'error' in q:
        return AgentIntent(intent='query_incidents', table='incidencias', filters=[], metric=None, raw_question=question)

    if 'tarea' in q or 'pendiente' in q:
        return AgentIntent(intent='query_tasks', table='tareas', filters=[], metric=None, raw_question=question)

    if 'hora' in q or 'horas' in q or 'jornada' in q:
        return AgentIntent(intent='query_hours', table='horas_trabajadas', filters=[], metric='sum', raw_question=question)

    if 'departamento' in q:
        return AgentIntent(intent='query_departments', table='departamentos', filters=[], metric=None, raw_question=question)

    if 'resumen' in q or 'estado general' in q or 'situacion general' in q:
        return AgentIntent(intent='summary', table=None, filters=[], metric=None, raw_question=question)

    return AgentIntent(intent='unknown', table=None, filters=[], metric=None, raw_question=question)
