import sqlite3
from database.migrate import ejecutar_migraciones

conexion = sqlite3.connect("database/tasas.db")

with open("database/schema.sql", "r", encoding="utf-8") as archivo:
    script_sql = archivo.read()

conexion.executescript(script_sql)
conexion.commit()
conexion.close()

# Aplicar migraciones adicionales (índices, tablas nuevas, etc.)
ejecutar_migraciones()

print("Base de datos creada correctamente en database/tasas.db")