# Credit Intelligence Colombia

Sistema de consulta, comparación, simulación y seguimiento de tasas de interés bancarias y usura en Colombia. Incluye alertas de proximidad al límite legal, dashboard interactivo con históricos, calculadora de crédito (sistema francés), y panel administrativo.

**URL:** [https://credit-intelligence-colombia-1.onrender.com](https://credit-intelligence-colombia-1.onrender.com)

---

## Características

- **Comparador de tasas** — Explora y filtra las tasas de más de 20 entidades financieras (bancos tradicionales, nubancos, cooperativas). Incluye tooltips informativos, columna de **Riesgo Usura** y toggle para mostrar/ocultar columnas.
- **Calculadora de crédito (sistema francés)** — Simula cuotas fijas mensuales con tabla de amortización completa. Descarga CSV con resumen del crédito + desglose mes a mes. Alerta si la tasa supera o se acerca al límite de usura.
- **Dashboard estadístico** — KPIs con contadores animados, gráfico de barras con gradientes y línea de usura, evolución histórica por banco, histórico de usura por modalidad, y tabla de alertas activas (críticas en rojo, preventivas en naranja).
- **Alertas de usura** — Detecta automáticamente los productos cuya tasa está a menos de 1 % (crítica) o menos de 3 % (preventiva) del techo legal.
- **Inicio educativo** — Explica qué es la usura, cómo se calcula, para quién es la herramienta, casos de uso prácticos y preguntas frecuentes con acordeón interactivo.
- **Inicio de sesión con Google** — Opcional. Activado con la variable `GOOGLE_CLIENT_ID`. Oculta completamente la interfaz de login si no está configurada.
- **Panel administrativo** — Protegido con contraseña (`ADMIN_PASSWORD`). Permite editar tasas de usura, gestionar usuarios, ver logs de sincronización y enviar notificaciones.
- **ETL automatizado** — Extrae tasas bancarias e indicadores de usura desde la API de datos.gov.co (Socrata). Sin fallback: si la API falla, el pipeline se detiene. Validación estricta con detección de anomalías.
- **Exportación CSV** — Compatible con Excel (locale español: separador `;`, decimal `,`). Descarga simulaciones con resumen completo y tablas de amortización. Descarga históricos de tasas y usura desde el dashboard.
- **Diseño responsive** — Menú hamburguesa en mobile, tablas adaptativas (ocultan columnas secundarias), KPIs en grilla de 2 columnas, gráficos compactos.

---

## Stack

| Capa | Tecnología |
|------|-----------|
| Backend | Flask (Python 3), PostgreSQL / SQLite |
| Frontend | HTML + CSS vanilla + JavaScript, Chart.js |
| ETL | Pandas, Requests (Socrata API), validación estadística |
| Auth | Google OAuth 2.0 (opcional) |
| Despliegue | Render (free tier), Gunicorn |
| CI/CD | GitHub Actions (cron mensual) |

---

## Instalación local

### Requisitos

- Python 3.12+
- Opcional: PostgreSQL (para probar el adapter en modo producción)

### Paso a paso

```bash
git clone https://github.com/Davidcastanom/Credit_Intelligence_Colombia.git
cd Credit_Intelligence_Colombia
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac
pip install -r requirements.txt
```

### Inicializar base de datos

Por defecto usa SQLite local (`database/tasas.db`). Las migraciones se ejecutan automáticamente al iniciar la app o el ETL.

```bash
python database/migrate.py      # Crea esquema + datos semilla
python scripts/run_etl.py       # Poblado inicial desde datos.gov.co
python app.py                   # Servidor en http://localhost:5000
```

### Probar con PostgreSQL (opcional)

```bash
# Define la URL de conexión
export DATABASE_URL="postgresql://usuario:password@localhost:5432/credit_intelligence"

# Todo funciona igual — el adapter detecta DATABASE_URL automáticamente
python scripts/run_etl.py
python app.py
```

### Verificar integridad

```bash
python scripts/test_integridad.py
# 27 pruebas: conectividad API, parseo, validación, extracción real, BD
```

---

## Variables de entorno

| Variable | Obligatoria | Descripción |
|----------|-------------|-------------|
| `DATABASE_URL` | No | URL de PostgreSQL. Si se omite, usa SQLite local |
| `FLASK_SECRET_KEY` | Sí | Secreto de sesión Flask |
| `ADMIN_PASSWORD` | No | Contraseña del panel admin. Si no se define, se genera una aleatoria |
| `GOOGLE_CLIENT_ID` | No | Client ID de Google OAuth. Si no se define, el login se oculta |
| `GOOGLE_CLIENT_SECRET` | No | Secret de Google OAuth |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASS` | No | Para envío de notificaciones por correo |
| `ADMIN_ALLOWED_IPS` | No | Restricción por IP/CIDR para el panel admin |

---

## Estructura del proyecto

```
├── app.py                         # Servidor Flask + API REST + admin + OAuth
├── Procfile                       # gunicorn para Render
├── requirements.txt               # Dependencias
├── .env.example                   # Plantilla de variables de entorno
├── database/
│   ├── db_adapter.py              # Adapter PostgreSQL/SQLite automático
│   ├── db.py                      # Consultas a la BD (usa db_adapter)
│   ├── migrate.py                 # Migraciones automáticas (10 versiones)
│   └── etl_scraper.py             # Pipeline ETL con Socrata API + validación
├── scripts/
│   ├── run_etl.py                 # CLI para ejecutar ETL manual
│   └── test_integridad.py         # Suite de pruebas de integridad (27 tests)
├── scripts_admin/
│   ├── ver_tablas.py              # Inspeccionar estructura de tablas
│   └── ver_datos.py               # Inspeccionar contenido de tablas
├── static/
│   ├── css/style.css
│   ├── js/main.js
│   ├── favicon.svg / favicon.png / favicon.ico
│   └── img/
├── templates/
│   ├── index.html                 # Inicio educativo + FAQ + casos de uso
│   ├── comparar.html              # Comparador de tasas
│   ├── calculadora.html           # Simulador de crédito
│   ├── dashboard.html             # Dashboard con gráficos y alertas
│   └── admin/
│       ├── login.html             # Login del panel admin
│       ├── dashboard.html         # Admin dashboard
│       ├── usura.html             # Editor de tasas de usura
│       └── notificar.html         # Envío de notificaciones
└── .github/workflows/
    └── etl.yml                    # ETL automático (día 1 de cada mes)
```

---

## ETL — Pipeline de datos

### Fuente de datos

**100% datos abiertos del gobierno colombiano** — sin scraping PDF, sin fallback.

| Dataset | API | Contenido |
|---------|-----|-----------|
| Tasas bancarias | `w9zh-vetq` | Tasas de interés promedio por entidad y producto |
| TIBC | `pare-7x5i` | Tasas de Interés Bancario Corriente por modalidad |
| Usura | derivado | Usura = TIBC × 1.5 (por ley) |

### Proceso

```bash
python scripts/run_etl.py
```

1. **Extracción** — Consulta las APIs de datos.gov.co con `$group` y `$where` para obtener las tasas del mes vigente.
2. **Limpieza** — `limpiar_tasa()`: elimina `*`, espacios, `$`, `%`, unicode basura, normaliza comas decimales.
3. **Validación de rango** — `validar_rango_tasa_ea()`: rechaza valores fuera de 0.0–100.0% EA, NaN, Inf.
4. **Detección de anomalías** — `validar_saltos_tasas()` / `validar_saltos_usura()`: compara contra el último valor en BD; si el cambio supera el 15%, el registro se bloquea con un log.
5. **Carga** — Actualiza `tasas` e `indicadores` (UPSERT) e inserta en `historico_tasas` / `historico_indicadores`.
6. **Log** — Cada ejecución se registra en `sync_logs` con estado, fecha, cantidad de registros y detalles.

### Validaciones de calidad

- Tasas entre 0 y 100 % EA (usura permite hasta 200%)
- Limpieza caracteres: asteriscos, comas, espacios, símbolos monetarios
- Detección de saltos anómalos > 15% mes a mes
- NIT del banco debe existir en `bancos`
- Producto debe pertenecer al banco
- Sin duplicados históricos
- Errores registrados sin datos fabricados — `ExtractionError` detiene el pipeline

### Automatización

**GitHub Actions** (`.github/workflows/etl.yml`):
```yaml
schedule:
  - cron: '0 10 1 * *'   # Día 1 de cada mes, 10:00 UTC
workflow_dispatch:         # También ejecución manual desde Actions
```

Requiere el secreto `DATABASE_URL` configurado en GitHub → Settings → Secrets and variables → Actions.

**Linux (cron):**
```cron
0 10 1 * * cd /ruta/proyecto && DATABASE_URL="postgresql://..." python scripts/run_etl.py >> logs/etl.log 2>&1
```

### Verificar estado

```bash
curl https://credit-intelligence-colombia-1.onrender.com/api/sync/status
```

---

## Base de datos

### Adapter automático (`database/db_adapter.py`)

El adapter `Conexion()` detecta automáticamente el motor según la variable `DATABASE_URL`:

| `DATABASE_URL` | Motor |
|----------------|-------|
| Definida | PostgreSQL (`psycopg2`) |
| Ausente | SQLite local (`database/tasas.db`) |

Todas las consultas SQL se traducen automáticamente: `?` → `%s`, `INSERT OR IGNORE` → `ON CONFLICT DO NOTHING`, `INTEGER PRIMARY KEY AUTOINCREMENT` → `SERIAL PRIMARY KEY`, etc.

### Tablas

| Tabla | Propósito |
|-------|-----------|
| `bancos` | Entidades financieras (23 registros) |
| `categorias_credito` | Modalidades de crédito SFC (12 registros) |
| `fuentes` | Fuentes oficiales de cada entidad |
| `productos` | Productos financieros por banco (52 registros) |
| `tasas` | Tasas vigentes (1 por producto) |
| `historico_tasas` | Historial de tasas bancarias con fecha |
| `indicadores` | Tasas de usura e indicadores vigentes (10: 9 usura + DTF) |
| `historico_indicadores` | Historial de usura con fecha de consulta |
| `sync_logs` | Registro de ejecuciones ETL |
| `schema_migrations` | Control de versiones del esquema (10 migraciones) |
| `usuarios` | Usuarios registrados vía Google OAuth |
| `notificaciones` | Notificaciones enviadas a usuarios |

---

## Despliegue en Render

### 1. Crear servicio Web

- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn app:app` (definido en `Procfile`)

### 2. Crear base de datos PostgreSQL

Desde el Dashboard de Render: New → PostgreSQL. Se crea automáticamente la variable `DATABASE_URL` en el servicio web vinculado.

### 3. Variables de entorno

| Variable | Descripción |
|----------|-------------|
| `DATABASE_URL` | Se inyecta automáticamente al vincular la BD PostgreSQL |
| `FLASK_SECRET_KEY` | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `ADMIN_PASSWORD` | Tu contraseña para el panel admin |
| `GOOGLE_CLIENT_ID` | (Opcional) Para login con Google |
| `GOOGLE_CLIENT_SECRET` | (Opcional) Para login con Google |

### 4. Ejecutar ETL inicial

```bash
# Desde Render Shell
python scripts/run_etl.py
```

### 5. Programar ETL automático

Agregar el secreto `DATABASE_URL` en GitHub:
```
Settings → Secrets and variables → Actions → New repository secret
Name: DATABASE_URL
Value: postgresql://user:pass@host:5432/db
```

El workflow de GitHub Actions lo ejecutará el día 1 de cada mes.

---

## Test de integridad

```bash
python scripts/test_integridad.py
```

Ejecuta 27 pruebas que verifican:

1. Conectividad a los endpoints de datos.gov.co (w9zh-vetq + pare-7x5i)
2. Parseo correcto de los campos JSON del Socrata API
3. Limpieza y conversión de tasas (comas, asteriscos, símbolos)
4. Validación de rango (0.0–100.0% EA)
5. Extracción real de 16 tasas bancarias + 9 indicadores de usura
6. Inserción y consistencia en base de datos

---

## API REST

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/tasas` | GET | Tasas vigentes de todos los productos financieros |
| `/api/indicadores` | GET | Indicadores de mercado (tasas de usura por modalidad) |
| `/api/historial` | GET | Historial de tasas bancarias |
| `/api/historial/usura` | GET | Historial de tasas de usura e indicadores |
| `/api/amortizacion?monto=X&tasa_ea=Y&plazo=Z` | GET | Simulación de crédito (sistema francés) |
| `/api/sync/status` | GET | Estado de la última sincronización ETL |
| `/api/auth/google` | POST | Autenticación con Google OAuth |
| `/api/auth/me` | GET | Perfil del usuario autenticado |

---

## Scripts de administración

```bash
python database/migrate.py              # Ejecutar migraciones pendientes
python scripts/run_etl.py               # Ejecutar ETL manual
python scripts/test_integridad.py       # Suite de verificación (27 tests)
python scripts_admin/ver_tablas.py      # Ver estructura de tablas
python scripts_admin/ver_datos.py       # Ver contenido de tablas
```

---

## Licencia

Datos de tasas con fines ilustrativos y analíticos. Fuente oficial: [Superintendencia Financiera de Colombia](https://www.datos.gov.co/Econom-a-y-Finanzas/Certificado-de-Tasas-de-Inter-s-Bancario-Corriente/pare-7x5i) y [datos.gov.co](https://www.datos.gov.co/Econom-a-y-Finanzas/Tasas-de-inter-s-promedio-por-entidad-y-producto/w9zh-vetq).
