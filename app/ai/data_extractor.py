import re

def extract_user_data(question: str) -> dict:
    q = question.lower()
    result = {"name": None, "role": None, "email": None, "password": None, "generate_password": False}

    name_match = re.search(r"llamado ([a-zA-Z ]+?)(?: con rol| con email| con correo| con password| con clave| y genera| genera clave|$)", q)
    if name_match:
        result["name"] = name_match.group(1).strip().title()

    role_match = re.search(r"rol ([a-zA-Z]+)", q)
    if role_match:
        result["role"] = role_match.group(1).strip().lower()

    email_match = re.search(r"(?:email|correo) ([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", q)
    if email_match:
        result["email"] = email_match.group(1).strip().lower()

    password_match = re.search(r"(?:password|clave) ([^\s]+)", question, re.IGNORECASE)
    if password_match:
        result["password"] = password_match.group(1).strip()

    if "genera una clave" in q or "generar clave" in q or "genera clave" in q:
        result["generate_password"] = True

    return result
