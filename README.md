# Credit Intelligence Colombia

Sistema de consulta, comparación y seguimiento histórico de tasas de interés bancarias y de usura en Colombia.

## Características

- Consulta tasas de interés de bancos, nubancos y cooperativas colombianas
- Obtiene la tasa de usura vigente por modalidad de crédito (SFC)
- Almacena todo en base de datos SQLite con historial completo
- Compara automáticamente las mejores tasas
- Genera simulaciones de crédito (sistema francés)
- Alerta cuando una entidad se acerca al límite legal de usura
- Muestra tendencias históricas en dashboard interactivo
- API REST para consulta de tasas actuales e históricas

## Stack

- **Backend**: Flask (Python 3), SQLite
- **Frontend**: HTML + CSS + JavaScript vanilla, Chart.js
- **ETL**: Pandas, Requests, BeautifulSoup4

## Instalación

```bash
python -m venv venv
venv\Scripts\activate      # Windows
pip install -r requirements.txt
python init_db.py           # Crear BD con datos semilla
python app.py               # Iniciar servidor en :5000
```

## Estructura del proyecto

```
├── app.py                      # Servidor Flask + API REST
├── init_db.py                  # Crear BD inicial desde schema.sql
├── database/
│   ├── schema.sql              # DDL completo + datos semilla
│   ├── migrate.py              # Migraciones automáticas del esquema
│   ├── db.py                   # Funciones de consulta a la BD
│   ├── etl_scraper.py          # Pipeline ETL (tasas bancarias + usura)
│   └── tasas.db                # Base de datos SQLite
├── scripts/
│   └── run_etl.py              # CLI para ejecutar ETL manualmente
├── scripts_admin/
│   ├── ver_tablas.py           # Ver estructura de todas las tablas
│   └── ver_datos.py            # Ver contenido de todas las tablas
├── static/
│   ├── css/style.css
│   ├── js/main.js
│   └── img/
└── templates/
    ├── index.html
    ├── comparar.html
    ├── calculadora.html
    └── dashboard.html
```

## API REST

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/tasas` | GET | Tasas vigentes de todos los productos |
| `/api/indicadores` | GET | Indicadores de mercado (usura, DTF) |
| `/api/historial` | GET | Historial de tasas bancarias |
| `/api/historial/usura` | GET | Historial de tasas de usura e indicadores |
| `/api/amortizacion` | GET/POST | Simulación de crédito (sistema francés) |

## Pipeline ETL

### Ejecución manual

```bash
python scripts/run_etl.py
```

### Programación automática (schedulers)

**Windows (Task Scheduler):**
```
Acción: Iniciar programa
Programa: python
Argumentos: C:\ruta\proyecto\scripts\run_etl.py
Directorio: C:\ruta\proyecto
Frecuencia: Diaria a las 6:00
```

**Linux (cron):**
```
0 6 * * * cd /ruta/proyecto && python scripts/run_etl.py
```

**GitHub Actions (`.github/workflows/etl.yml`):**
```yaml
name: ETL Diario
on:
  schedule:
    - cron: '0 6 * * *'
  workflow_dispatch:
jobs:
  etl:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.x'
      - run: pip install -r requirements.txt
      - run: python scripts/run_etl.py
```

**Celery Beat:**
```python
from celery import Celery
from database.etl_scraper import correr_etl

app = Celery('credit_intelligence', broker='redis://localhost')

@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(86400.0, correr_etl.s(), name='etl-diario')
```

### ¿Qué hace el ETL?

1. **Tasas bancarias**: Extrae tasas de los productos financieros, las valida (rango 0-100% EA, datos numéricos, sin duplicados), calcula tasa MV, actualiza la tabla `tasas` (vigentes) e inserta en `historico_tasas`.
2. **Tasas de usura**: Extrae indicadores de usura por modalidad de crédito desde la Superintendencia Financiera de Colombia, actualiza `indicadores` (vigentes) e inserta en `historico_indicadores`.
3. **Logs**: Cada ejecución queda registrada en `sync_logs` con estado, fecha y detalles.

### Validaciones de calidad

- Tasas numéricas mayores a 0 y menores a 100% EA
- NIT de banco debe existir en la tabla `bancos`
- Producto debe existir para el banco correspondiente
- No duplicados históricos: mismo producto + misma fecha no se inserta dos veces
- No duplicados de usura: mismo indicador + misma vigencia no se inserta dos veces
- Errores registrados en `sync_logs` sin romper la aplicación

### Verificar que funcionó

```bash
# Consultar logs de sincronización
python -c "import sqlite3; conn = sqlite3.connect('database/tasas.db'); [print(r) for r in conn.execute('SELECT fecha_ejecucion, estado, registros_procesados, detalles FROM sync_logs ORDER BY fecha_ejecucion DESC LIMIT 5')]"

# Consultar histórico de tasas
python -c "import sqlite3; conn = sqlite3.connect('database/tasas.db'); [print(r) for r in conn.execute('SELECT fecha_registro, COUNT(*) FROM historico_tasas GROUP BY fecha_registro ORDER BY fecha_registro DESC LIMIT 10')]"

# Consultar histórico de usura
python -c "import sqlite3; conn = sqlite3.connect('database/tasas.db'); [print(r) for r in conn.execute('SELECT fecha_consulta, nombre, valor FROM historico_indicadores ORDER BY fecha_consulta DESC LIMIT 10')]"

# Ver estado desde la API
curl http://localhost:5000/api/historial/usura
```

## Base de datos

### Tablas

| Tabla | Propósito |
|-------|-----------|
| `bancos` | Entidades financieras (23 registros) |
| `categorias_credito` | Modalidades de crédito SFC (12 registros) |
| `fuentes` | Fuentes oficiales de cada entidad (24 registros) |
| `productos` | Productos financieros por banco (24 registros) |
| `tasas` | Tasas vigentes (1 por producto) |
| `historico_tasas` | Historial de tasas bancarias con fecha |
| `indicadores` | Tasas de usura e indicadores vigentes |
| `historico_indicadores` | Historial de usura con fecha de consulta |
| `sync_logs` | Registro de ejecuciones ETL |
| `schema_migrations` | Control de versiones del esquema |

### Scripts de administración

```bash
python scripts_admin/ver_tablas.py   # Ver estructura de todas las tablas
python scripts_admin/ver_datos.py    # Ver contenido de todas las tablas
python scripts/run_etl.py            # Ejecutar ETL manualmente
```
