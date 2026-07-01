import pandas as pd
import datetime
import math
import requests
import sys
import calendar
import re

from database.db_adapter import Conexion
from database.migrate import ejecutar_migraciones

FUENTE_SFC = 1
EA_MAX_VALIDA = 100.0
EA_MIN_VALIDA = 0.0

FUENTE_TASAS_BANCARIAS = 1

REQ_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

TIBC_API = "https://www.datos.gov.co/resource/pare-7x5i.json"
BANK_RATES_API = "https://www.datos.gov.co/resource/w9zh-vetq.json"

REQUIRED_MODALIDADES = [
    "tasa_usura_consumo_ordinario",
    "tasa_usura_bajo_monto",
    "tasa_usura_productivo_mayor_monto",
    "tasa_usura_productivo_rural",
    "tasa_usura_productivo_urbano",
    "tasa_usura_popular_productivo_rural",
    "tasa_usura_popular_productivo_urbano",
    "tasa_usura_consumo",
    "tasa_usura_microcredito",
]

TIBC_MODALIDAD_MAP = {
    "CONSUMO Y ORDINARIO": ["tasa_usura_consumo_ordinario", "tasa_usura_consumo"],
    "CONSUMO BAJO MONTO": ["tasa_usura_bajo_monto"],
    "CREDITO PRODUCTIVO MAYOR MONTO": ["tasa_usura_productivo_mayor_monto"],
    "CREDITO PRODUCTIVO RURAL": ["tasa_usura_productivo_rural"],
    "CREDITO PRODUCTIVO URBANO": ["tasa_usura_productivo_urbano"],
    "CREDITO POPULAR PRODUCTIVO RURAL": ["tasa_usura_popular_productivo_rural"],
    "CREDITO POPULAR PRODUCTIVO URBANO": ["tasa_usura_popular_productivo_urbano"],
    "MICROCREDITO": ["tasa_usura_microcredito"],
}

BANK_RATE_LOOKUPS = [
    ("Bancolombia", "Libre inversi\u00f3n", "890903938-8", "Libre Inversion Bancolombia"),
    ("Bancolombia", "Adquisici\u00f3n de vivienda no vis", "890903938-8", "Hipotecario Pesos Bancolombia"),
    ("Banco de Bogot\u00e1", "Libre inversi\u00f3n", "860002964-4", "Libre Destinacion Banco de Bogota"),
    ("Confiar", "Libre inversi\u00f3n", "890981395-1", "Microcredito Confiar"),
    ("Banco Davivienda", "Libre inversi\u00f3n", "860034313-7", "Credito Movil Davivienda"),
    ("BBVA Colombia", "Libre inversi\u00f3n", "860003020-1", "Prestamo de Libre Inversion BBVA"),
    ("Banco Popular", "Libre inversi\u00f3n", "860007738-9", "Credito de Libranza Banco Popular"),
    ("Banco de Occidente", "Libre inversi\u00f3n", "890300279-4", "Libre Inversi\u00f3n Banco de Occidente"),
    ("AV Villas", "Libre inversi\u00f3n", "860035827-5", "Credito Libre Inversion AV Villas"),
    ("Banco Caja Social S.A.", "Libre inversi\u00f3n", "860007335-4", "Credito Libre Inversion Banco Caja Social"),
    ("Ita\u00fa", "Libre inversi\u00f3n", "890903937-0", "Credito Libre Inversion Itau"),
    ("Banco Falabella S.A.", "Libre inversi\u00f3n", "900047981-8", "Credito de Libre Inversion Banco Falabella"),
    ("Banco Pichincha S.A.", "Libre inversi\u00f3n", "890200756-7", "Libre Inversi\u00f3n Banco Pichincha"),
    ("Nu Colombia C.F.", "Libre inversi\u00f3n", "901659846-8", "Prestamo Nu Colombia"),
    ("Lulo Bank", "Libre inversi\u00f3n", "901353491-1", "Credito Digital Lulo Bank"),
    ("Rappipay", "Libre inversi\u00f3n", "901400002-9", "Credito RappiPay"),
    ("JFK Cooperativa Financiera", "Libranza otros", "890907489-5", "Libranza JFK Cooperativa"),
]


class ExtractionError(Exception):
    pass


def calcular_tasa_mv(tasa_ea):
    tasa_decimal = tasa_ea / 100.0
    mv_decimal = math.pow(1.0 + tasa_decimal, 1.0 / 12.0) - 1.0
    return round(mv_decimal * 100.0, 2)


def obtener_conexion():
    return Conexion()


def log_sync(cursor, fuente_id, estado, registros_procesados, detalles):
    fecha = datetime.date.today().isoformat()
    cursor.execute(
        "INSERT INTO sync_logs (fecha_ejecucion, fuente_id, estado, registros_procesados, detalles) VALUES (?, ?, ?, ?, ?)",
        (fecha, fuente_id, estado, registros_procesados, detalles),
    )


# ============================================
# VALIDACIÓN Y LIMPIEZA
# ============================================

class ValidationError(Exception):
    pass


def limpiar_tasa(raw_value):
    if raw_value is None:
        raise ValueError("Valor nulo recibido para tasa")
    if isinstance(raw_value, (int, float)):
        return float(raw_value)
    s = str(raw_value).strip()
    s = s.replace("*", "")
    s = s.replace("\xa0", " ")
    s = re.sub(r"\s+", "", s)
    s = s.replace("$", "").replace("%", "")
    s = s.replace(",", ".")
    s = re.sub(r"[^\d.\-]", "", s)
    if not s or s in (".", "-", "-."):
        raise ValueError(f"No se pudo extraer valor numérico de: '{raw_value}'")
    return float(s)


def validar_rango_tasa_ea(valor):
    if not isinstance(valor, (int, float)):
        return False
    if math.isnan(valor) or math.isinf(valor):
        return False
    return EA_MIN_VALIDA < valor < EA_MAX_VALIDA


def detectar_salto_anomalo(conexion, producto_id, nuevo_valor, umbral=15.0):
    cursor = conexion.cursor()
    cursor.execute(
        "SELECT tasa_ea FROM tasas WHERE producto_id = ? ORDER BY fecha_actualizacion DESC LIMIT 1",
        (producto_id,),
    )
    row = cursor.fetchone()
    if row is None:
        return None
    anterior = float(row[0])
    if anterior == 0.0:
        return None
    cambio_pct = abs(nuevo_valor - anterior) / anterior * 100.0
    if cambio_pct > umbral:
        return (anterior, round(cambio_pct, 2))
    return None


def validar_saltos_tasas(df, conexion, umbral=15.0):
    cursor = conexion.cursor()
    filas_validas = []
    for _, row in df.iterrows():
        cursor.execute("SELECT id FROM productos WHERE banco_id IN (SELECT id FROM bancos WHERE nit = ?) AND nombre = ?",
                       (row["nit"], row["producto"]))
        prod_res = cursor.fetchone()
        if prod_res is None:
            filas_validas.append(row)
            continue
        resultado = detectar_salto_anomalo(conexion, prod_res[0], row["tasa_ea"], umbral)
        if resultado is not None:
            anterior, pct = resultado
            print(f"  [BLOQUEO] {row['producto']} ({row['nit']}): salto de {pct}% "
                  f"(anterior={anterior}%, nuevo={row['tasa_ea']}%) — NO se inserta")
            continue
        filas_validas.append(row)
    if len(filas_validas) < len(df):
        print(f"  [VALIDACIÓN] {len(df) - len(filas_validas)} registro(s) bloqueado(s) por salto anómalo")
    return pd.DataFrame(filas_validas)


def validar_saltos_usura(usura_rates, conexion, umbral=15.0):
    cursor = conexion.cursor()
    validados = {}
    for nombre, nuevo_valor in usura_rates.items():
        cursor.execute(
            "SELECT valor FROM indicadores WHERE nombre = ? ORDER BY fecha_vigencia_inicio DESC LIMIT 1",
            (nombre,),
        )
        row = cursor.fetchone()
        if row is not None:
            anterior = float(row[0])
            if anterior != 0.0:
                cambio_pct = abs(nuevo_valor - anterior) / anterior * 100.0
                if cambio_pct > umbral:
                    print(f"  [BLOQUEO] {nombre}: salto de {round(cambio_pct, 2)}% "
                          f"(anterior={anterior}%, nuevo={nuevo_valor}%) — NO se inserta")
                    continue
        validados[nombre] = nuevo_valor
    if len(validados) < len(usura_rates):
        print(f"  [VALIDACIÓN] {len(usura_rates) - len(validados)} indicador(es) bloqueado(s) por salto anómalo")
    return validados


# ============================================
# EXTRACCIÓN: SFC (usura / indicadores) via TIBC API
# ============================================

def extraer_tasas_usura():
    print("  [SFC API] Consultando TIBC desde datos.gov.co...")
    today = datetime.date.today()
    vigencia_desde = today.replace(day=1).isoformat()
    url = f"{TIBC_API}?$where=vigencia_desde>='{vigencia_desde}'&$order=modalidad"
    print(f"    URL: {url}")
    resp = requests.get(url, timeout=30, headers=REQ_HEADERS)
    if resp.status_code != 200:
        raise ExtractionError(
            f"TIBC API retornó HTTP {resp.status_code}: {resp.text[:200]}. "
            "No se pueden obtener tasas de usura."
        )
    data = resp.json()
    if not data:
        raise ExtractionError(
            f"TIBC API no devolvió datos para vigencia_desde >= {vigencia_desde}. "
            "El dataset puede estar desactualizado."
        )
    print(f"    {len(data)} registros recibidos de la API")

    usura = {}
    for row in data:
        sfc_mod = row.get("modalidad", "").strip().upper()
        tibc_str = row.get("interes_bancario_corriente", "0%")
        try:
            tibc = limpiar_tasa(tibc_str)
        except (ValueError, TypeError) as e:
            print(f"    [WARN] Valor no numérico TIBC para {sfc_mod}: {tibc_str} — {e}")
            continue
        target_keys = TIBC_MODALIDAD_MAP.get(sfc_mod, [])
        for key in target_keys:
            usura_val = round(tibc * 1.5, 2)
            if key not in usura:
                usura[key] = usura_val
                print(f"    {sfc_mod} -> {key}: TIBC={tibc}% -> USURA={usura_val}%")

    found = set(usura.keys())
    missing = set(REQUIRED_MODALIDADES) - found

    if missing:
        print(f"    Modalidades faltantes del período actual: {missing}")
        if "tasa_usura_microcredito" in missing:
            print("    Buscando MICROCREDITO (certificación trimestral)...")
            micro_url = f"{TIBC_API}?$where=modalidad='MICROCREDITO'&$order=vigencia_desde DESC&$limit=1"
            micro_resp = requests.get(micro_url, timeout=15, headers=REQ_HEADERS)
            if micro_resp.status_code == 200:
                micro_data = micro_resp.json()
                if micro_data:
                    try:
                        tibc = limpiar_tasa(micro_data[0].get("interes_bancario_corriente", "0%"))
                        usura["tasa_usura_microcredito"] = round(tibc * 1.5, 2)
                        print(f"    MICROCREDITO -> tasa_usura_microcredito: TIBC={tibc}% -> USURA={usura['tasa_usura_microcredito']}%")
                    except ValueError as e:
                        print(f"    [WARN] MICROCREDITO TIBC no numérico: {e}")
            missing = set(REQUIRED_MODALIDADES) - set(usura.keys())

    if missing:
        print(f"    Modalidades aún faltantes: {missing}")

    if not usura:
        raise ExtractionError(
            "No se pudo extraer ninguna tasa de usura desde la API de datos.gov.co. "
            "Verifica conectividad y estructura del dataset pare-7x5i."
        )

    print(f"  [SFC API] {len(usura)} modalidades de usura extraídas correctamente")
    for k, v in sorted(usura.items()):
        print(f"    {k}: {v}%")
    return usura


# ============================================
# EXTRACCIÓN: Tasas bancarias via SFC API
# ============================================

def _consultar_rates_api(sfc_entities, sfc_product, max_retries=3, timeout=60):
    entities_filter = "%20OR%20".join(
        f"nombre_entidad='{e}'" for e in sfc_entities
    )
    url = (
        f"{BANK_RATES_API}"
        f"?$select=nombre_entidad,avg(tasa_efectiva_promedio)"
        f"&$where=({entities_filter})"
        f"%20AND%20producto_de_cr_dito='{sfc_product}'"
        f"%20AND%20fecha_corte>='2025-01-01'"
        f"&$group=nombre_entidad"
    )
    print(f"    Consultando API: {len(sfc_entities)} entidades, producto='{sfc_product}'")
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, timeout=timeout, headers=REQ_HEADERS)
            if resp.status_code == 200:
                data = resp.json()
                result = {}
                for row in data:
                    raw = row.get("avg_tasa_efectiva_promedio")
                    if raw is not None:
                        try:
                            result[row["nombre_entidad"]] = round(float(raw), 2)
                        except (ValueError, TypeError):
                            pass
                return result
            print(f"      HTTP {resp.status_code}, reintento {attempt + 1}")
        except requests.exceptions.Timeout:
            print(f"      Timeout, reintento {attempt + 1}")
        except requests.exceptions.ConnectionError:
            print(f"      Error de conexión, reintento {attempt + 1}")
    raise ExtractionError(
        f"No se pudo consultar la API de tasas bancarias para '{sfc_product}' "
        f"después de {max_retries} intentos."
    )


def extraer_tasas_bancarias():
    libre_inv_entities = {}
    for sfc_entity, sfc_product, nit, prod_name in BANK_RATE_LOOKUPS:
        if sfc_product == "Libre inversi\u00f3n":
            libre_inv_entities.setdefault(sfc_entity, []).append((nit, prod_name))

    libre_inv_api_data = {}
    if libre_inv_entities:
        print(f"\n  Consultando tasas 'Libre inversión' para {len(libre_inv_entities)} entidades...")
        libre_inv_api_data = _consultar_rates_api(list(libre_inv_entities.keys()), "Libre inversi\u00f3n")

    results = []
    errores = []
    for sfc_entity, sfc_product, nit, prod_name in BANK_RATE_LOOKUPS:
        print(f"\n  [{nit}] {prod_name}")
        print(f"    SFC entity: '{sfc_entity}', product: '{sfc_product}'")
        if sfc_product == "Libre inversi\u00f3n":
            tasa = libre_inv_api_data.get(sfc_entity)
            if tasa is None:
                print(f"      Entidad no encontrada en respuesta de API")
                errores.append(f"{prod_name} (NIT {nit}): sin datos en API para {sfc_entity}/{sfc_product}")
                continue
        else:
            print(f"    Producto no estándar, consultando individualmente...")
            entities_filter = f"nombre_entidad='{sfc_entity}'"
            url = (
                f"{BANK_RATES_API}"
                f"?$select=avg(tasa_efectiva_promedio)"
                f"&$where={entities_filter}"
                f"%20AND%20producto_de_cr_dito='{sfc_product}'"
                f"%20AND%20fecha_corte>='2025-01-01'"
            )
            try:
                resp = requests.get(url, timeout=60, headers=REQ_HEADERS)
                if resp.status_code == 200:
                    d = resp.json()
                    if d and "avg_tasa_efectiva_promedio" in d[0] and d[0]["avg_tasa_efectiva_promedio"] is not None:
                        tasa = round(float(d[0]["avg_tasa_efectiva_promedio"]), 2)
                    else:
                        errores.append(f"{prod_name} (NIT {nit}): sin datos para {sfc_entity}/{sfc_product}")
                        continue
                else:
                    errores.append(f"{prod_name} (NIT {nit}): HTTP {resp.status_code}")
                    continue
            except Exception as e:
                errores.append(f"{prod_name} (NIT {nit}): error: {e}")
                continue

        try:
            tasa = limpiar_tasa(tasa)
        except ValueError as e:
            errores.append(f"{prod_name} (NIT {nit}): limpieza falló: {e}")
            continue

        if not validar_rango_tasa_ea(tasa):
            errores.append(f"{prod_name} (NIT {nit}): tasa fuera de rango ({tasa})")
            continue

        print(f"    >>> {prod_name} = {tasa}% EA")
        results.append({"nit": nit, "producto": prod_name, "tasa_ea": tasa})

    if errores:
        for e in errores:
            print(f"  [WARN] {e}")

    if not results:
        raise ExtractionError(
            "No se pudo extraer ninguna tasa bancaria desde la API de datos.gov.co. "
            "Verifica conectividad y estructura del dataset w9zh-vetq."
        )

    print(f"\n  Total bancos procesados: {len(results)}")
    for r in results:
        print(f"    {r['nit']} | {r['producto']}: {r['tasa_ea']}% EA")
    return results


# ============================================
# TRANSFORMACIÓN Y VALIDACIÓN
# ============================================

def validar_tasas_bancarias(raw_rates):
    df = pd.DataFrame(raw_rates)
    if "nit" not in df.columns or "producto" not in df.columns or "tasa_ea" not in df.columns:
        raise ValueError("Faltan columnas requeridas: nit, producto, tasa_ea")
    antes = len(df)
    df = df[df["tasa_ea"].apply(validar_rango_tasa_ea)]
    if len(df) < antes:
        print(f"  [VALIDACIÓN] {antes - len(df)} registro(s) fuera de rango eliminado(s)")
    df = df.drop_duplicates(subset=["nit", "producto"])
    df["tasa_mv"] = df["tasa_ea"].apply(calcular_tasa_mv)
    return df


def validar_tasas_usura(usura_rates):
    validados = {}
    for nombre, valor in usura_rates.items():
        try:
            v = limpiar_tasa(valor)
        except ValueError as e:
            print(f"  [WARN] Valor no numérico para {nombre}: {valor} — {e}")
            continue
        if not (0 < v <= 200):
            print(f"  [WARN] Valor fuera de rango para {nombre}: {v}")
            continue
        validados[nombre] = v
    return validados


# ============================================
# CARGA
# ============================================

def cargar_tasas_bancarias(df, conexion, fecha_actual):
    cursor = conexion.cursor()
    registros_actualizados = 0
    errores = []
    for _, row in df.iterrows():
        try:
            cursor.execute("SELECT id FROM bancos WHERE nit = ?", (row["nit"],))
            banco_res = cursor.fetchone()
            if not banco_res:
                errores.append(f"Banco no encontrado: NIT {row['nit']}")
                continue
            banco_id = banco_res[0]
            cursor.execute(
                "SELECT id FROM productos WHERE banco_id = ? AND nombre = ?",
                (banco_id, row["producto"]),
            )
            prod_res = cursor.fetchone()
            if not prod_res:
                errores.append(f"Producto no encontrado: {row['producto']}")
                continue
            producto_id = prod_res[0]
            cursor.execute(
                "INSERT INTO tasas (producto_id, tasa_ea, tasa_mv, fuente_id, fecha_actualizacion) VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(producto_id) DO UPDATE SET tasa_ea = excluded.tasa_ea, tasa_mv = excluded.tasa_mv, fuente_id = excluded.fuente_id, fecha_actualizacion = excluded.fecha_actualizacion",
                (producto_id, row["tasa_ea"], row["tasa_mv"], FUENTE_TASAS_BANCARIAS, fecha_actual),
            )
            cursor.execute(
                "INSERT OR IGNORE INTO historico_tasas (producto_id, tasa_ea, tasa_mv, fecha_registro) VALUES (?, ?, ?, ?)",
                (producto_id, row["tasa_ea"], row["tasa_mv"], fecha_actual),
            )
            registros_actualizados += 1
        except Exception as e:
            errores.append(f"Error procesando {row.get('producto', '?')}: {e}")
    return registros_actualizados, errores


def cargar_tasas_usura(usura_rates, conexion, fecha_actual, fecha_inicio_mes, fecha_fin_mes):
    cursor = conexion.cursor()
    registros_actualizados = 0
    errores = []
    for nombre, valor in usura_rates.items():
        try:
            cursor.execute(
                "INSERT INTO indicadores (nombre, valor, fecha_vigencia_inicio, fecha_vigencia_fin) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(nombre) DO UPDATE SET valor = excluded.valor, fecha_vigencia_inicio = excluded.fecha_vigencia_inicio, fecha_vigencia_fin = excluded.fecha_vigencia_fin",
                (nombre, valor, fecha_inicio_mes, fecha_fin_mes),
            )
            cursor.execute(
                "INSERT OR IGNORE INTO historico_indicadores (nombre, valor, fuente_id, fecha_consulta, fecha_vigencia_inicio, fecha_vigencia_fin) VALUES (?, ?, ?, ?, ?, ?)",
                (nombre, valor, FUENTE_SFC, fecha_actual, fecha_inicio_mes, fecha_fin_mes),
            )
            registros_actualizados += 1
        except Exception as e:
            errores.append(f"Error cargando {nombre}: {e}")
    return registros_actualizados, errores


# ============================================
# PIPELINE PRINCIPAL
# ============================================

def correr_etl():
    print("=" * 60)
    print("  CREDIT INTELLIGENCE COLOMBIA - ETL PIPELINE")
    print("=" * 60)
    print("\n[Paso 0] Verificando esquema de base de datos...")
    ejecutar_migraciones()

    fecha_actual = datetime.date.today().isoformat()
    today = datetime.date.today()
    fecha_inicio_mes = today.replace(day=1).isoformat()
    _, ultimo_dia = calendar.monthrange(today.year, today.month)
    fecha_fin_mes = today.replace(day=ultimo_dia).isoformat()

    conexion = obtener_conexion()
    cursor = conexion.cursor()
    success = True

    try:
        # ============ PIPELINE 1: TASAS BANCARIAS ============
        print("\n[Pipeline 1] Tasas Bancarias")
        print("-" * 40)
        print("Fase 1: Extracción desde sitios web oficiales...")
        raw_rates = extraer_tasas_bancarias()

        print("Fase 2: Transformación y validación...")
        df = validar_tasas_bancarias(raw_rates)
        print(f"  Registros válidos: {len(df)}")
        print("Fase 2b: Detección de saltos anómalos...")
        df = validar_saltos_tasas(df, conexion)
        print(f"  Registros tras detección de saltos: {len(df)}")

        print("Fase 3: Carga en base de datos...")
        proc_bancos, err_bancos = cargar_tasas_bancarias(df, conexion, fecha_actual)
        if err_bancos:
            for e in err_bancos[:5]:
                print(f"  [WARN] {e}")
            if len(err_bancos) > 5:
                print(f"  [WARN] ... y {len(err_bancos) - 5} error(es) más")
        log_sync(
            cursor, 1, "SUCCESS" if proc_bancos > 0 else "FAILED",
            proc_bancos, f"Tasas bancarias: {proc_bancos} actualizadas, {len(err_bancos)} errores",
        )
        print(f"  Resultado: {proc_bancos} tasa(s) bancaria(s) actualizada(s)")

        # ============ PIPELINE 2: TASAS DE USURA ============
        print(f"\n[Pipeline 2] Tasas de Usura e Indicadores")
        print("-" * 40)
        print("Fase 1: Extracción desde SFC / fuentes oficiales...")
        usura_rates = extraer_tasas_usura()

        print("Fase 2: Validación...")
        usura_validados = validar_tasas_usura(usura_rates)
        print(f"  Indicadores válidos: {len(usura_validados)}")
        print("Fase 2b: Detección de saltos anómalos en usura...")
        usura_validados = validar_saltos_usura(usura_validados, conexion)
        print(f"  Indicadores tras detección de saltos: {len(usura_validados)}")

        print("Fase 3: Carga en base de datos...")
        proc_usura, err_usura = cargar_tasas_usura(
            usura_validados, conexion, fecha_actual, fecha_inicio_mes, fecha_fin_mes,
        )
        if err_usura:
            for e in err_usura:
                print(f"  [WARN] {e}")
        log_sync(
            cursor, FUENTE_SFC, "SUCCESS" if proc_usura > 0 else "FAILED",
            proc_usura, f"Usura/indicadores: {proc_usura} actualizados, {len(err_usura)} errores",
        )
        print(f"  Resultado: {proc_usura} indicador(es) actualizado(s)")

        conexion.commit()
        print(f"\n{'=' * 60}")
        print(f"  ETL COMPLETADO: {fecha_actual}")
        print(f"  Tasas bancarias: {proc_bancos}")
        print(f"  Indicadores usura: {proc_usura}")
        print(f"{'=' * 60}")

    except ExtractionError as error:
        success = False
        print(f"\n[ERROR DE EXTRACCIÓN] {error}")
        print("[ETL DETENIDO] No se insertaron datos fabricados.")
        try:
            log_sync(cursor, 1, "FAILED", 0, f"Error extracción: {str(error)}")
            conexion.commit()
        except Exception:
            pass
    except Exception as error:
        success = False
        print(f"\n[ERROR CRÍTICO] {error}")
        try:
            log_sync(cursor, 1, "FAILED", 0, f"Error crítico ETL: {str(error)}")
            conexion.commit()
        except Exception:
            pass
    finally:
        conexion.close()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(correr_etl())
