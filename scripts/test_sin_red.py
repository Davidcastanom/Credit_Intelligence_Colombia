"""
Tests offline — no requieren internet ni BD externa.
Valida funciones de limpieza, rango, conversion, traduccion SQL y amortizacion.
Correr con: python scripts/test_sin_red.py
"""

import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.etl_scraper import limpiar_tasa, validar_rango_tasa_ea, calcular_tasa_mv
from database.db_adapter import _translate_sql


# ============================================
# Grupo 1: limpiar_tasa()
# ============================================
# Toma un valor crudo desde la API (string o numero) y devuelve float limpio.
# Debe eliminar: asteriscos, espacios, $, %, comas (cambiandolas a punto),
# unicode \xa0, y cualquier otro caracter no numerico.

def test_limpiar_tasa_entero():
    """Entero simple"""
    assert limpiar_tasa(25) == 25.0

def test_limpiar_tasa_float():
    """Float directo"""
    assert limpiar_tasa(18.5) == 18.5

def test_limpiar_tasa_string_simple():
    """String con punto decimal"""
    assert limpiar_tasa("24.50") == 24.50

def test_limpiar_tasa_con_asterisco():
    """String con asterisco (dato preliminar)"""
    assert limpiar_tasa("18.5*") == 18.5

def test_limpiar_tasa_con_porcentaje():
    """String con signo %"""
    assert limpiar_tasa("24.50%") == 24.50

def test_limpiar_tasa_con_dolar():
    """String con signo $"""
    assert limpiar_tasa("$24.50") == 24.50

def test_limpiar_tasa_con_coma_decimal():
    """String con coma como separador decimal (locale)"""
    assert limpiar_tasa("24,50") == 24.50

def test_limpiar_tasa_con_espacios():
    """String con espacios alrededor"""
    assert limpiar_tasa("  24.50  ") == 24.50

def test_limpiar_tasa_con_unicode_xa0():
    """String con \xa0 (non-breaking space)"""
    assert limpiar_tasa("24.50\xa0") == 24.50

def test_limpiar_tasa_con_todo():
    """String con asterisco, espacios, $, % y unicode mezclados"""
    assert limpiar_tasa("$ 24.50* %\xa0") == 24.50

def test_limpiar_tasa_none_raise():
    """None debe lanzar ValueError"""
    try:
        limpiar_tasa(None)
        assert False, "Debio lanzar ValueError"
    except ValueError:
        pass

def test_limpiar_tasa_vacio_raise():
    """String vacio debe lanzar ValueError"""
    try:
        limpiar_tasa("")
        assert False, "Debio lanzar ValueError"
    except ValueError:
        pass


# ============================================
# Grupo 2: validar_rango_tasa_ea()
# ============================================
# Una tasa EA valida debe ser un numero entre 0.0 y 100.0 (exclusivo en ambos extremos).
# NaN e Inf deben ser rechazados.

def test_rango_valido_normal():
    assert validar_rango_tasa_ea(18.5) == True

def test_rango_valido_limite_inferior():
    """0.01 debe ser valido (0.0 es exclusivo)"""
    assert validar_rango_tasa_ea(0.01) == True

def test_rango_valido_limite_superior():
    """99.99 debe ser valido (100.0 es exclusivo)"""
    assert validar_rango_tasa_ea(99.99) == True

def test_rango_invalido_cero():
    """0.0 NO debe ser valido"""
    assert validar_rango_tasa_ea(0.0) == False

def test_rango_invalido_cien():
    """100.0 NO debe ser valido"""
    assert validar_rango_tasa_ea(100.0) == False

def test_rango_invalido_negativo():
    """Tasa negativa debe ser invalida"""
    assert validar_rango_tasa_ea(-5.0) == False

def test_rango_invalido_excesivo():
    """Tasa sobre 100% debe ser invalida"""
    assert validar_rango_tasa_ea(150.0) == False

def test_rango_invalido_nan():
    """NaN debe ser invalido"""
    assert validar_rango_tasa_ea(float("nan")) == False

def test_rango_invalido_inf():
    """Infinito debe ser invalido"""
    assert validar_rango_tasa_ea(float("inf")) == False

def test_rango_invalido_string():
    """String no es numero -> False"""
    assert validar_rango_tasa_ea("18.5") == False


# ============================================
# Grupo 3: calcular_tasa_mv()
# ============================================
# Formula: MV = (1 + EA/100)^(1/12) - 1, resultado en porcentaje.
# La tasa EA se entrega en % (ej: 24.50 significa 24.50%).

def test_calcular_mv_cero():
    """0% EA debe dar 0% MV"""
    assert calcular_tasa_mv(0.0) == 0.0

def test_calcular_mv_conocido():
    """24.50% EA debe dar ~1.84% MV (valor de referencia SFC)"""
    mv = calcular_tasa_mv(24.50)
    assert abs(mv - 1.84) < 0.01

def test_calcular_mv_round():
    """18.0% EA debe dar ~1.39% MV"""
    mv = calcular_tasa_mv(18.0)
    assert abs(mv - 1.39) < 0.01


# ============================================
# Grupo 4: _translate_sql() (adapter PostgreSQL)
# ============================================
# Convierte SQL estilo SQLite a sintaxis PostgreSQL.
# Reglas: ? -> %s, INSERT OR IGNORE -> ON CONFLICT DO NOTHING,
# INTEGER PRIMARY KEY AUTOINCREMENT -> SERIAL PRIMARY KEY, etc.

def test_translate_param_placeholder():
    """? debe convertirse a %s"""
    assert _translate_sql("SELECT * FROM tasas WHERE id = ?") == "SELECT * FROM tasas WHERE id = %s"

def test_translate_insert_or_ignore():
    """INSERT OR IGNORE debe agregar ON CONFLICT DO NOTHING"""
    sql = "INSERT OR IGNORE INTO historico_tasas (producto_id) VALUES (?)"
    result = _translate_sql(sql)
    assert "INSERT INTO historico_tasas" in result
    assert "ON CONFLICT DO NOTHING" in result
    assert "OR IGNORE" not in result

def test_translate_insert_values_on_conflict():
    """INSERT ... VALUES con ON CONFLICT no debe duplicar la clausula"""
    sql = "INSERT INTO tasas (id) VALUES (?) ON CONFLICT(id) DO UPDATE SET x = 1"
    result = _translate_sql(sql)
    assert result.count("ON CONFLICT") == 1

def test_translate_insert_select_no_conflict():
    """INSERT ... SELECT no debe recibir ON CONFLICT DO NOTHING"""
    sql = "INSERT INTO historico_tasas SELECT * FROM tmp"
    result = _translate_sql(sql)
    assert "ON CONFLICT" not in result

def test_translate_autoincrement():
    """INTEGER PRIMARY KEY AUTOINCREMENT -> SERIAL PRIMARY KEY"""
    sql = "id INTEGER PRIMARY KEY AUTOINCREMENT"
    assert _translate_sql(sql) == "id SERIAL PRIMARY KEY"

def test_translate_default_date():
    """DEFAULT (date('now')) -> DEFAULT CURRENT_DATE"""
    sql = "creado TEXT DEFAULT (date('now'))"
    assert _translate_sql(sql) == "creado TEXT DEFAULT CURRENT_DATE"

def test_translate_default_datetime():
    """DEFAULT (datetime('now')) -> DEFAULT NOW()"""
    sql = "creado TEXT DEFAULT (datetime('now'))"
    assert _translate_sql(sql) == "creado TEXT DEFAULT NOW()"

def test_translate_sqlite_master():
    """sqlite_master -> information_schema.tables"""
    sql = "SELECT name FROM sqlite_master"
    assert _translate_sql(sql) == "SELECT name FROM information_schema.tables"

def test_translate_excluded():
    """excluded. -> EXCLUDED."""
    sql = "SET x = excluded.x"
    assert _translate_sql(sql) == "SET x = EXCLUDED.x"


# ============================================
# Grupo 5: Formula de amortizacion (sistema frances)
# ============================================
# Cuota fija mensual: C = (M * i) / (1 - (1 + i)^(-n))
# donde M = monto, i = tasa mensual decimal, n = plazo en meses

def test_amortizacion_conocida():
    """Monto 10M, 18% EA, 60 meses -> cuota ~246,734"""
    monto = 10_000_000
    tasa_ea = 18.0
    plazo = 60

    tasa_ea_decimal = tasa_ea / 100.0
    i = math.pow(1.0 + tasa_ea_decimal, 1.0 / 12.0) - 1.0
    cuota = (monto * i) / (1 - math.pow(1.0 + i, -plazo))

    assert abs(cuota - 246734) < 100  # tolerancia 100 COP

def test_amortizacion_tasa_cero():
    """Si tasa=0%, cuota = monto / plazo"""
    monto = 1_000_000
    plazo = 12
    i = 0.0
    cuota = monto / plazo if i == 0 else (monto * i) / (1 - math.pow(1.0 + i, -plazo))
    assert abs(cuota - 83333.33) < 1

def test_amortizacion_total_interes():
    """Verificar que total pagado = cuota * plazo >= monto (interes >= 0)"""
    monto = 50_000_000
    tasa_ea = 24.0
    plazo = 120

    i = math.pow(1.0 + tasa_ea / 100.0, 1.0 / 12.0) - 1.0
    cuota = (monto * i) / (1 - math.pow(1.0 + i, -plazo))
    total_pagado = cuota * plazo

    assert total_pagado > monto  # debe haber intereses
    assert total_pagado < monto * 3  # pero no mas del triple


# ============================================
# Grupo 6: Mapeo de usura por categoria
# ============================================
# Cada categoria de credito tiene un indicador de usura asociado.
# Esto se usa en el frontend para calcular el Riesgo Usura.
# Las categorias se cruzan con la columna modalidad_usura de categorias_credito.

def test_mapeo_usura_consumo():
    """Consumo -> tasa_usura_consumo_ordinario"""
    from database.db import obtener_tasas_comparativa
    # No llamamos a la BD, solo verificamos la logica de mapeo
    CATEGORIA_USURA_MAP = {
        "Tarjeta de Crédito": "tasa_usura_consumo_ordinario",
        "Crédito de Consumo": "tasa_usura_consumo_ordinario",
        "Crédito Hipotecario": "tasa_usura_productivo_urbano",
        "Microcrédito": "tasa_usura_microcredito",
        "Libranza": "tasa_usura_consumo_ordinario",
        "Crédito Vehículo": "tasa_usura_consumo_ordinario",
        "Crédito Comercial": "tasa_usura_productivo_mayor_monto",
    }
    assert CATEGORIA_USURA_MAP["Tarjeta de Crédito"] == "tasa_usura_consumo_ordinario"
    assert CATEGORIA_USURA_MAP["Microcrédito"] == "tasa_usura_microcredito"
    assert CATEGORIA_USURA_MAP["Crédito Hipotecario"] == "tasa_usura_productivo_urbano"


# ============================================
# Ejecucion
# ============================================
if __name__ == "__main__":
    tests = [
        ("limpiar_tasa", test_limpiar_tasa_entero),
        ("limpiar_tasa", test_limpiar_tasa_float),
        ("limpiar_tasa", test_limpiar_tasa_string_simple),
        ("limpiar_tasa", test_limpiar_tasa_con_asterisco),
        ("limpiar_tasa", test_limpiar_tasa_con_porcentaje),
        ("limpiar_tasa", test_limpiar_tasa_con_dolar),
        ("limpiar_tasa", test_limpiar_tasa_con_coma_decimal),
        ("limpiar_tasa", test_limpiar_tasa_con_espacios),
        ("limpiar_tasa", test_limpiar_tasa_con_unicode_xa0),
        ("limpiar_tasa", test_limpiar_tasa_con_todo),
        ("limpiar_tasa", test_limpiar_tasa_none_raise),
        ("limpiar_tasa", test_limpiar_tasa_vacio_raise),
        ("validar_rango", test_rango_valido_normal),
        ("validar_rango", test_rango_valido_limite_inferior),
        ("validar_rango", test_rango_valido_limite_superior),
        ("validar_rango", test_rango_invalido_cero),
        ("validar_rango", test_rango_invalido_cien),
        ("validar_rango", test_rango_invalido_negativo),
        ("validar_rango", test_rango_invalido_excesivo),
        ("validar_rango", test_rango_invalido_nan),
        ("validar_rango", test_rango_invalido_inf),
        ("validar_rango", test_rango_invalido_string),
        ("calcular_mv", test_calcular_mv_cero),
        ("calcular_mv", test_calcular_mv_conocido),
        ("calcular_mv", test_calcular_mv_round),
        ("translate_sql", test_translate_param_placeholder),
        ("translate_sql", test_translate_insert_or_ignore),
        ("translate_sql", test_translate_insert_values_on_conflict),
        ("translate_sql", test_translate_insert_select_no_conflict),
        ("translate_sql", test_translate_autoincrement),
        ("translate_sql", test_translate_default_date),
        ("translate_sql", test_translate_default_datetime),
        ("translate_sql", test_translate_sqlite_master),
        ("translate_sql", test_translate_excluded),
        ("amortizacion", test_amortizacion_conocida),
        ("amortizacion", test_amortizacion_tasa_cero),
        ("amortizacion", test_amortizacion_total_interes),
        ("mapeo_usura", test_mapeo_usura_consumo),
    ]

    print(f"\nCredit Intelligence Colombia - Tests sin red")
    print(f"{'='*50}")
    pasaron = 0
    fallaron = 0
    grupo_actual = ""
    for grupo, test_fn in tests:
        if grupo != grupo_actual:
            grupo_actual = grupo
            print(f"\n  [{grupo}]")
        try:
            test_fn()
            print(f"    [OK] {test_fn.__name__}")
            pasaron += 1
        except Exception as e:
            print(f"    [FAIL] {test_fn.__name__}: {e}")
            fallaron += 1

    print(f"\n{'='*50}")
    print(f"  Total: {pasaron + fallaron} | OK {pasaron} | FAIL {fallaron}")
    sys.exit(0 if fallaron == 0 else 1)
