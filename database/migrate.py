import sqlite3
import os


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


if __name__ == "__main__":
    ejecutar_migraciones()
