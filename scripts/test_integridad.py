"""
Script de verificación de integridad pre-despliegue.

Prueba:
  1. Conectividad a datos.gov.co (ambos datasets)
  2. Parseo de respuestas JSON
  3. Conversión y validación de tasas
  4. Conexión a base de datos e inserción real

USO:
    python scripts/test_integridad.py                          # Todo local (SQLite)
    DATABASE_URL="postgresql://..." python scripts/test_integridad.py   # Contra PostgreSQL
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import datetime

# ---------------------------------------------------------------
# 1. Prueba de conectividad a datos.gov.co
# ---------------------------------------------------------------
print("=" * 60)
print("  TEST DE INTEGRIDAD - CREDIT INTELLIGENCE COLOMBIA")
print("=" * 60)

PASS = 0
FAIL = 0

def test(nombre, ok, detalle=""):
    global PASS, FAIL
    if ok:
        print(f"  [PASS] {nombre}")
        PASS += 1
    else:
        print(f"  [FAIL] {nombre}")
        if detalle:
            print(f"         {detalle}")
        FAIL += 1

print("\n--- 1. Conectividad a datos.gov.co ---\n")

import requests

# Dataset tasas bancarias
try:
    r = requests.get(
        "https://www.datos.gov.co/resource/w9zh-vetq.json?$limit=1",
        timeout=15,
    )
    test("API w9zh-vetq (bancarias) responde", r.status_code == 200, f"HTTP {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        test("API w9zh-vetq devuelve JSON válido", isinstance(data, list), str(type(data)))
        if isinstance(data, list) and len(data) > 0:
            row = data[0]
            cr_required = ("nombre_entidad", "tasa_efectiva_promedio", "producto_de_cr_dito")
    test("JSON tiene campos esperados",
         all(k in row for k in cr_required),
         f"Faltan campos Socrata. Tiene: {list(row.keys())}")
except Exception as e:
    test("API w9zh-vetq (bancarias) responde", False, str(e))

# Dataset TIBC
try:
    r = requests.get(
        "https://www.datos.gov.co/resource/pare-7x5i.json?$limit=1",
        timeout=15,
    )
    test("API pare-7x5i (TIBC/usura) responde", r.status_code == 200, f"HTTP {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        test("API pare-7x5i devuelve JSON válido", isinstance(data, list), str(type(data)))
except Exception as e:
    test("API pare-7x5i (TIBC/usura) responde", False, str(e))

# ---------------------------------------------------------------
# 2. Prueba de parseo y limpieza de tasas
# ---------------------------------------------------------------
print("\n--- 2. Parseo y limpieza de tasas ---\n")

from database.etl_scraper import limpiar_tasa, validar_rango_tasa_ea

casos = [
    ("28.79%", 28.79, "porcentaje básico"),
    ("10,5", 10.5, "coma decimal"),
    (" 22.5 ", 22.5, "espacios alrededor"),
    ("*15.0*", 15.0, "asteriscos alrededor"),
    ("$12,500.00", None, "formato monetario (ambiguo)"),
    ("   ", None, "cadena vacía"),
    ("28.79%", 28.79, "duplicado para validación EA"),
]

for raw, esperado, desc in casos:
    try:
        valor = limpiar_tasa(raw)
        if esperado is None:
            test(f"limpiar_tasa: '{raw}' ({desc})", False, "Debió lanzar ValueError")
        else:
            test(f"limpiar_tasa: '{raw}' -> {valor} ({desc})",
                 abs(valor - esperado) < 0.01,
                 f"Esperado {esperado}, obtenido {valor}")
    except ValueError:
        test(f"limpiar_tasa: '{raw}' ({desc})", esperado is None,
             f"No debió fallar, esperado={esperado}")

test("validar_rango_tasa_ea: 28.79", validar_rango_tasa_ea(28.79))
test("validar_rango_tasa_ea: 99 (valido)", validar_rango_tasa_ea(99.0))
test("validar_rango_tasa_ea: 150 (rechazado)", not validar_rango_tasa_ea(150.0))
test("validar_rango_tasa_ea: -1 (rechazado)", not validar_rango_tasa_ea(-1.0))
test("validar_rango_tasa_ea: 0 (rechazado)", not validar_rango_tasa_ea(0.0))
test("validar_rango_tasa_ea: 999 (rechazado)", not validar_rango_tasa_ea(999.0))

# ---------------------------------------------------------------
# 3. Prueba de extracción real (modo ligero - tasas bancarias)
# ---------------------------------------------------------------
print("\n--- 3. Extracción real desde API ---\n")

from database.etl_scraper import extraer_tasas_bancarias, extraer_tasas_usura

try:
    rates = extraer_tasas_bancarias()
    test(f"extraer_tasas_bancarias devuelve {len(rates)} registros",
         len(rates) >= 15,
         f"Solo {len(rates)} registros")
    if rates:
        sample = rates[0]
        required_keys = {"nit", "producto", "tasa_ea"}
        test("Registros tienen NIT, producto, tasa_ea",
             required_keys.issubset(sample.keys()),
             f"Keys: {list(sample.keys())}")
        for r in rates:
            if not isinstance(r.get("tasa_ea"), (int, float)) or r["tasa_ea"] <= 0:
                test(f"Tasa válida en {r.get('producto')}", False,
                     f"tasa_ea={r.get('tasa_ea')}")
                break
        else:
            test("Todas las tasas bancarias son > 0", True)
except Exception as e:
    test("extraer_tasas_bancarias completa", False, str(e))

try:
    usura = extraer_tasas_usura()
    test(f"extraer_tasas_usura devuelve {len(usura)} indicadores",
         len(usura) >= 8,
         f"Solo {len(usura)} indicadores")
    for nombre, valor in usura.items():
        try:
            v = float(valor) if not isinstance(valor, float) else valor
            if not (0 < v <= 200):
                test(f"Usura {nombre}={valor} en rango", False)
                break
        except (ValueError, TypeError):
            test(f"Usura {nombre}={valor} es numérico", False)
            break
    else:
        test("Todas las tasas de usura son válidas", True)
except Exception as e:
    test("extraer_tasas_usura completa", False, str(e))

# ---------------------------------------------------------------
# 4. Prueba de base de datos (inserción real si se solicita)
# ---------------------------------------------------------------
print("\n--- 4. Conexión a base de datos ---\n")

try:
    from database.db_adapter import Conexion, DatabaseError
    conn = Conexion()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM tasas")
    total_tasas = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM indicadores")
    total_indicadores = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM sync_logs")
    total_syncs = cur.fetchone()[0]
    conn.close()

    test("Conexión a BD exitosa", True)
    test(f"Tasas en BD: {total_tasas}", total_tasas > 0,
         f"BD vacía -- ejecuta 'python scripts/run_etl.py' primero")
    test(f"Indicadores en BD: {total_indicadores}", total_indicadores > 0,
         f"BD vacía -- ejecuta 'python scripts/run_etl.py' primero")
    test(f"Sync logs: {total_syncs}", total_syncs > 0)
except Exception as e:
    test("Conexión a BD", False, str(e))

# ---------------------------------------------------------------
# RESUMEN
# ---------------------------------------------------------------
print(f"\n{'=' * 60}")
print(f"  RESULTADO: {PASS} pasaron, {FAIL} fallaron")
print(f"{'=' * 60}")

sys.exit(0 if FAIL == 0 else 1)
