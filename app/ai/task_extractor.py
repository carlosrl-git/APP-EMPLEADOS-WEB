def extract_task_data(text: str):
    t = text.lower()

    data = {
        "trabajador_id": None,
        "titulo": None,
        "descripcion": None,
        "prioridad": "media",
        "estado": "pendiente",
        "fecha_asignacion": None,
        "fecha_vencimiento": None
    }

    words = t.split()

    for i, w in enumerate(words):
        if w == "trabajador" and i + 1 < len(words):
            try:
                data["trabajador_id"] = int(words[i + 1])
            except:
                pass

        if w == "titulo" and i + 1 < len(words):
            data["titulo"] = words[i + 1]

        if w == "prioridad" and i + 1 < len(words):
            data["prioridad"] = words[i + 1]

        if w == "estado" and i + 1 < len(words):
            data["estado"] = words[i + 1]

        if w == "asignacion" and i + 1 < len(words):
            data["fecha_asignacion"] = words[i + 1]

        if w == "vencimiento" and i + 1 < len(words):
            data["fecha_vencimiento"] = words[i + 1]

    if "descripcion" in t:
        data["descripcion"] = t.split("descripcion", 1)[1].split(" prioridad")[0].split(" estado")[0].split(" asignacion")[0].split(" vencimiento")[0].strip()

    return data
