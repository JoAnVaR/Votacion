import sqlite3

def mostrar_tablas_y_contenido(db_path):
    # Conectar a la base de datos
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Obtener las tablas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tablas = cursor.fetchall()

    for tabla in tablas:
        nombre_tabla = tabla[0]
        print(f"Tabla: {nombre_tabla}")

        # Obtener el contenido de la tabla
        cursor.execute(f"SELECT * FROM {nombre_tabla};")
        filas = cursor.fetchall()

        for fila in filas:
            print(fila)

        print("\n")

    # Cerrar la conexión
    conn.close()

if __name__ == "__main__":
    mostrar_tablas_y_contenido('c:/Users/JordyA/Documents/phyton/Votacion/instance/votacion.db')
