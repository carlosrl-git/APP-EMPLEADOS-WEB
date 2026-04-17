def extract_shift_data(text: str):
    t = text.lower()

    data = {
        "trabajador_id": None,
        "fecha": None,
        "inicio_jornada": None,
        "fin_jornada": None,
        "total_horas": None,
        "observaciones": None
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

        if w in ["inicio", "empieza"] and i + 1 < len(words):
            data["inicio_jornada"] = words[i + 1]

        if w in ["fin", "termina"] and i + 1 < len(words):
            data["fin_jornada"] = words[i + 1]

        if w == "horas" and i + 1 < len(words):
            try:
                data["total_horas"] = float(words[i + 1])
            except:
                pass

    if "observaciones" in t:
        data["observaciones"] = t.split("observaciones", 1)[1].strip()

    return data
