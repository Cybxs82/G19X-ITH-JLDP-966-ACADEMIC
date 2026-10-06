# Plataforma CFO

Dashboard Next.js con API FastAPI para la plataforma de inteligencia financiera (ejecución local).

## Arquitectura

El backend sigue una separación MVC modular:

```text
backend/
	controllers/     Controladores HTTP y rutas FastAPI
	models/          Schemas y contratos de entrada/salida
	repositories/    Persistencia y consultas PostgreSQL
	services/        Ingestion, normalizacion y reglas de negocio
	infrastructure/  Configuracion y conexion a PostgreSQL
```

El frontend mantiene sus responsabilidades separadas en `controllers/`, `models/` y `views/`. `main.py` funciona como composition root: configura FastAPI, registra middleware y conecta el controlador con el repositorio PostgreSQL.

---

## ⚠️ Configuración Obligatoria de Base de Datos y `.env`

Antes de ejecutar la plataforma, **es necesario utilizar el esquema de base de datos (`schema.sql`) y cambiar los valores del archivo `.env`** para que el proyecto se conecte correctamente a tu instancia local de PostgreSQL (15+):

1. **Crear la base de datos y aplicar el esquema (`schema.sql`):**
   ```powershell
   psql -U postgres -c "CREATE DATABASE todo_plataforma_cfo;"
   psql -U postgres -d todo_plataforma_cfo -f schema.sql
   ```

2. **Modificar los valores del archivo `.env`:**
   Edita el archivo `.env` en la raíz del proyecto con las credenciales reales de tu PostgreSQL local:
   ```env
   CFO_DATABASE_URL=postgresql+psycopg2://USUARIO:CONTRASENA@localhost:5432/todo_plataforma_cfo
   CFO_ENABLE_DEMO_DATA=false
   CFO_SECURE_SESSION_COOKIE=false
   ```
   *(Para ejecución local por HTTP, mantén `CFO_SECURE_SESSION_COOKIE=false`).*

---

## Backend FastAPI

El punto de entrada es [`main.py`](main.py). La API expone documentación OpenAPI en `/docs` y estos recursos bajo `/api/v1`:

- `GET /dashboard`: resumen con KPIs, forecast, alertas y recomendaciones.
- `GET /kpis`: KPIs filtrables por periodo.
- `GET /forecast?days=90`: proyección de flujo de caja a 30, 60 o 90 días.
- `GET /alerts` y `PATCH /alerts/{id}`: consulta y atención de alertas.
- `GET /recommendations` y `POST /feedback`: recomendaciones y feedback del CFO.
- `POST /sync`: registro de una corrida de sincronización.
- `POST /ingestion/files?source_type=erp`: carga automatizada de archivos `.xlsx`, `.csv` o `.pdf`.
- `POST /ingestion/documents`: carga autenticada de documentos ERP PDF, CSV o Excel; conserva el texto/payload extraído en staging sin normalizarlo ni recalcular KPIs.
- `POST /ingestion/budgets`: carga autenticada de presupuesto ERP CSV/Excel con periodo, monto presupuestado, cuenta y centro de costo.
- `GET /health`: health check.

El MVP requiere importar movimientos bancarios y presupuestos para calcular desviaciones. El forecast usa regresión lineal diaria, se habilita con al menos 180 días recientes de movimientos bancarios y reporta un intervalo predictivo del 80 % y MAE de backtest a 30 días. Sin datos suficientes, la API devuelve una serie vacía. Los movimientos netos bancarios no se presentan como saldo de caja porque aún no se captura el saldo inicial.

La conexión PostgreSQL usa `psycopg2` y se verifica con `SELECT 1` desde `GET /health`. La Fase 2 conserva el archivo recibido en `datos_temporales_erp` o `datos_temporales_banco`, normaliza cuentas, centros de costo y transacciones, registra filas rechazadas en `registros_sincronizacion_rechazados` y recalcula los KPIs desde `transacciones`. Si no hay transacciones cargadas, la aplicación mantiene el seed demo como fallback de desarrollo. No se guardan credenciales en el código.

### Ejecutar la API

```powershell
py -3.8 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000
```

La API queda disponible en `http://localhost:8000` y su contrato interactivo en `http://localhost:8000/docs`. Si PostgreSQL no está levantado, FastAPI arranca igualmente y `/health` reporta `database: unavailable`.

---

## Frontend (Next.js)

En una segunda terminal, instala las dependencias y levanta el servidor de desarrollo local:

```bash
npm install
npm run dev
```

Abre [http://localhost:3000](http://localhost:3000) en tu navegador e **inicia sesión**.

---

## 📂 Importación de Datos de Prueba (Carpeta `datos/`)

En la **carpeta raíz del proyecto** hay una carpeta llamada **`datos/`** donde se encuentran los documentos listos para la prueba de importación de datos dentro del proyecto. **Se impulsa a usarlos sí o sí para el correcto funcionamiento y demostración del proyecto.**

### Pasos para importar (después de iniciar sesión):
1. Ya habiendo iniciado sesión y estando dentro del proyecto en `http://localhost:3000`, dirígete a la vista **Carga ERP**.
2. Selecciona **ERP**, **Banco** o **Presupuesto**.
3. Para probar y demostrar el MVP con los ejemplos incluidos en la carpeta **`datos/`**, carga **sí o sí**:
   - **Primero:** [`datos/erp_datasheet_50_lineas.csv`](datos/erp_datasheet_50_lineas.csv) (como tipo **ERP**).
   - **Después:** [`datos/presupuesto_template.csv`](datos/presupuesto_template.csv) (como tipo **Presupuesto**).

También puedes realizar la importación de los archivos de la carpeta `datos/` por terminal o vía API multipart:

```powershell
.\.venv\Scripts\python.exe scripts\ingest_financial_files.py .\datos\erp_datasheet_50_lineas.csv --source-type erp
.\.venv\Scripts\python.exe scripts\ingest_financial_files.py .\datos\presupuesto_template.csv --source-type presupuesto
```

```powershell
curl.exe -X POST "http://localhost:8000/api/v1/ingestion/files?source_type=erp" -F "file=@.\datos\erp_datasheet_50_lineas.csv"
```

### Estructura de los archivos
- **Excel/CSV (ERP y Banco):** Deben incluir al menos `fecha` y `monto`. Se reconocen también `cuenta`, `nombre_cuenta`, `categoria`, `centro_costo`, `concepto`, `referencia` y `moneda`.
- **Presupuesto (CSV/Excel):** Debe incluir `periodo`, `monto_presupuestado`, `cuenta` y `centro_costo`.
- **PDF:** Se procesan mediante texto extraíble y requieren filas con `fecha` y `monto` legibles.
- Cada corrida crea un `sync_log`, conserva el payload original en staging y usa `source_type + source_reference` para evitar duplicados.
