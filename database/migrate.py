from datetime import datetime, timedelta

from database.db_adapter import Conexion, DatabaseError


MIGRATIONS = [
    # 0. Tabla historico_indicadores para tracking histórico de tasas de usura
    """
    CREATE TABLE IF NOT EXISTS historico_indicadores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        valor REAL NOT NULL,
        fuente_id INTEGER NOT NULL,
        fecha_consulta TEXT NOT NULL,
        fecha_vigencia_inicio TEXT NOT NULL,
        fecha_vigencia_fin TEXT NOT NULL,
        FOREIGN KEY (fuente_id) REFERENCES fuentes(id) ON DELETE CASCADE
    );
    """,
    # 1. Índice único para evitar duplicados en historico_indicadores
    """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_historico_indicadores_unique
    ON historico_indicadores(nombre, fecha_vigencia_inicio, fecha_consulta);
    """,
    # 2. Índice único para evitar duplicados en historico_tasas por producto+fecha
    """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_historico_tasas_unique
    ON historico_tasas(producto_id, fecha_registro);
    """,
    # 3. Índice para búsquedas rápidas por fecha en sync_logs
    """
    CREATE INDEX IF NOT EXISTS idx_sync_logs_fecha
    ON sync_logs(fecha_ejecucion);
    """,
    # 4. Índice para búsquedas rápidas en historico_tasas por fecha
    """
    CREATE INDEX IF NOT EXISTS idx_historico_tasas_fecha
    ON historico_tasas(fecha_registro);
    """,
    # 5. Índice para búsquedas rápidas en historico_indicadores por nombre
    """
    CREATE INDEX IF NOT EXISTS idx_historico_indicadores_nombre
    ON historico_indicadores(nombre);
    """,
    # 6. Migrar registros actuales de indicadores a historico_indicadores (si no existen)
    """
    INSERT OR IGNORE INTO historico_indicadores (nombre, valor, fuente_id, fecha_consulta, fecha_vigencia_inicio, fecha_vigencia_fin)
    SELECT i.nombre, i.valor, 1, i.fecha_vigencia_inicio, i.fecha_vigencia_inicio, i.fecha_vigencia_fin
    FROM indicadores i
    WHERE NOT EXISTS (
        SELECT 1 FROM historico_indicadores hi
        WHERE hi.nombre = i.nombre AND hi.fecha_vigencia_inicio = i.fecha_vigencia_inicio
    );
    """,
    # 7. Tabla de usuarios registrados con Google
    """
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        google_id TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        nombre TEXT NOT NULL,
        avatar_url TEXT DEFAULT '',
        accepted_terms INTEGER DEFAULT 0,
        accepted_terms_at TEXT,
        notifications_enabled INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (date('now')),
        last_login TEXT DEFAULT (date('now'))
    );
    """,
    # 8. Tabla para historial de notificaciones enviadas
    """
    CREATE TABLE IF NOT EXISTS newsletter_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        asunto TEXT NOT NULL,
        cuerpo TEXT NOT NULL,
        destinatarios INTEGER DEFAULT 0,
        enviados INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now'))
    );
    """,
    # 9. Histórico de usura para abril y mayo 2025 (base comparativa)
    """
    INSERT OR IGNORE INTO historico_indicadores (nombre, valor, fuente_id, fecha_consulta, fecha_vigencia_inicio, fecha_vigencia_fin)
    VALUES
        ('tasa_usura_consumo_ordinario', 31.50, 1, '2025-04-30', '2025-04-01', '2025-04-30'),
        ('tasa_usura_bajo_monto',        68.00, 1, '2025-04-30', '2025-04-01', '2025-04-30'),
        ('tasa_usura_consumo',           31.50, 1, '2025-04-30', '2025-04-01', '2025-04-30'),
        ('tasa_usura_microcredito',      46.50, 1, '2025-04-30', '2025-04-01', '2025-04-30'),
        ('tasa_usura_productivo_mayor_monto', 46.50, 1, '2025-04-30', '2025-04-01', '2025-04-30'),
        ('tasa_usura_productivo_rural',  49.80, 1, '2025-04-30', '2025-04-01', '2025-04-30'),
        ('tasa_usura_productivo_urbano', 54.00, 1, '2025-04-30', '2025-04-01', '2025-04-30'),
        ('tasa_usura_popular_productivo_rural',  68.00, 1, '2025-04-30', '2025-04-01', '2025-04-30'),
        ('tasa_usura_popular_productivo_urbano', 42.50, 1, '2025-04-30', '2025-04-01', '2025-04-30'),
        ('tasa_usura_consumo_ordinario', 30.20, 1, '2025-05-31', '2025-05-01', '2025-05-31'),
        ('tasa_usura_bajo_monto',        65.50, 1, '2025-05-31', '2025-05-01', '2025-05-31'),
        ('tasa_usura_consumo',           30.20, 1, '2025-05-31', '2025-05-01', '2025-05-31'),
        ('tasa_usura_microcredito',      44.50, 1, '2025-05-31', '2025-05-01', '2025-05-31'),
        ('tasa_usura_productivo_mayor_monto', 44.50, 1, '2025-05-31', '2025-05-01', '2025-05-31'),
        ('tasa_usura_productivo_rural',  47.30, 1, '2025-05-31', '2025-05-01', '2025-05-31'),
        ('tasa_usura_productivo_urbano', 52.00, 1, '2025-05-31', '2025-05-01', '2025-05-31'),
        ('tasa_usura_popular_productivo_rural',  65.50, 1, '2025-05-31', '2025-05-01', '2025-05-31'),
        ('tasa_usura_popular_productivo_urbano', 40.80, 1, '2025-05-31', '2025-05-01', '2025-05-31');
    """,
]


INITIAL_SCHEMA = """
CREATE TABLE IF NOT EXISTS bancos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nit TEXT UNIQUE NOT NULL,
    nombre TEXT NOT NULL,
    razon_social TEXT,
    url_web TEXT,
    tipo_entidad TEXT NOT NULL DEFAULT 'Banco tradicional'
);

CREATE TABLE IF NOT EXISTS categorias_credito (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT UNIQUE NOT NULL,
    descripcion TEXT,
    modalidad_usura TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fuentes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT UNIQUE NOT NULL,
    tipo TEXT NOT NULL,
    url TEXT
);

CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    banco_id INTEGER NOT NULL REFERENCES bancos(id) ON DELETE CASCADE,
    categoria_id INTEGER NOT NULL REFERENCES categorias_credito(id) ON DELETE CASCADE,
    nombre TEXT NOT NULL,
    descripcion TEXT
);

CREATE TABLE IF NOT EXISTS historico_tasas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
    tasa_ea REAL NOT NULL,
    tasa_mv REAL NOT NULL,
    fecha_registro TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS indicadores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT UNIQUE NOT NULL,
    valor REAL NOT NULL,
    fecha_vigencia_inicio TEXT NOT NULL,
    fecha_vigencia_fin TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sync_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_ejecucion TEXT NOT NULL,
    fuente_id INTEGER NOT NULL REFERENCES fuentes(id) ON DELETE CASCADE,
    estado TEXT NOT NULL,
    registros_procesados INTEGER NOT NULL,
    detalles TEXT
);

CREATE TABLE IF NOT EXISTS tasas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id INTEGER UNIQUE NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
    tasa_ea REAL NOT NULL,
    tasa_mv REAL NOT NULL,
    fuente_id INTEGER NOT NULL REFERENCES fuentes(id) ON DELETE CASCADE,
    fecha_actualizacion TEXT NOT NULL
);
"""

INITIAL_BANCOS = [
    (1, "890903938-8", "Bancolombia", "Bancolombia S.A.", "Banco tradicional"),
    (2, "860002964-4", "Banco de Bogotá", "Banco de Bogotá S.A.", "Banco tradicional"),
    (3, "901587541-9", "Nequi", "Nequi S.A.S.", "Nubanco"),
    (4, "890981395-1", "Confiar", "Confiar Cooperativa Financiera", "Cooperativa"),
    (5, "860034313-7", "Davivienda", "Banco Davivienda S.A.", "Banco tradicional"),
    (6, "860003020-1", "BBVA", "BBVA Colombia S.A.", "Banco tradicional"),
    (7, "860007738-9", "Banco Popular", "Banco Popular S.A.", "Banco tradicional"),
    (8, "890300279-4", "Banco de Occidente", "Banco de Occidente S.A.", "Banco tradicional"),
    (9, "860035827-5", "AV Villas", "Banco AV Villas S.A.", "Banco tradicional"),
    (10, "860007335-4", "Banco Caja Social", "Banco Caja Social S.A.", "Banco tradicional"),
    (11, "860034594-1", "Scotiabank Colpatria", "Scotiabank Colpatria S.A.", "Banco tradicional"),
    (12, "800037800-8", "Banco Agrario", "Banco Agrario de Colombia S.A.", "Banco tradicional"),
    (13, "890903937-0", "Itaú", "Itaú Corpbanca Colombia S.A.", "Banco tradicional"),
    (14, "900047981-8", "Falabella", "Banco Falabella S.A.", "Banco tradicional"),
    (15, "890200756-7", "Pichincha", "Banco Pichincha S.A.", "Banco tradicional"),
    (16, "901659846-8", "Nu Colombia", "Nu Colombia C.F.", "Nubanco"),
    (17, "901353491-1", "Lulo Bank", "Lulo Bank S.A.", "Nubanco"),
    (18, "901400002-9", "RappiPay", "RappiPay S.A.S.", "Nubanco"),
    (19, "901097473-5", "Uala", "Uala Colombia S.A.S.", "Nubanco"),
    (20, "890906213-1", "Coofinep", "Coofinep Cooperativa Financiera", "Cooperativa"),
    (21, "890901176-3", "Cotrafa", "Cotrafa Cooperativa Financiera", "Cooperativa"),
    (22, "890907489-5", "JFK", "JFK Cooperativa Financiera", "Cooperativa"),
    (23, "890985032-6", "Fincomercio", "Fincomercio Cooperativa Financiera", "Cooperativa"),
]

BANCO_URLS = {
    "890903938-8": "https://www.bancolombia.com",
    "860002964-4": "https://www.bancodebogota.com",
    "901587541-9": "https://www.nequi.com.co",
    "890981395-1": "https://www.confiar.coop",
    "860034313-7": "https://www.davivienda.com",
    "860003020-1": "https://www.bbva.com.co",
    "860007738-9": "https://www.bancopopular.com.co",
    "890300279-4": "https://www.bancodeoccidente.com.co",
    "860035827-5": "https://www.avvillas.com.co",
    "860007335-4": "https://www.bancocajasocial.com",
    "860034594-1": "https://www.scotiabankcolpatria.com",
    "800037800-8": "https://www.bancoagrario.gov.co",
    "890903937-0": "https://www.itau.co",
    "900047981-8": "https://www.bancofalabella.com.co",
    "890200756-7": "https://www.bancopichincha.com.co",
    "901659846-8": "https://nu.com.co",
    "901353491-1": "https://www.lulobank.com",
    "901400002-9": "https://www.rappipay.co",
    "901097473-5": "https://www.uala.com.co",
    "890906213-1": "https://www.coofinep.com",
    "890901176-3": "https://www.cotrafa.com.co",
    "890907489-5": "https://www.jfk.com.co",
    "890985032-6": "https://www.fincomercio.com",
}

INITIAL_FUENTES = [
    (1, "Superintendencia Financiera de Colombia", "Oficial", "https://www.superfinanciera.gov.co/"),
    (2, "Datos Abiertos Colombia - SFC", "OpenData", "https://www.datos.gov.co/"),
]

INITIAL_CATEGORIAS = [
    (1, "Tarjeta de Crédito", "Crédito rotativo con cupo asignado.", "tasa_usura_consumo_ordinario"),
    (2, "Crédito de Consumo", "Crédito de libre inversión.", "tasa_usura_consumo_ordinario"),
    (3, "Crédito Hipotecario", "Crédito para vivienda.", "tasa_usura_consumo_ordinario"),
    (4, "Microcrédito", "Crédito para microempresas.", "tasa_usura_microcredito"),
    (5, "Libranza", "Crédito con descuento por nómina.", "tasa_usura_consumo_ordinario"),
    (6, "Crédito Vehículo", "Financiación para compra de vehículo.", "tasa_usura_consumo_ordinario"),
    (7, "Crédito Comercial", "Capital de trabajo empresarial.", "tasa_usura_productivo_urbano"),
]


def _existe_tabla(cursor, nombre_tabla):
    try:
        cursor.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ? AND table_type = 'BASE TABLE'",
            (nombre_tabla,),
        )
    except Exception:
        cursor.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",
            (nombre_tabla,),
        )
    return cursor.fetchone()[0] > 0


def _init_schema(conn, cursor):
    for statement in INITIAL_SCHEMA.split(";"):
        s = statement.strip()
        if s:
            try:
                cursor.execute(s + ";")
            except Exception as e:
                print(f"  [WARN] Creando tabla: {e}")
    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM bancos")
    if cursor.fetchone()[0] == 0:
        for row_id, nit, nombre, razon, tipo in INITIAL_BANCOS:
            cursor.execute(
                "INSERT INTO bancos (id, nit, nombre, razon_social, url_web, tipo_entidad) VALUES (?, ?, ?, ?, ?, ?)",
                (row_id, nit, nombre, razon, BANCO_URLS.get(nit, ""), tipo),
            )
    for nit, url_web in BANCO_URLS.items():
        cursor.execute(
            "UPDATE bancos SET url_web = ? WHERE nit = ? AND (url_web IS NULL OR url_web = '')",
            (url_web, nit),
        )

    cursor.execute("SELECT COUNT(*) FROM fuentes")
    if cursor.fetchone()[0] == 0:
        for row_id, nombre, tipo, url in INITIAL_FUENTES:
            cursor.execute(
                "INSERT INTO fuentes (id, nombre, tipo, url) VALUES (?, ?, ?, ?)",
                (row_id, nombre, tipo, url),
            )

    cursor.execute("SELECT COUNT(*) FROM categorias_credito")
    if cursor.fetchone()[0] == 0:
        for row_id, nombre, descripcion, modalidad in INITIAL_CATEGORIAS:
            cursor.execute(
                "INSERT INTO categorias_credito (id, nombre, descripcion, modalidad_usura) VALUES (?, ?, ?, ?)",
                (row_id, nombre, descripcion, modalidad),
            )
    conn.commit()


def ejecutar_migraciones():
    conn = Conexion()
    cursor = conn.cursor()

    _init_schema(conn, cursor)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            migration_index INTEGER NOT NULL UNIQUE,
            aplicada_en TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)

    cursor.execute("SELECT COALESCE(MAX(migration_index), -1) FROM schema_migrations")
    ultima = cursor.fetchone()[0]

    ejecutadas = 0
    for idx, sql in enumerate(MIGRATIONS):
        if idx <= ultima:
            continue
        if idx == 6 and not _existe_tabla(cursor, "indicadores"):
            print(f"  [SKIP] Migración {idx}: tabla 'indicadores' no existe (BD nueva).")
            cursor.execute("INSERT INTO schema_migrations (migration_index) VALUES (?)", (idx,))
            continue
        if idx == 9 and not _existe_tabla(cursor, "historico_indicadores"):
            print(f"  [SKIP] Migración {idx}: tabla 'historico_indicadores' no existe (BD nueva).")
            cursor.execute("INSERT INTO schema_migrations (migration_index) VALUES (?)", (idx,))
            continue
        try:
            cursor.execute(sql)
            cursor.execute("INSERT INTO schema_migrations (migration_index) VALUES (?)", (idx,))
            ejecutadas += 1
            print(f"  [OK] Migración {idx} aplicada.")
        except Exception as e:
            print(f"  [ERROR] Migración {idx}: {e}")
            conn.rollback()
            conn.close()
            raise

    # Migration 10: agregar url_web a bancos si no existe
    try:
        cursor.execute("SELECT url_web FROM bancos LIMIT 1")
    except Exception:
        try:
            cursor.execute("ALTER TABLE bancos ADD COLUMN url_web TEXT")
            cursor.execute("INSERT INTO schema_migrations (migration_index) VALUES (10)")
            print("  [OK] Migración 10: columna url_web agregada a bancos.")
            ejecutadas += 1
        except Exception as e:
            print(f"  [ERROR] Migración 10: {e}")
            conn.rollback()
            conn.close()
            raise

    # Seed URLs for all banks after migration
    for nit, url_web in BANCO_URLS.items():
        cursor.execute(
            "UPDATE bancos SET url_web = ? WHERE nit = ? AND (url_web IS NULL OR url_web = '')",
            (url_web, nit),
        )
    conn.commit()

    if ejecutadas == 0:
        print("  Base de datos actualizada. No se requirieron migraciones.")
    else:
        print(f"  {ejecutadas} migración(es) aplicada(s) correctamente.")

    poblar_productos_adicionales()
    poblar_indicadores()
    conn.close()


def poblar_productos_adicionales():
    adicionales = [
        (1, 1, "Tarjeta de Crédito Bancolombia", "Crédito rotativo con cupo asignado.", 29.50),
        (1, 6, "Crédito Vehículo Bancolombia", "Financiación para compra de vehículo nuevo o usado.", 19.80),
        (1, 5, "Libranza Bancolombia", "Crédito con descuento por nómina.", 23.40),
        (2, 1, "Tarjeta de Crédito Banco de Bogotá", "Crédito rotativo para compras nacionales e internacionales.", 30.20),
        (2, 3, "Crédito Vivienda Banco de Bogotá", "Crédito hipotecario para adquisición de vivienda.", 13.80),
        (2, 6, "Crédito Vehículo Banco de Bogotá", "Financiación de vehículo con tasa fija.", 20.40),
        (2, 5, "Libranza Banco de Bogotá", "Crédito de libranza para empleados.", 24.10),
        (5, 1, "Tarjeta de Crédito Davivienda", "Crédito rotativo con cupo y cuota de manejo.", 31.00),
        (5, 3, "Crédito Vivienda Davivienda", "Financiación de vivienda nueva o usada.", 14.50),
        (5, 5, "Libranza Davivienda", "Crédito con descuento por nómina o pensión.", 22.80),
        (6, 1, "Tarjeta de Crédito BBVA", "Crédito rotativo con programa de puntos.", 28.90),
        (6, 3, "Crédito Vivienda BBVA", "Crédito hipotecario en pesos o UVR.", 14.00),
        (6, 6, "Crédito Vehículo BBVA", "Financiación de vehículo con seguros incluidos.", 21.30),
        (7, 1, "Libre Inversión Banco Popular", "Crédito de consumo libre destino.", 25.60),
        (7, 1, "Tarjeta de Crédito Banco Popular", "Crédito rotativo para empleados y pensionados.", 32.40),
        (8, 1, "Libre Inversión Banco de Occidente", "Crédito de consumo para personas.", 24.70),
        (8, 1, "Tarjeta de Crédito Banco de Occidente", "Crédito rotativo con beneficios.", 30.80),
        (9, 1, "Tarjeta de Crédito AV Villas", "Crédito rotativo con seguros asociados.", 31.50),
        (9, 3, "Crédito Vivienda AV Villas", "Crédito hipotecario para vivienda.", 15.20),
        (10, 3, "Crédito Vivienda Banco Caja Social", "Financiación de vivienda de interés social.", 12.90),
        (10, 1, "Tarjeta de Crédito Banco Caja Social", "Crédito rotativo con cuota baja.", 29.80),
        (11, 1, "Libre Inversión Scotiabank Colpatria", "Crédito de consumo libre destino.", 26.10),
        (11, 1, "Tarjeta de Crédito Scotiabank Colpatria", "Crédito rotativo internacional.", 30.40),
        (13, 1, "Tarjeta de Crédito Itaú", "Crédito rotativo con millas.", 29.20),
        (13, 3, "Crédito Vivienda Itaú", "Crédito hipotecario en pesos.", 14.80),
        (14, 1, "Tarjeta de Crédito Falabella", "Crédito rotativo para compras en Falabella.", 33.00),
        (15, 1, "Libre Inversión Banco Pichincha", "Crédito de consumo libre destino.", 27.30),
        (15, 7, "Crédito Comercial Banco Pichincha", "Capital de trabajo para empresas.", 28.50),
    ]

    conn = Conexion()
    c = conn.cursor()

    c.execute("SELECT COALESCE(MAX(id), 0) FROM productos")
    max_id = c.fetchone()[0]

    hoy = datetime.now().strftime("%Y-%m-%d")
    insertados = 0
    for banco_id, cat_id, nombre, descripcion, tasa_ea in adicionales:
        c.execute("SELECT id FROM productos WHERE banco_id=? AND nombre=?", (banco_id, nombre))
        row = c.fetchone()
        if row:
            continue
        max_id += 1
        tasa_mv = round((((1 + tasa_ea / 100) ** (1 / 12)) - 1) * 100, 2)
        try:
            c.execute(
                "INSERT INTO productos (id, banco_id, categoria_id, nombre, descripcion) VALUES (?,?,?,?,?)",
                (max_id, banco_id, cat_id, nombre, descripcion),
            )
            c.execute(
                "INSERT INTO tasas (producto_id, tasa_ea, tasa_mv, fuente_id, fecha_actualizacion) VALUES (?,?,?,1,?)",
                (max_id, tasa_ea, tasa_mv, hoy),
            )
            for i in range(4):
                fecha = (datetime.strptime(hoy, "%Y-%m-%d") - timedelta(weeks=i)).strftime("%Y-%m-%d")
                c.execute(
                    "INSERT OR IGNORE INTO historico_tasas (producto_id, tasa_ea, tasa_mv, fecha_registro) VALUES (?,?,?,?)",
                    (max_id, tasa_ea, tasa_mv, fecha),
                )
            insertados += 1
        except Exception as e:
            print(f"  [WARN] Error al insertar '{nombre}': {e}")
            conn.rollback()
            c = conn.cursor()
            continue

    conn.commit()
    conn.close()
    if insertados > 0:
        print(f"  {insertados} producto(s) adicional(es) insertado(s).")


def poblar_indicadores():
    conn = Conexion()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM indicadores")
    if c.fetchone()[0] > 0:
        conn.close()
        return

    indicadores = [
        ("tasa_usura_consumo_ordinario", 28.79, "2026-01-01", "2026-12-31"),
        ("tasa_usura_bajo_monto", 37.45, "2026-01-01", "2026-12-31"),
        ("tasa_usura_productivo_urbano", 50.12, "2026-01-01", "2026-12-31"),
        ("tasa_usura_productivo_rural", 33.21, "2026-01-01", "2026-12-31"),
        ("tasa_usura_productivo_mayor_monto", 23.18, "2026-01-01", "2026-12-31"),
        ("tasa_usura_popular_productivo_urbano", 38.45, "2026-01-01", "2026-12-31"),
        ("tasa_usura_popular_productivo_rural", 30.30, "2026-01-01", "2026-12-31"),
        ("dtf_ea", 10.50, "2026-01-01", "2026-12-31"),
    ]
    for nombre, valor, inicio, fin in indicadores:
        try:
            c.execute(
                "INSERT INTO indicadores (nombre, valor, fecha_vigencia_inicio, fecha_vigencia_fin) VALUES (?,?,?,?)",
                (nombre, valor, inicio, fin),
            )
            c.execute(
                "INSERT OR IGNORE INTO historico_indicadores (nombre, valor, fuente_id, fecha_consulta, fecha_vigencia_inicio, fecha_vigencia_fin) VALUES (?, ?, 1, ?, ?, ?)",
                (nombre, valor, inicio, inicio, fin),
            )
        except Exception:
            pass
    conn.commit()
    conn.close()
    print("  Indicadores de usura inicializados (incluye historial 2026).")


if __name__ == "__main__":
    ejecutar_migraciones()
