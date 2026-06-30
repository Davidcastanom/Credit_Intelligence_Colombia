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
- **ETL automatizado** — Extrae tasas bancarias e indicadores de usura. Ejecutable manualmente, vía GitHub Actions (programación mensual), o mediante cron/Task Scheduler.
- **Exportación CSV** — Compatible con Excel (locale español: separador `;`, decimal `,`). Descarga simulaciones con resumen completo y tablas de amortización. Descarga históricos de tasas y usura desde el dashboard.
- **Diseño responsive** — Menú hamburguesa en mobile, tablas adaptativas (ocultan columnas secundarias), KPIs en grilla de 2 columnas, gráficos compactos.

---

## Stack

| Capa | Tecnología |
|------|-----------|
| Backend | Flask (Python 3), SQLite |
| Frontend | HTML + CSS vanilla + JavaScript, Chart.js |
| ETL | Pandas, Requests, pdfplumber |
| Auth | Google OAuth 2.0 (opcional) |
| Despliegue | Render (free tier), Gunicorn |

---

## Instalación local

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# ó: source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
python database/migrate.py      # Crea esquema + datos semilla (52 productos, 7 indicadores)
python app.py                   # Servidor en http://localhost:5000
```

### Variables de entorno (`.env`)

| Variable | Obligatoria | Descripción |
|----------|-------------|-------------|
| `FLASK_SECRET_KEY` | Sí | Secreto de sesión Flask |
| `ADMIN_PASSWORD` | No | Contraseña del panel admin. Si no se define, se genera una aleatoria mostrada al iniciar |
| `GOOGLE_CLIENT_ID` | No | Client ID de Google OAuth. Si no se define, el login con Google se oculta por completo |

---

## Estructura del proyecto

```
├── app.py                         # Servidor Flask + API REST + admin + OAuth
├── Procfile                       # Comando de inicio para Render
├── requirements.txt               # Dependencias
├── .env.example                   # Plantilla de variables de entorno
├── database/
│   ├── db.py                      # Consultas a la BD
│   ├── migrate.py                 # Migraciones automáticas (9 versiones)
│   └── etl_scraper.py             # Pipeline ETL (tasas bancarias + usura PDF)
├── scripts/
│   └── run_etl.py                 # CLI para ejecutar ETL manualmente
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
    └── etl.yml                    # ETL automático mensual
```

---

## Páginas principales

| Ruta | Descripción |
|------|-------------|
| `/` | Inicio con hero, características, segmentos de audiencia, FAQ, explicación de usura |
| `/comparar` | Tabla interactiva de tasas con filtros, ordenamiento, tooltips y toggle de columnas |
| `/calculadora` | Simulador de crédito (sistema francés) con tabla de amortización y exportación CSV |
| `/dashboard` | KPIs animados, gráficos (barras con línea de usura, históricos), alertas de riesgo |
| `/admin/login` | Acceso al panel administrativo (requiere `ADMIN_PASSWORD`) |
| `/api/tasas` | API REST — tasas vigentes |
| `/api/indicadores` | API REST — indicadores de mercado (usura, DTF) |
| `/api/amortizacion?monto=X&tasa_ea=Y&plazo=Z` | API REST — simulación de crédito |

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

---

## ETL — Pipeline de datos

### Ejecución manual

```bash
python scripts/run_etl.py
```

### Automatización

**GitHub Actions** (`.github/workflows/etl.yml`):
```yaml
name: ETL Mensual
on:
  schedule:
    - cron: '0 6 1 * *'   # 1er día de cada mes
  workflow_dispatch:        # también manual
```

### ¿Qué hace?

1. **Tasas bancarias** — Extrae, valida (rango 0–100 % EA, datos numéricos, sin duplicados) y actualiza tasas vigentes + histórico.
2. **Tasas de usura** — Descarga el certificado PDF de la SFC (o usa valores simulados como fallback), extrae tasas por modalidad y las guarda con fechas de vigencia.
3. **Logs** — Cada ejecución se registra en `sync_logs` con estado, fecha, cantidad de registros y detalles.

### Validaciones de calidad

- Tasas numéricas entre 0 y 100 % EA
- NIT de banco debe existir en `bancos`
- Producto debe pertenecer al banco
- Sin duplicados históricos (mismo producto + fecha)
- Sin duplicados de usura (mismo indicador + vigencia)
- Errores registrados sin romper la aplicación

### Verificar estado

```bash
curl https://credit-intelligence-colombia-1.onrender.com/api/sync/status
```

---

## Base de datos (SQLite)

### Tablas

| Tabla | Propósito |
|-------|-----------|
| `bancos` | Entidades financieras (23 registros) |
| `categorias_credito` | Modalidades de crédito SFC (12 registros) |
| `fuentes` | Fuentes oficiales de cada entidad |
| `productos` | Productos financieros por banco (52 registros) |
| `tasas` | Tasas vigentes (1 por producto) |
| `historico_tasas` | Historial de tasas bancarias con fecha |
| `indicadores` | Tasas de usura e indicadores vigentes |
| `historico_indicadores` | Historial de usura con fecha de consulta |
| `sync_logs` | Registro de ejecuciones ETL |
| `schema_migrations` | Control de versiones del esquema (9 migraciones) |
| `usuarios` | Usuarios registrados vía Google OAuth |
| `notificaciones` | Notificaciones enviadas a usuarios |

### Nota sobre persistencia

En Render (free tier), la base de datos SQLite **no persiste** entre reinicios. El archivo `database/tasas.db` se regenera desde cero en cada deploy. Las migraciones re-siembran productos (52) e indicadores (7) automáticamente al iniciar.

---

## Despliegue en Render

1. Crear servicio Web en Render
2. **Build Command:** `pip install -r requirements.txt`
3. **Start Command:** `gunicorn app:app`
4. **Variables de entorno:**
   - `FLASK_SECRET_KEY`
   - `ADMIN_PASSWORD` (opcional)
   - `GOOGLE_CLIENT_ID` (opcional)
5. Tras el deploy, ejecutar ETL manual desde Render Shell:
   ```bash
   python scripts/run_etl.py
   ```

> **Nota:** La URL actual es `credit-intelligence-colombia-1.onrender.com`. Render free tier duerme tras 15 min de inactividad — la primera visita tarda 5–15 s en despertar.

---

## Scripts de administración

```bash
python database/migrate.py          # Ejecutar migraciones pendientes
python scripts/run_etl.py           # Ejecutar ETL manual
python scripts_admin/ver_tablas.py  # Ver estructura de tablas
python scripts_admin/ver_datos.py   # Ver contenido de tablas
```

---

## Licencia

Datos de tasas con fines ilustrativos y analíticos. Fuente oficial: [Superintendencia Financiera de Colombia](https://www.superfinanciera.gov.co/publicaciones/10115837/seguimiento-a-la-tibc/).
