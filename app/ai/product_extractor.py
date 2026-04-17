def extract_product_data(text: str):
    t = text.lower()

    data = {
        "nombre": None,
        "categoria": None,
        "stock": 0
    }

    words = t.split()

    for i, w in enumerate(words):
        if w == "producto" and i + 1 < len(words):
            data["nombre"] = words[i + 1]

        if w == "categoria" and i + 1 < len(words):
            data["categoria"] = words[i + 1]

        if w == "stock" and i + 1 < len(words):
            try:
                data["stock"] = int(words[i + 1])
            except:
                pass

    return data
