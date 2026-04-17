from sqlalchemy import text
from app.core.database import engine

def create_product(nombre, categoria, stock):
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO productos (nombre, categoria, stock)
                VALUES (:nombre, :categoria, :stock)
            """), {
                "nombre": nombre.strip(),
                "categoria": categoria.strip() if categoria else None,
                "stock": int(stock or 0)
            })
        return True, "Producto creado correctamente."
    except Exception as e:
        return False, f"Error al crear producto: {e}"
