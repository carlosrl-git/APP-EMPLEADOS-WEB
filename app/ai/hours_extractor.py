def extract_hours_data(text: str):
    t = text.lower()

    data = {
        "trabajador_id": None,
        "fecha": None,
        "horas": None,
        "horas_extra": 0,
        "tipo": "normal"
    }

    words = t.split()

    for i, w in enumerate(words):
        if w == "trabajador" and i + 1 < len(words):
            try:
                data["trabajador_id"] = int(words[i + 1])
            except:
                pass

        if w == "fecha" and i + 1 < len(words):
            data["fecha"] = words[i + 1]

        if w == "horas" and i + 1 < len(words):
            try:
                data["horas"] = float(words[i + 1])
            except:
                pass

        if w == "extra" and i + 1 < len(words):
            try:
                data["horas_extra"] = float(words[i + 1])
            except:
                pass

        if w == "tipo" and i + 1 < len(words):
            data["tipo"] = words[i + 1]

    return data
