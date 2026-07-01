from database.db_adapter import Conexion, DatabaseError, ConnectionError


def obtener_conexion():
    try:
        return Conexion()
    except ConnectionError:
        raise
    except Exception as e:
        raise ConnectionError(f"Error inesperado al conectar: {e}")


def obtener_tasas_comparativa():
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT
                b.nombre AS banco,
                b.nit AS nit,
                b.url_web AS url_banco,
                b.tipo_entidad AS tipo_entidad,
                p.nombre AS producto,
                c.nombre AS categoria,
                c.modalidad_usura AS modalidad_usura,
                t.tasa_ea AS tasa_ea,
                t.tasa_mv AS tasa_mv,
                t.fecha_actualizacion AS fecha_actualizacion,
                f.nombre AS fuente,
                f.url AS url_fuente
            FROM tasas t
            JOIN productos p ON t.producto_id = p.id
            JOIN bancos b ON p.banco_id = b.id
            JOIN categorias_credito c ON p.categoria_id = c.id
            JOIN fuentes f ON t.fuente_id = f.id
            ORDER BY t.tasa_ea ASC
        """)
        resultados = [dict(row) for row in cursor.fetchall()]
        conexion.close()
        return resultados
    except DatabaseError:
        raise
    except Exception as e:
        raise DatabaseError(f"Error al obtener tasas comparativa: {e}")


def obtener_indicadores():
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute(
            "SELECT nombre, valor, fecha_vigencia_inicio, fecha_vigencia_fin FROM indicadores"
        )
        resultados = [dict(row) for row in cursor.fetchall()]
        conexion.close()
        return resultados
    except DatabaseError:
        raise
    except Exception as e:
        raise DatabaseError(f"Error al obtener indicadores: {e}")


def obtener_historial():
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT
                b.nombre AS banco,
                b.url_web AS url_banco,
                b.tipo_entidad AS tipo_entidad,
                p.nombre AS producto,
                h.tasa_ea AS tasa_ea,
                h.tasa_mv AS tasa_mv,
                h.fecha_registro AS fecha_registro
            FROM historico_tasas h
            JOIN productos p ON h.producto_id = p.id
            JOIN bancos b ON p.banco_id = b.id
            ORDER BY h.fecha_registro ASC
        """)
        resultados = [dict(row) for row in cursor.fetchall()]
        conexion.close()
        return resultados
    except DatabaseError:
        raise
    except Exception as e:
        raise DatabaseError(f"Error al obtener historial: {e}")


def obtener_historial_indicadores():
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT
                hi.nombre,
                hi.valor,
                hi.fecha_consulta,
                hi.fecha_vigencia_inicio,
                hi.fecha_vigencia_fin,
                f.nombre AS fuente,
                f.url AS url_fuente
            FROM historico_indicadores hi
            JOIN fuentes f ON hi.fuente_id = f.id
            ORDER BY hi.nombre ASC, hi.fecha_consulta ASC
        """)
        resultados = [dict(row) for row in cursor.fetchall()]
        conexion.close()
        return resultados
    except DatabaseError:
        raise
    except Exception as e:
        raise DatabaseError(f"Error al obtener historial de indicadores: {e}")


def obtener_indicadores_con_id():
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute(
            "SELECT id, nombre, valor, fecha_vigencia_inicio, fecha_vigencia_fin FROM indicadores ORDER BY nombre"
        )
        resultados = [dict(row) for row in cursor.fetchall()]
        conexion.close()
        return resultados
    except DatabaseError:
        raise
    except Exception as e:
        raise DatabaseError(f"Error al obtener indicadores con id: {e}")


def actualizar_indicador(indicador_id, nuevo_valor):
    import datetime
    import calendar
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute(
            "SELECT nombre, valor, fecha_vigencia_inicio, fecha_vigencia_fin FROM indicadores WHERE id = ?",
            (indicador_id,),
        )
        anterior = cursor.fetchone()
        if not anterior:
            conexion.close()
            raise ValueError(f"Indicador {indicador_id} no encontrado")

        nombre = anterior["nombre"]
        today = datetime.date.today()
        fecha_inicio = today.replace(day=1).isoformat()
        _, ultimo_dia = calendar.monthrange(today.year, today.month)
        fecha_fin = today.replace(day=ultimo_dia).isoformat()
        fecha_actual = today.isoformat()

        cursor.execute(
            "UPDATE indicadores SET valor = ?, fecha_vigencia_inicio = ?, fecha_vigencia_fin = ? WHERE id = ?",
            (nuevo_valor, fecha_inicio, fecha_fin, indicador_id),
        )

        cursor.execute(
            "INSERT OR IGNORE INTO historico_indicadores (nombre, valor, fuente_id, fecha_consulta, fecha_vigencia_inicio, fecha_vigencia_fin) VALUES (?, ?, 1, ?, ?, ?)",
            (nombre, nuevo_valor, fecha_actual, fecha_inicio, fecha_fin),
        )

        conexion.commit()
        conexion.close()
    except DatabaseError:
        raise
    except Exception as e:
        raise DatabaseError(f"Error al actualizar indicador: {e}")


def obtener_ultimo_sync():
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT fecha_ejecucion, fuente_id, estado, registros_procesados, detalles
            FROM sync_logs
            ORDER BY fecha_ejecucion DESC, id DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
        conexion.close()
        if row:
            return {
                "fecha_ejecucion": row["fecha_ejecucion"],
                "estado": row["estado"],
                "registros_procesados": row["registros_procesados"],
                "detalles": row["detalles"],
            }
        return None
    except DatabaseError:
        raise
    except Exception as e:
        raise DatabaseError(f"Error al obtener último sync: {e}")


def crear_o_actualizar_usuario(google_id, email, nombre, avatar_url=""):
    import datetime
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        today = datetime.date.today().isoformat()

        cursor.execute("SELECT id FROM usuarios WHERE google_id = ?", (google_id,))
        existe = cursor.fetchone()

        if existe:
            cursor.execute(
                "UPDATE usuarios SET email=?, nombre=?, avatar_url=?, last_login=? WHERE google_id=?",
                (email, nombre, avatar_url, today, google_id),
            )
            user_id = existe["id"]
        else:
            cursor.execute(
                "INSERT INTO usuarios (google_id, email, nombre, avatar_url, created_at, last_login) VALUES (?, ?, ?, ?, ?, ?)",
                (google_id, email, nombre, avatar_url, today, today),
            )
            user_id = cursor.lastrowid

        conexion.commit()
        cursor.execute("SELECT * FROM usuarios WHERE id = ?", (user_id,))
        usuario = dict(cursor.fetchone())
        conexion.close()
        return usuario
    except DatabaseError:
        raise
    except Exception as e:
        raise DatabaseError(f"Error al crear/actualizar usuario: {e}")


def obtener_usuario_por_id(user_id):
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conexion.close()
        return dict(row) if row else None
    except DatabaseError:
        raise
    except Exception as e:
        raise DatabaseError(f"Error al obtener usuario: {e}")


def aceptar_terminos(user_id):
    import datetime
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute(
            "UPDATE usuarios SET accepted_terms=1, accepted_terms_at=? WHERE id=?",
            (datetime.date.today().isoformat(), user_id),
        )
        conexion.commit()
        conexion.close()
    except DatabaseError:
        raise
    except Exception as e:
        raise DatabaseError(f"Error al aceptar términos: {e}")


def actualizar_preferencias(user_id, notifications_enabled):
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute(
            "UPDATE usuarios SET notifications_enabled=? WHERE id=?",
            (1 if notifications_enabled else 0, user_id),
        )
        conexion.commit()
        conexion.close()
    except DatabaseError:
        raise
    except Exception as e:
        raise DatabaseError(f"Error al actualizar preferencias: {e}")


def obtener_usuarios_con_notificaciones():
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute(
            "SELECT id, email, nombre FROM usuarios WHERE notifications_enabled=1"
        )
        resultados = [dict(row) for row in cursor.fetchall()]
        conexion.close()
        return resultados
    except DatabaseError:
        raise
    except Exception as e:
        raise DatabaseError(f"Error al obtener usuarios con notificaciones: {e}")


def obtener_todos_usuarios():
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute(
            "SELECT id, google_id, email, nombre, avatar_url, accepted_terms, notifications_enabled, created_at, last_login FROM usuarios ORDER BY created_at DESC"
        )
        resultados = [dict(row) for row in cursor.fetchall()]
        conexion.close()
        return resultados
    except DatabaseError:
        raise
    except Exception as e:
        raise DatabaseError(f"Error al obtener todos los usuarios: {e}")


def guardar_newsletter_log(asunto, cuerpo_html, total_destinatarios, enviados):
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute(
            "INSERT INTO newsletter_log (asunto, cuerpo, destinatarios, enviados) VALUES (?, ?, ?, ?)",
            (asunto, cuerpo_html, total_destinatarios, enviados),
        )
        conexion.commit()
        conexion.close()
    except DatabaseError:
        raise
    except Exception as e:
        raise DatabaseError(f"Error al guardar newsletter log: {e}")
