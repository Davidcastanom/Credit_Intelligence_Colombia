# Credit Intelligence Colombia

Sistema de consulta, comparación, simulación y seguimiento de tasas de interés bancarias y usura en Colombia. Incluye alertas de proximidad al límite legal, dashboard interactivo con históricos, calculadora de crédito (sistema francés), y panel administrativo.

**URL:** [https://credit-intelligence-colombia-1.onrender.com](https://credit-intelligence-colombia-1.onrender.com)

---

## Características

- **Comparador de tasas** — Explora y filtra las tasas de 23 entidades financieras (bancos tradicionales, nubancos, cooperativas). Incluye tooltips, columna de **Riesgo Usura** y toggle de columnas.
- **Calculadora de crédito (sistema francés)** — Simula cuotas fijas con tabla de amortización completa. Descarga CSV compatible con Excel. Alerta si la tasa supera el límite de usura.
- **Dashboard estadístico** — KPIs (mejor tasa consumo, promedio mercado), gráfico de barras por entidad (coloreado por tipo), evolución histórica por banco, histórico de usura por modalidad y tabla de alertas activas.
- **Alertas de usura** — Detecta productos con tasa a menos de 1% (crítica) o 3% (preventiva) del techo legal.
- **Inicio educativo** — Explica qué es la usura, cómo se calcula, para quién es la herramienta, casos de uso y FAQ.
- **Inicio de sesión con Google** — Opcional (`GOOGLE_CLIENT_ID`). Se oculta si no está configurado.
- **Panel administrativo** — Protegido con `ADMIN_PASSWORD`. Editar tasas de usura, gestionar usuarios y ver logs de sincronización.
- **Auto-ETL al iniciar** — Al desplegar en Render, la app ejecuta migraciones + extracción desde datos.gov.co automáticamente sin intervención manual.
- **Actualización mensual** — GitHub Actions dispara un **Deploy Hook** de Render el día 1 de cada mes, forzando redeploy con ETL automático.
- **Exportación CSV** — Compatible con Excel (locale español: separador `;`, decimal `,`).
- **Diseño responsive** — Menú hamburguesa, tablas adaptativas, KPIs en grilla 2 columnas, gráficos compactos.

---

## Stack

| Capa | Tecnología |
|------|-----------|
| Backend | Flask (Python 3), PostgreSQL / SQLite |
| Frontend | HTML + CSS vanilla + JavaScript, Chart.js |
| ETL | Pandas, Requests (Socrata API), validación estadística |
| Auth | Google OAuth 2.0 (opcional) |
| Despliegue | Render (free tier), Gunicorn, auto-ETL al iniciar |
| CI/CD | GitHub Actions → Deploy Hook → Render redeploy |

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
├── app.py                         # Servidor Flask + API REST + admin + OAuth + auto-ETL
├── Procfile                       # gunicorn app:app (Render)
├── requirements.txt               # Dependencias
├── .env.example                   # Plantilla de variables de entorno
├── database/
│   ├── db_adapter.py              # Adapter PostgreSQL vía psycopg2 (DATABASE_URL) / SQLite fallback
│   ├── db.py                      # Consultas a la BD (usa db_adapter)
│   ├── migrate.py                 # Migraciones: INITIAL_SCHEMA para PG + datos semilla
│   └── etl_scraper.py             # Pipeline ETL con Socrata API + validación estadística
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

**100% datos abiertos del gobierno colombiano** — sin scraping PDF, sin fallback. Las tasas provienen de la [Superintendencia Financiera de Colombia](https://www.superfinanciera.gov.co/) a través de [datos.gov.co](https://www.datos.gov.co/).

| Dataset | ID API Socrata | Contenido |
|---------|----------------|-----------|
| Tasas bancarias | `w9zh-vetq` | Tasas de interés promedio por entidad y producto (16 bancos, ~52 productos) |
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

**GitHub Actions + Render Deploy Hook** (`.github/workflows/etl.yml`):
```yaml
schedule:
  - cron: '0 10 1 * *'   # Día 1 de cada mes, 10:00 UTC
workflow_dispatch:         # También ejecución manual desde Actions
```

El workflow llama al **Deploy Hook** de Render (`api.render.com/deploy/...`), lo que dispara un redeploy. Al reiniciar la app, el **auto-ETL** se ejecuta automáticamente (si el último sync tiene más de 1 día).

No se necesita configurar `DATABASE_URL` en GitHub — el pipeline nunca conecta a la BD directamente (Render free tier bloquea conexiones externas a PostgreSQL).

**Linux (cron alternativo):**
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

Todas las consultas SQL se traducen automáticamente: `?` → `%s`, `INSERT OR IGNORE` → `ON CONFLICT DO NOTHING` (solo para `INSERT ... VALUES`, no para `INSERT ... SELECT`), `INTEGER PRIMARY KEY AUTOINCREMENT` → `SERIAL PRIMARY KEY`, etc.

### Tablas

| Tabla | Propósito |
|-------|-----------|
| `bancos` | Entidades financieras (23 registros) con tipo_entidad (tradicional, nubanco, cooperativa) |
| `categorias_credito` | Modalidades de crédito SFC (12 registros) |
| `fuentes` | Fuentes oficiales (2 registros: SFC, Datos Abiertos) |
| `productos` | Productos financieros por banco (52 registros) |
| `tasas` | Tasas vigentes (1 por producto) |
| `historico_tasas` | Historial de tasas bancarias con fecha |
| `indicadores` | Tasas de usura e indicadores vigentes (10: 9 usura + DTF) |
| `historico_indicadores` | Historial de usura con fecha de consulta |
| `sync_logs` | Registro de ejecuciones ETL |
| `schema_migrations` | Control de versiones del esquema (INITIAL_SCHEMA para PostgreSQL + migraciones progresivas) |
| `usuarios` | Usuarios registrados vía Google OAuth |
| `notificaciones` | Notificaciones enviadas a usuarios |

---

## Despliegue en Render

> **Importante:** Render free tier PostgreSQL solo acepta conexiones internas (no expone puerto externo). El ETL se ejecuta automáticamente al iniciar la app, no desde GitHub Actions ni desde tu máquina local.

### 1. Crear servicio Web

- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn app:app` (definido en `Procfile`)

### 2. Crear base de datos PostgreSQL

Desde el Dashboard de Render: New → PostgreSQL. Luego ve a tu Web Service → Environment → **link to PostgreSQL**.

Esto inyecta automáticamente la variable `DATABASE_URL` con la URL de conexión interna.

### 3. Variables de entorno

| Variable | Descripción |
|----------|-------------|
| `DATABASE_URL` | Se inyecta automáticamente al vincular la BD PostgreSQL |
| `FLASK_SECRET_KEY` | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `ADMIN_PASSWORD` | Tu contraseña para el panel admin |
| `GOOGLE_CLIENT_ID` | (Opcional) Para login con Google |
| `GOOGLE_CLIENT_SECRET` | (Opcional) Para login con Google |

### 4. Auto-ETL al iniciar

No requiere acción manual. Al hacer deploy, la app ejecuta automáticamente:
1. Migraciones de esquema (crea tablas si no existen)
2. Poblado inicial (bancos, categorías, fuentes)
3. ETL desde datos.gov.co — consulta tasas bancarias e indicadores de usura

El ETL solo corre si la BD está vacía o el último sync tiene más de 1 día.

### 5. Programar ETL automático

1. Obtén el **Deploy Hook** de Render: Dashboard → `credit-intelligence-colombia-1` → Settings → Deploy Hook → copiar URL
2. Agrega el secreto en GitHub:
```
Settings → Secrets and variables → Actions → New repository secret
Name: RENDER_DEPLOY_HOOK
Value: https://api.render.com/deploy/srv-xxx?key=yyy
```

El workflow de GitHub Actions llamará al hook el día 1 de cada mes.

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

## Atribución de datos

Las tasas de interés mostradas provienen de la **Superintendencia Financiera de Colombia (SFC)** a través del portal de datos abiertos [datos.gov.co](https://www.datos.gov.co/). Los datasets utilizados son:

- [Tasas de interés promedio por entidad y producto](https://www.datos.gov.co/Econom-a-y-Finanzas/Tasas-de-inter-s-promedio-por-entidad-y-producto/w9zh-vetq) (`w9zh-vetq`)
- [Certificado de Tasas de Interés Bancario Corriente](https://www.datos.gov.co/Econom-a-y-Finanzas/Certificado-de-Tasas-de-Inter-s-Bancario-Corriente/pare-7x5i) (`pare-7x5i`)

La tasa de usura se calcula como **TIBC × 1.5** conforme a la normativa colombiana.

> **Importante:** Verifique siempre la tasa contratada directamente con su entidad financiera. Este sitio ofrece datos de referencia con fines ilustrativos y analíticos, no constituye asesoría financiera.

## Licencia

Datos de tasas con fines ilustrativos y analíticos.
