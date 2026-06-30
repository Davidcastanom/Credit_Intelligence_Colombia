import sqlite3

conexion = sqlite3.connect("database/tasas.db")
cursor = conexion.cursor()

print("--- ESTRUCTURA DE LA BASE DE DATOS (TABLAS Y COLUMNAS) ---")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
tablas = cursor.fetchall()

for tabla_tupla in tablas:
    tabla = tabla_tupla[0]
    print(f"\nTabla: {tabla.upper()}")
    cursor.execute(f"PRAGMA table_info({tabla});")
    columnas = cursor.fetchall()
    for col in columnas:
        # col[1] es el nombre de la columna, col[2] es el tipo de datos, col[3] si es NOT NULL, col[5] si es PK
        pk_desc = " [PK]" if col[5] else ""
        nn_desc = " [NOT NULL]" if col[3] else ""
        print(f"  - {col[1]} ({col[2]}){pk_desc}{nn_desc}")

print("\n--- CONTEO DE REGISTROS POR TABLA ---")
for tabla_tupla in tablas:
    tabla = tabla_tupla[0]
    cursor.execute(f"SELECT COUNT(*) FROM {tabla};")
    conteo = cursor.fetchone()[0]
    print(f"  - {tabla}: {conteo} registros")

conexion.close()
