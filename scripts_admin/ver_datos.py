import sqlite3

conexion = sqlite3.connect("database/tasas.db")
cursor = conexion.cursor()

print("--- 1. BANCOS ---")
cursor.execute("SELECT * FROM bancos")
for fila in cursor.fetchall():
    print(fila)

print("\n--- 2. CATEGORIAS DE CREDITO ---")
cursor.execute("SELECT * FROM categorias_credito")
for fila in cursor.fetchall():
    print(fila)

print("\n--- 3. PRODUCTOS ---")
cursor.execute("SELECT * FROM productos")
for fila in cursor.fetchall():
    print(fila)

print("\n--- 4. INDICADORES DE MERCADO ---")
cursor.execute("SELECT * FROM indicadores")
for fila in cursor.fetchall():
    print(fila)

print("\n--- 5. TASAS VIGENTES ---")
cursor.execute("SELECT * FROM tasas")
for fila in cursor.fetchall():
    print(fila)

print("\n--- 6. LOGS DE SINCRONIZACION ---")
cursor.execute("SELECT * FROM sync_logs")
for fila in cursor.fetchall():
    print(fila)

print("\n--- 7. HISTORICO INDICADORES (Usura/DTF) ---")
cursor.execute("SELECT * FROM historico_indicadores")
for fila in cursor.fetchall():
    print(fila)

conexion.close()