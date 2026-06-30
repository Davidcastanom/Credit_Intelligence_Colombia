import sqlite3
import os
from datetime import datetime, timedelta


MIGRATIONS = [
    # 1. Tabla historico_indicadores para tracking histórico de tasas de usura
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
    # 2. Índice único para evitar duplicados en historico_indicadores
    """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_historico_indicadores_unique
    ON historico_indicadores(nombre, fecha_vigencia_inicio, fecha_consulta);
    """,
    # 3. Índice único para evitar duplicados en historico_tasas por producto+fecha
    """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_historico_tasas_unique
    ON historico_tasas(producto_id, fecha_registro);
    """,
    # 4. Índice para búsquedas rápidas por fecha en sync_logs
    """
    CREATE INDEX IF NOT EXISTS idx_sync_logs_fecha
    ON sync_logs(fecha_ejecucion);
    """,
    # 5. Índice para búsquedas rápidas en historico_tasas por fecha
    """
    CREATE INDEX IF NOT EXISTS idx_historico_tasas_fecha
    ON historico_tasas(fecha_registro);
    """,
    # 6. Índice para búsquedas rápidas en historico_indicadores por nombre
    """
    CREATE INDEX IF NOT EXISTS idx_historico_indicadores_nombre
    ON historico_indicadores(nombre);
    """,
    # 7. Migrar registros actuales de indicadores a historico_indicadores (si no existen)
    """
    INSERT OR IGNORE INTO historico_indicadores (nombre, valor, fuente_id, fecha_consulta, fecha_vigencia_inicio, fecha_vigencia_fin)
    SELECT i.nombre, i.valor, 1, i.fecha_vigencia_inicio, i.fecha_vigencia_inicio, i.fecha_vigencia_fin
    FROM indicadores i
    WHERE NOT EXISTS (
        SELECT 1 FROM historico_indicadores hi
        WHERE hi.nombre = i.nombre AND hi.fecha_vigencia_inicio = i.fecha_vigencia_inicio
    );
    """,
    # 8. Tabla de usuarios registrados con Google
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
    # 9. Tabla para historial de notificaciones enviadas
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
]


def ejecutar_migraciones(ruta_db=None):
    if ruta_db is None:
        ruta_db = os.path.join(os.path.dirname(__file__), "tasas.db")

    conn = sqlite3.connect(ruta_db)
    cursor = conn.cursor()

    # Crear tabla de control de migraciones si no existe
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
        # Saltar migraciones de datos si la tabla fuente no existe
        if idx == 7:
            cursor.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='indicadores'"
            )
            if cursor.fetchone()[0] == 0:
                print(f"  [SKIP] Migración {idx}: tabla 'indicadores' no existe (BD nueva).")
                cursor.execute(
                    "INSERT INTO schema_migrations (migration_index) VALUES (?)",
                    (idx,)
                )
                continue
        try:
            cursor.execute(sql)
            cursor.execute(
                "INSERT INTO schema_migrations (migration_index) VALUES (?)",
                (idx,)
            )
            ejecutadas += 1
            print(f"  [OK] Migración {idx} aplicada.")
        except Exception as e:
            print(f"  [ERROR] Migración {idx}: {e}")
            conn.rollback()
            conn.close()
            raise

    conn.commit()
    conn.close()

    if ejecutadas == 0:
        print("  Base de datos actualizada. No se requirieron migraciones.")
    else:
        print(f"  {ejecutadas} migración(es) aplicada(s) correctamente.")

    # Poblar productos adicionales para mayor variedad por banco
    poblar_productos_adicionales(ruta_db)
    poblar_indicadores(ruta_db)


def poblar_productos_adicionales(ruta_db):
    """Agrega más productos por banco para cubrir la variedad real del mercado."""
    adicionales = [
        # (banco_id, categoria_id, nombre, descripcion, tasa_ea)
        # Bancolombia
        (1, 1, "Tarjeta de Crédito Bancolombia", "Crédito rotativo con cupo asignado.", 29.50),
        (1, 6, "Crédito Vehículo Bancolombia", "Financiación para compra de vehículo nuevo o usado.", 19.80),
        (1, 5, "Libranza Bancolombia", "Crédito con descuento por nómina.", 23.40),
        # Banco de Bogotá
        (2, 1, "Tarjeta de Crédito Banco de Bogotá", "Crédito rotativo para compras nacionales e internacionales.", 30.20),
        (2, 3, "Crédito Vivienda Banco de Bogotá", "Crédito hipotecario para adquisición de vivienda.", 13.80),
        (2, 6, "Crédito Vehículo Banco de Bogotá", "Financiación de vehículo con tasa fija.", 20.40),
        (2, 5, "Libranza Banco de Bogotá", "Crédito de libranza para empleados.", 24.10),
        # Davivienda
        (5, 1, "Tarjeta de Crédito Davivienda", "Crédito rotativo con cupo y cuota de manejo.", 31.00),
        (5, 3, "Crédito Vivienda Davivienda", "Financiación de vivienda nueva o usada.", 14.50),
        (5, 5, "Libranza Davivienda", "Crédito con descuento por nómina o pensión.", 22.80),
        # BBVA
        (6, 1, "Tarjeta de Crédito BBVA", "Crédito rotativo con programa de puntos.", 28.90),
        (6, 3, "Crédito Vivienda BBVA", "Crédito hipotecario en pesos o UVR.", 14.00),
        (6, 6, "Crédito Vehículo BBVA", "Financiación de vehículo con seguros incluidos.", 21.30),
        # Banco Popular
        (7, 1, "Libre Inversión Banco Popular", "Crédito de consumo libre destino.", 25.60),
        (7, 1, "Tarjeta de Crédito Banco Popular", "Crédito rotativo para empleados y pensionados.", 32.40),
        # Banco de Occidente
        (8, 1, "Libre Inversión Banco de Occidente", "Crédito de consumo para personas.", 24.70),
        (8, 1, "Tarjeta de Crédito Banco de Occidente", "Crédito rotativo con beneficios.", 30.80),
        # AV Villas
        (9, 1, "Tarjeta de Crédito AV Villas", "Crédito rotativo con seguros asociados.", 31.50),
        (9, 3, "Crédito Vivienda AV Villas", "Crédito hipotecario para vivienda.", 15.20),
        # Caja Social
        (10, 3, "Crédito Vivienda Banco Caja Social", "Financiación de vivienda de interés social.", 12.90),
        (10, 1, "Tarjeta de Crédito Banco Caja Social", "Crédito rotativo con cuota baja.", 29.80),
        # Scotiabank Colpatria
        (11, 1, "Libre Inversión Scotiabank Colpatria", "Crédito de consumo libre destino.", 26.10),
        (11, 1, "Tarjeta de Crédito Scotiabank Colpatria", "Crédito rotativo internacional.", 30.40),
        # Itaú
        (13, 1, "Tarjeta de Crédito Itaú", "Crédito rotativo con millas.", 29.20),
        (13, 3, "Crédito Vivienda Itaú", "Crédito hipotecario en pesos.", 14.80),
        # Falabella
        (14, 1, "Tarjeta de Crédito Falabella", "Crédito rotativo para compras en Falabella.", 33.00),
        # Pichincha
        (15, 1, "Libre Inversión Banco Pichincha", "Crédito de consumo libre destino.", 27.30),
        (15, 7, "Crédito Comercial Banco Pichincha", "Capital de trabajo para empresas.", 28.50),
    ]

    conn = sqlite3.connect(ruta_db)
    c = conn.cursor()

    # Obtener máximo ID actual
    c.execute("SELECT COALESCE(MAX(id), 0) FROM productos")
    max_id = c.fetchone()[0]

    hoy = "2026-06-30"
    insertados = 0
    for banco_id, cat_id, nombre, descripcion, tasa_ea in adicionales:
        # Verificar si ya existe ese producto para ese banco
        c.execute(
            "SELECT id FROM productos WHERE banco_id=? AND nombre=?",
            (banco_id, nombre)
        )
        row = c.fetchone()
        if row:
            continue  # ya existe
        max_id += 1
        tasa_mv = round((((1 + tasa_ea / 100) ** (1/12)) - 1) * 100, 2)
        try:
            c.execute(
                "INSERT INTO productos (id, banco_id, categoria_id, nombre, descripcion) VALUES (?,?,?,?,?)",
                (max_id, banco_id, cat_id, nombre, descripcion)
            )
            c.execute(
                "INSERT INTO tasas (producto_id, tasa_ea, tasa_mv, fuente_id, fecha_actualizacion) VALUES (?,?,?,1,?)",
                (max_id, tasa_ea, tasa_mv, hoy)
            )
            # Historial 4 semanas
            for i in range(4):
                fecha = (datetime.strptime(hoy, "%Y-%m-%d") - timedelta(weeks=i)).strftime("%Y-%m-%d")
                c.execute(
                    "INSERT OR IGNORE INTO historico_tasas (producto_id, tasa_ea, tasa_mv, fecha_registro) VALUES (?,?,?,?)",
                    (max_id, tasa_ea, tasa_mv, fecha)
                )
            insertados += 1
        except Exception as e:
            print(f"  [WARN] Error al insertar '{nombre}': {e}")
            conn.rollback()
            conn.commit()
            continue

    conn.commit()
    conn.close()
    if insertados > 0:
        print(f"  {insertados} producto(s) adicional(es) insertado(s).")


def poblar_indicadores(ruta_db):
    """Inserta indicadores de usura si la tabla está vacía."""
    conn = sqlite3.connect(ruta_db)
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
    ]
    for nombre, valor, inicio, fin in indicadores:
        try:
            c.execute(
                "INSERT INTO indicadores (nombre, valor, fuente_id, fecha_vigencia_inicio, fecha_vigencia_fin) VALUES (?,?,1,?,?)",
                (nombre, valor, inicio, fin)
            )
        except Exception:
            pass
    conn.commit()
    conn.close()
    print("  Indicadores de usura inicializados.")


if __name__ == "__main__":
    ejecutar_migraciones()
