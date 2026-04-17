import re

def extract_incident_data(question: str) -> dict:
    q = question.lower()

    result = {
        "descripcion": None,
        "trabajador_id": None,
        "estado": "abierta"
    }

    desc_match = re.search(r"(?:descripcion|incidencia|problema) ([a-zA-Z0-9 ,.\-_]+?)(?: trabajador| estado|$)", q)
    if desc_match:
        result["descripcion"] = desc_match.group(1).strip()

    trabajador_match = re.search(r"trabajador (\d+)", q)
    if trabajador_match:
        result["trabajador_id"] = int(trabajador_match.group(1))

    estado_match = re.search(r"estado ([a-zA-Z]+)", q)
    if estado_match:
        result["estado"] = estado_match.group(1).strip().lower()

    return result
