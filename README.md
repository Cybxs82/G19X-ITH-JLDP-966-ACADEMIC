# Plataforma CFO

Dashboard Next.js con API FastAPI para la plataforma de inteligencia financiera.

## Arquitectura

El backend sigue una separacion MVC modular:

```text
backend/
	controllers/     Controladores HTTP y rutas FastAPI
	models/          Schemas y contratos de entrada/salida
	repositories/    Persistencia y consultas PostgreSQL
	services/        Ingestion, normalizacion y reglas de negocio
	infrastructure/  Configuracion y conexion a PostgreSQL
```

El frontend mantiene sus responsabilidades separadas en `controllers/`, `models/` y `views/`. `main.py` funciona como composition root: configura FastAPI, registra middleware y conecta el controlador con el repositorio PostgreSQL.

## Backend FastAPI

El punto de entrada es [`main.py`](main.py). La API expone documentacion OpenAPI en `/docs` y estos recursos bajo `/api/v1`:

- `GET /dashboard`: resumen con KPIs, forecast, alertas y recomendaciones.
- `GET /kpis`: KPIs filtrables por periodo.
- `GET /forecast?days=90`: proyeccion de flujo de caja a 30, 60 o 90 dias.
- `GET /alerts` y `PATCH /alerts/{id}`: consulta y atencion de alertas.
- `GET /recommendations` y `POST /feedback`: recomendaciones y feedback del CFO.
- `POST /sync`: registro de una corrida de sincronizacion.
- `POST /ingestion/files?source_type=erp`: carga automatizada de archivos `.xlsx`, `.csv` o `.pdf`.
- `POST /ingestion/documents`: carga autenticada de documentos ERP PDF, CSV o Excel; conserva el texto/payload extraído en staging sin normalizarlo ni recalcular KPIs.
- `GET /health`: health check.

La conexion PostgreSQL usa `psycopg2` y se verifica con `SELECT 1` desde `GET /health`. La Fase 2 conserva el archivo recibido en `datos_temporales_erp` o `datos_temporales_banco`, normaliza cuentas, centros de costo y transacciones, registra filas rechazadas en `registros_sincronizacion_rechazados` y recalcula los KPIs desde `transacciones`. Si no hay transacciones cargadas, la aplicacion mantiene el seed demo como fallback de desarrollo. No se guardan credenciales en el codigo.

### Carga automatizada de datos

La carga batch no requiere captura manual:

```powershell
.\.venv\Scripts\python.exe scripts\ingest_financial_files.py .\datos\erp.xlsx --source-type erp
.\.venv\Scripts\python.exe scripts\ingest_financial_files.py .\datos\movimientos-banco.pdf --source-type banco
```

Tambien puede usarse la API multipart:

```powershell
curl.exe -X POST "http://localhost:8000/api/v1/ingestion/files?source_type=erp" -F "file=@.\datos\erp.xlsx"
```

Los Excel/CSV deben incluir al menos `fecha` y `monto`. Se reconocen tambien `cuenta`, `nombre_cuenta`, `categoria`, `centro_costo`, `concepto`, `referencia` y `moneda`. Los PDF se procesan mediante texto extraible y requieren filas con fecha y monto legibles. Cada corrida crea un `sync_log`, conserva el payload original en staging y usa `source_type + source_reference` para evitar duplicados.

### Ejecutar la API

```powershell
py -3.8 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000
```

Antes de iniciar, edita `.env` con los datos reales de tu PostgreSQL:

```env
CFO_DATABASE_URL=postgresql+psycopg2://USUARIO:CONTRASENA@HOST:5432/NOMBRE_BASE
```

La API queda disponible en `http://localhost:8000` y su contrato interactivo en `http://localhost:8000/docs`. Si PostgreSQL no está levantado, FastAPI arranca igualmente y `/health` reporta `database: unavailable`.

## Frontend

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
