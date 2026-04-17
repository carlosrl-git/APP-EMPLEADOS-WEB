def extract_absence_data(text: str):
    t = text.lower()

    data = {
        "trabajador_id": None,
        "tipo": None,
        "fecha_inicio": None,
        "fecha_fin": None,
        "motivo": None,
        "estado": "pendiente"
    }

    words = t.split()

    for i, w in enumerate(words):
        if w == "trabajador" and i + 1 < len(words):
            try:
                data["trabajador_id"] = int(words[i + 1])
            except:
                pass

        if w == "tipo" and i + 1 < len(words):
            data["tipo"] = words[i + 1]

        if w in ["desde"] and i + 1 < len(words):
            data["fecha_inicio"] = words[i + 1]

        if w in ["hasta"] and i + 1 < len(words):
            data["fecha_fin"] = words[i + 1]

    if "motivo" in t:
        data["motivo"] = t.split("motivo",1)[1].strip()

    return data
