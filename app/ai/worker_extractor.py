import re

def extract_worker_data(question: str) -> dict:
    q = question.lower()

    result = {
        "nombre": None,
        "apellidos": None,
        "email": None,
        "telefono": None,
        "puesto": None,
        "departamento_id": None
    }

    nombre_match = re.search(r"llamado ([a-zA-Z]+)", q)
    if nombre_match:
        result["nombre"] = nombre_match.group(1).capitalize()

    apellidos_match = re.search(r"([a-zA-Z]+)\s([a-zA-Z]+)", q)
    if apellidos_match:
        result["apellidos"] = apellidos_match.group(2).capitalize()

    email_match = re.search(r"(?:email|correo) ([\w\.-]+@[\w\.-]+)", q)
    if email_match:
        result["email"] = email_match.group(1)

    telefono_match = re.search(r"(?:telefono|tel) (\d+)", q)
    if telefono_match:
        result["telefono"] = telefono_match.group(1)

    puesto_match = re.search(r"puesto ([a-zA-Z]+)", q)
    if puesto_match:
        result["puesto"] = puesto_match.group(1)

    dep_match = re.search(r"departamento (\d+)", q)
    if dep_match:
        result["departamento_id"] = int(dep_match.group(1))

    return result
