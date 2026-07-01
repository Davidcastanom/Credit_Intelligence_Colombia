"""
CLI para ejecutar el pipeline ETL de Credit Intelligence Colombia.

USO:
    python scripts/run_etl.py                    # Ejecutar ETL completo
    python scripts/run_etl.py --help              # Ver ayuda

FRECUENCIA RECOMENDADA:
    La SFC publica el certificado de tasas de interés mensualmente,
    generalmente durante la primera semana de cada mes.


    Se recomienda ejecutar este script apenas se publique el nuevo certificado.

PROGRAMACIÓN AUTOMÁTICA:

    A) Windows (Programador de tareas) - RECOMENDADO para este servidor:
       1. Abrir "Programador de tareas" (Taskschd.msc)
       2. "Crear tarea básica" -> Nombre: "CIC ETL Mensual"
       3. Desencadenador: "Mensualmente", día 5 a las 8:00 AM
          (dar margen para que SFC publique el certificado)
       4. Acción: "Iniciar un programa"
          - Programa: python
          - Argumentos: scripts\run_etl.py
          - Iniciar en: C:/ruta/completa/del/proyecto
       5. Marcar "Ejecutar con privilegios más altos" si hay permisos

    B) Linux (cron):
       # Ejecutar el día 5 de cada mes a las 8:00 AM
       0 8 5 * * cd /ruta/proyecto && python scripts/run_etl.py >> logs/etl.log 2>&1

    C) GitHub Actions (cloud):
       El archivo .github/workflows/etl.yml ya está configurado.
       - Se ejecuta automáticamente el día 1 de cada mes a las 6:00 AM UTC
       - También se puede ejecutar manualmente desde Actions > ETL Diario > Run workflow

    D) Manual (con aviso en el panel admin):
       Desde el panel de administración (/admin/), hay un enlace
       a la gestión manual de tasas de usura si la automatización falla.

CONFIGURACIÓN:
    ADMIN_PASSWORD=mi_clave     # Contraseña para /admin/ (opcional, default: admin123)
    FLASK_SECRET_KEY=mi_secreto # Clave secreta de Flask (opcional)

EXIT CODES:
    0 = éxito
    1 = error
"""
import sys
import os
# Forzar UTF-8 en stdout/stderr (Windows cp1252)
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.etl_scraper import correr_etl


def main():
    print("Credit Intelligence Colombia - ETL")
    print(f"Directorio base: {os.getcwd()}")
    print()

    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        sys.exit(0)

    codigo = correr_etl()

    print()
    if codigo == 0:
        print("ETL finalizó correctamente.")
    else:
        print("ETL finalizó con errores.")
    sys.exit(codigo)


if __name__ == "__main__":
    main()
