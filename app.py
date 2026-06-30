import os
import math
import time
import json
import smtplib
import email.utils
import secrets
from email.mime.text import MIMEText
from functools import wraps
from pathlib import Path
from flask import Flask, render_template, jsonify, request, session, redirect, url_for, send_from_directory
from database.migrate import ejecutar_migraciones
from database.db import (
    obtener_tasas_comparativa,
    obtener_indicadores,
    obtener_historial,
    obtener_historial_indicadores,
    obtener_ultimo_sync,
    obtener_indicadores_con_id,
    actualizar_indicador as db_actualizar_indicador,
    crear_o_actualizar_usuario,
    obtener_usuario_por_id,
    aceptar_terminos as db_aceptar_terminos,
    actualizar_preferencias as db_actualizar_preferencias,
    obtener_usuarios_con_notificaciones,
    obtener_todos_usuarios,
    guardar_newsletter_log,
)

app = Flask(__name__)

# ---------------------------------------------------------------
# CONFIGURACIÓN DE SEGURIDAD
# ---------------------------------------------------------------
# Clave secreta de sesión (requerida)
_SECRET_KEY = os.environ.get("FLASK_SECRET_KEY")
if not _SECRET_KEY:
    _SECRET_KEY = secrets.token_hex(32)
    import warnings
    warnings.warn(
        "FLASK_SECRET_KEY no definida. Usando clave temporal. "
        "DEFÍNELA en variables de entorno para sesiones persistentes."
    )
app.secret_key = _SECRET_KEY

# Contraseña de administrador
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
if not ADMIN_PASSWORD:
    ADMIN_PASSWORD = secrets.token_urlsafe(16)
    import warnings
    warnings.warn(
        f"ADMIN_PASSWORD no definida. Usando clave temporal: {ADMIN_PASSWORD}. "
        "DEFÍNELA en variables de entorno."
    )

# Restricción por IP (opcional)
# Formato: "186.27.64.1, 190.24.0.0/16" (IPs separadas por coma, soporta CIDR)
ADMIN_ALLOWED_IPS = os.environ.get("ADMIN_ALLOWED_IPS", "")

# Sesión segura
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("RENDER", "") == "true",
    PERMANENT_SESSION_LIFETIME=3600,  # 1 hora
)

# ---------------------------------------------------------------
# INICIALIZAR BASE DE DATOS AL ARRANCAR
# ---------------------------------------------------------------
ejecutar_migraciones()

# ---------------------------------------------------------------
# RATE LIMITING (anti fuerza bruta)
# ---------------------------------------------------------------
_LOG_DIR = Path("logs")
_LOG_DIR.mkdir(exist_ok=True)
_LOG_FILE = _LOG_DIR / "admin_login.log"

_INTENTOS_FALLIDOS = {}  # ip -> {"count": n, "since": timestamp}
_MAX_INTENTOS = 5
_BLOQUEO_MINUTOS = 15

def _registrar_intento(ip, exitoso):
    ahora = time.time()
    if not exitoso:
        entry = _INTENTOS_FALLIDOS.get(ip)
        if entry and ahora - entry["since"] > _BLOQUEO_MINUTOS * 60:
            _INTENTOS_FALLIDOS[ip] = {"count": 1, "since": ahora}
        elif entry:
            entry["count"] += 1
        else:
            _INTENTOS_FALLIDOS[ip] = {"count": 1, "since": ahora}
        restantes = _MAX_INTENTOS - _INTENTOS_FALLIDOS[ip]["count"]
    else:
        _INTENTOS_FALLIDOS.pop(ip, None)
        restantes = _MAX_INTENTOS

    # Log a archivo
    estado = "EXITO" if exitoso else "FALLO"
    with open(_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {estado} IP={ip} Restantes={restantes}\n")
    return restantes

def _ip_permmitida(ip):
    if not ADMIN_ALLOWED_IPS:
        return True
    import ipaddress
    try:
        addr = ipaddress.ip_address(ip)
        for entrada in ADMIN_ALLOWED_IPS.split(","):
            entrada = entrada.strip()
            if not entrada:
                continue
            if "/" in entrada:
                red = ipaddress.ip_network(entrada, strict=False)
                if addr in red:
                    return True
            elif addr == ipaddress.ip_address(entrada):
                return True
    except ValueError:
        pass
    return False

def _obtener_ip():
    if request.headers.get("X-Forwarded-For"):
        return request.headers["X-Forwarded-For"].split(",")[0].strip()
    return request.remote_addr or "0.0.0.0"

# ============================================
# ADMIN AUTH
# ============================================

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))
        # Verificación de IP en cada request admin
        if ADMIN_ALLOWED_IPS:
            ip = _obtener_ip()
            if not _ip_permmitida(ip):
                return "Acceso no autorizado desde esta IP.", 403
        return f(*args, **kwargs)
    return decorated

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    ip = _obtener_ip()

    # Verificar bloqueo
    entry = _INTENTOS_FALLIDOS.get(ip)
    if entry and entry["count"] >= _MAX_INTENTOS:
        tiempo_restante = int(_BLOQUEO_MINUTOS - (time.time() - entry["since"]) / 60)
        if tiempo_restante > 0:
            return render_template("admin/login.html",
                error=f"Demasiados intentos. Espere {tiempo_restante} minuto(s).",
                bloqueado=True, minutos_restantes=tiempo_restante)

    # Verificar IP permitida
    if ADMIN_ALLOWED_IPS and not _ip_permmitida(ip):
        return "Acceso al panel restringido por seguridad.", 403

    error = None
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            session.permanent = True
            _registrar_intento(ip, exitoso=True)
            return redirect(url_for("admin_dashboard"))
        error = "Contraseña incorrecta"
        restantes = _registrar_intento(ip, exitoso=False)
        if restantes <= 0:
            error = f"Cuenta bloqueada por {_BLOQUEO_MINUTOS} minutos por seguridad."

    return render_template("admin/login.html", error=error)

# Google OAuth
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

# SMTP (correos)
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
SMTP_FROM = os.environ.get("SMTP_FROM", "notificaciones@creditintelligence.co")

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin_login"))

@app.route("/admin/")
@login_required
def admin_dashboard():
    return render_template("admin/dashboard.html")

@app.route("/admin/usura", methods=["GET", "POST"])
@login_required
def admin_usura():
    if request.method == "POST":
        try:
            data = request.get_json() or request.form
            indicador_id = int(data.get("id"))
            nuevo_valor = float(data.get("valor"))
            db_actualizar_indicador(indicador_id, nuevo_valor)
            return jsonify({"status": "ok"})
        except Exception as e:
            return jsonify({"status": "error", "mensaje": str(e)}), 400

    indicadores = obtener_indicadores_con_id()
    return render_template("admin/usura.html", indicadores=indicadores)

# ============================================
# GOOGLE OAUTH (Login de usuarios)
# ============================================

@app.route("/api/auth/google", methods=["POST"])
def api_auth_google():
    if not GOOGLE_CLIENT_ID:
        return jsonify({"error": "Google OAuth no configurado. Defina GOOGLE_CLIENT_ID"}), 400
    try:
        token = request.get_json().get("credential")
        if not token:
            return jsonify({"error": "Token requerido"}), 400

        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests
        info = id_token.verify_oauth2_token(token, google_requests.Request(), GOOGLE_CLIENT_ID)

        google_id = info["sub"]
        email = info.get("email", "")
        nombre = info.get("name", email)
        avatar = info.get("picture", "")

        usuario = crear_o_actualizar_usuario(google_id, email, nombre, avatar)
        session["user_id"] = usuario["id"]
        session["user_name"] = usuario["nombre"]
        session["user_email"] = usuario["email"]
        session["user_avatar"] = usuario["avatar_url"]
        session["user_terms"] = bool(usuario["accepted_terms"])

        return jsonify({
            "id": usuario["id"],
            "nombre": usuario["nombre"],
            "email": usuario["email"],
            "avatar": usuario["avatar_url"],
            "accepted_terms": bool(usuario["accepted_terms"])
        })
    except ValueError as e:
        return jsonify({"error": f"Token inválido: {e}"}), 401
    except ImportError:
        return jsonify({"error": "google-auth no instalado. Ejecute: pip install google-auth"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/auth/me")
def api_auth_me():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"autenticado": False}), 200
    usuario = obtener_usuario_por_id(user_id)
    if not usuario:
        session.clear()
        return jsonify({"autenticado": False}), 200
    return jsonify({
        "autenticado": True,
        "id": usuario["id"],
        "nombre": usuario["nombre"],
        "email": usuario["email"],
        "avatar": usuario["avatar_url"],
        "accepted_terms": bool(usuario["accepted_terms"]),
        "notifications_enabled": bool(usuario["notifications_enabled"])
    })

@app.route("/api/auth/logout", methods=["POST"])
def api_auth_logout():
    session.pop("user_id", None)
    session.pop("user_name", None)
    session.pop("user_email", None)
    session.pop("user_avatar", None)
    session.pop("user_terms", None)
    return jsonify({"status": "ok"})

@app.route("/api/auth/aceptar-terminos", methods=["POST"])
def api_aceptar_terminos():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "No autenticado"}), 401
    db_aceptar_terminos(user_id)
    session["user_terms"] = True
    return jsonify({"status": "ok"})

@app.route("/api/auth/preferencias", methods=["POST"])
def api_actualizar_preferencias():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "No autenticado"}), 401
    data = request.get_json() or {}
    enabled = data.get("notifications_enabled", True)
    db_actualizar_preferencias(user_id, enabled)
    return jsonify({"status": "ok"})

@app.context_processor
def inject_user():
    user_id = session.get("user_id")
    usuario = None
    if user_id:
        usuario = obtener_usuario_por_id(user_id)
    return {
        "current_user": usuario,
        "google_client_id": GOOGLE_CLIENT_ID
    }

# ============================================
# ADMIN: USUARIOS Y NOTIFICACIONES
# ============================================

@app.route("/admin/usuarios")
@login_required
def admin_usuarios():
    usuarios = obtener_todos_usuarios()
    return render_template("admin/usuarios.html", usuarios=usuarios)

@app.route("/admin/notificar", methods=["GET", "POST"])
@login_required
def admin_notificar():
    if request.method == "POST":
        data = request.get_json() or request.form
        asunto = data.get("asunto", "").strip()
        cuerpo = data.get("cuerpo", "").strip()
        if not asunto or not cuerpo:
            return jsonify({"status": "error", "mensaje": "Asunto y cuerpo requeridos"}), 400

        usuarios = obtener_usuarios_con_notificaciones()
        total = len(usuarios)
        enviados = 0
        errores = []

        if not SMTP_HOST:
            guardar_newsletter_log(asunto, cuerpo, total, 0)
            return jsonify({
                "status": "ok",
                "mensaje": f"Correo guardado (SMTP no configurado). {total} destinatarios pendientes.",
                "total": total, "enviados": 0
            })

        cuerpo_html = cuerpo.replace("\n", "<br>")
        html = f"""<html><body style="font-family:Segoe UI,sans-serif;padding:20px;">
<h2 style="color:#3b82f6;">Credit Intelligence Colombia</h2>
{cuerpo_html}
<hr><p style="color:#666;font-size:0.8rem;">
Este correo fue enviado porque estás registrado en Credit Intelligence Colombia.
Si no deseas recibir estas notificaciones, inicia sesión y desactívalas en tu perfil.</p></body></html>"""

        try:
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            for u in usuarios:
                try:
                    msg = MIMEText(html, "html", "utf-8")
                    msg["Subject"] = asunto
                    msg["From"] = SMTP_FROM
                    msg["To"] = u["email"]
                    msg["Date"] = email.utils.formatdate()
                    server.sendmail(SMTP_FROM, [u["email"]], msg.as_string())
                    enviados += 1
                except Exception as e:
                    errores.append(f"{u['email']}: {e}")
            server.quit()
        except Exception as e:
            guardar_newsletter_log(asunto, cuerpo, total, 0)
            return jsonify({"status": "error", "mensaje": f"Error SMTP: {e}"}), 500

        guardar_newsletter_log(asunto, cuerpo, total, enviados)
        return jsonify({
            "status": "ok",
            "mensaje": f"Enviado a {enviados}/{total} usuarios. {len(errores)} error(es).",
            "total": total, "enviados": enviados, "errores": errores[:5]
        })

    usuarios = obtener_usuarios_con_notificaciones()
    return render_template("admin/notificar.html", usuarios=usuarios, smtp_configured=bool(SMTP_HOST))

# ============================================
# VISTAS FRONTEND
# ============================================

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/comparar")
def comparar():
    return render_template("comparar.html")

@app.route("/calculadora")
def calculadora():
    return render_template("calculadora.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/favicon.ico")
def favicon():
    return send_from_directory(app.static_folder, "favicon.ico", mimetype="image/x-icon")

# ============================================
# ENDPOINTS REST API
# ============================================

@app.route("/api/tasas")
def api_tasas():
    try:
        return jsonify(obtener_tasas_comparativa())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/indicadores")
def api_indicadores():
    try:
        return jsonify(obtener_indicadores())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/historial")
def api_historial():
    try:
        return jsonify(obtener_historial())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/historial/usura")
def api_historial_usura():
    try:
        return jsonify(obtener_historial_indicadores())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/sync/status")
def api_sync_status():
    try:
        ultimo = obtener_ultimo_sync()
        if ultimo:
            return jsonify(ultimo)
        return jsonify({"estado": "NO_DATA", "fecha_ejecucion": None, "registros_procesados": 0})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/amortizacion", methods=["GET", "POST"])
def api_amortizacion():
    try:
        if request.method == "POST":
            datos = request.get_json() or {}
            monto = float(datos.get("monto", 0))
            tasa_ea = float(datos.get("tasa_ea", 0))
            plazo = int(datos.get("plazo", 0))
        else:
            monto = float(request.args.get("monto", 0))
            tasa_ea = float(request.args.get("tasa_ea", 0))
            plazo = int(request.args.get("plazo", 0))

        if monto <= 0 or tasa_ea <= 0 or plazo <= 0:
            return jsonify({"error": "Parámetros inválidos. Deben ser mayores a cero."}), 400
        if tasa_ea > 100:
            return jsonify({"error": "La tasa E.A. no puede superar el 100%."}), 400
        if plazo > 480:
            return jsonify({"error": "El plazo máximo es 480 meses (40 años)."}), 400

        tasa_ea_decimal = tasa_ea / 100.0
        tasa_mv_decimal = math.pow(1.0 + tasa_ea_decimal, 1.0 / 12.0) - 1.0
        tasa_mv = tasa_mv_decimal * 100.0
        i = tasa_mv_decimal

        if i == 0:
            cuota = monto / plazo
        else:
            cuota = (monto * i) / (1 - math.pow(1.0 + i, -plazo))

        tabla = []
        saldo_pendiente = monto

        for mes in range(1, plazo + 1):
            if mes == plazo:
                capital = saldo_pendiente
                interes = saldo_pendiente * i
                cuota_real = capital + interes
                saldo_pendiente_nuevo = 0.0
            else:
                interes_normal = saldo_pendiente * i
                capital_normal = cuota - interes_normal
                capital = capital_normal
                interes = interes_normal
                cuota_real = cuota
                saldo_pendiente_nuevo = saldo_pendiente - capital

            tabla.append({
                "mes": mes,
                "cuota": round(cuota_real, 2),
                "interes": round(interes, 2),
                "capital": round(capital, 2),
                "saldo": round(max(0.0, saldo_pendiente_nuevo), 2)
            })
            saldo_pendiente = saldo_pendiente_nuevo

        total_interes = sum(row["interes"] for row in tabla)

        return jsonify({
            "monto": monto,
            "tasa_ea": tasa_ea,
            "tasa_mv": round(tasa_mv, 4),
            "plazo": plazo,
            "cuota_mensual": round(cuota, 2),
            "total_interes": round(total_interes, 2),
            "tabla": tabla
        })

    except ValueError:
        return jsonify({"error": "Los datos deben ser numéricos."}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
