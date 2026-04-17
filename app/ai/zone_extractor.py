def extract_zone_data(text: str):
    t = text.lower()

    data = {
        "nombre": None,
        "tipo": None,
        "activo": "true"
    }

    words = t.split()

    for i, w in enumerate(words):
        if w == "zona" and i + 1 < len(words):
            data["nombre"] = words[i + 1]

        if w == "tipo" and i + 1 < len(words):
            data["tipo"] = words[i + 1]

        if w == "activo":
            data["activo"] = "true"
        if w == "inactivo":
            data["activo"] = "false"

    return data
