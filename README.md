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

## Backend FastAPI

El punto de entrada es [`main.py`](main.py). La API expone documentación OpenAPI en `/docs` y estos recursos bajo `/api/v1`:

- `GET /dashboard`: resumen con KPIs, forecast, alertas y recomendaciones; acepta `period_from`, `period_to`, `cost_center_id` y `horizon_days` (`30`, `60` o `90`).
- `GET /kpis`: KPIs filtrables por periodo.
- `GET /forecast?days=90`: proyección de flujo de caja a 30, 60 o 90 días.
- `GET /alerts` y `PATCH /alerts/{id}`: consulta y atención de alertas.
- `GET /recommendations`: consulta las recomendaciones guardadas sin generarlas; `POST /recommendations/generate`: las genera y persiste (solo CFO o administrador); `POST /feedback`: registra feedback del usuario. Las cargas y la eliminación de datos de práctica actualizan las recomendaciones. El dashboard consulta el endpoint GET para mostrarlas.
- `POST /sync`: registro de una corrida de sincronización.
- `POST /ingestion/files?source_type=erp`: carga automatizada de archivos `.xlsx`, `.csv` o `.pdf`.
- `POST /ingestion/documents`: carga autenticada de documentos ERP PDF, CSV o Excel; conserva el texto/payload extraído en staging sin normalizarlo ni recalcular KPIs.
- `POST /ingestion/budgets`: carga autenticada de presupuesto ERP CSV/Excel con periodo, monto presupuestado, cuenta y centro de costo.
- `DELETE /ingestion/practice-data`: elimina las cargas cuyo nombre de archivo inicia con `practica_` y actualiza los indicadores derivados.
- `GET /health`: health check.

El MVP requiere importar movimientos bancarios y presupuestos para calcular desviaciones. El forecast usa regresión lineal diaria sobre al menos 180 días de movimientos bancarios hasta `period_to` (el filtro `period_from` limita KPIs y alertas, pero no recorta el histórico necesario para proyectar). `horizon_days` determina si el endpoint devuelve 30, 60 o 90 días. Además de la serie diaria, la API entrega agregados mensuales con intervalos de predicción calculados para la suma del mes; el resultado es flujo neto estimado, no saldo de caja, porque aún no se captura el saldo inicial. El backend reporta intervalos predictivos del 80 % y MAE de backtest a 30 días. Sin histórico suficiente, la API devuelve series vacías.

El MVP ofrece resúmenes ejecutivos y recomendaciones sin IA generativa ni servicios de pago: se generan mediante reglas explicables a partir de alertas, KPIs y forecast calculados con datos reales, después de las cargas y de eliminar datos de práctica. Si faltan datos para una regla o el forecast no está disponible, el sistema lo indica en lugar de inventar cifras.

La conexión PostgreSQL usa `psycopg2` y se verifica con `SELECT 1` desde `GET /health`. La Fase 2 conserva el archivo recibido en `datos_temporales_erp` o `datos_temporales_banco`, normaliza cuentas, centros de costo y transacciones, registra filas rechazadas en `registros_sincronizacion_rechazados` y recalcula los KPIs desde `transacciones`. La carga del seed demo está desactivada por omisión (`CFO_ENABLE_DEMO_DATA=false`); puede habilitarse explícitamente para desarrollo. No se guardan credenciales en el código.

## Instalación desde cero

Sigue estos pasos en orden desde la raíz del proyecto. Necesitas PostgreSQL 15+, Python 3.11 y Node.js/npm.

1. **Crear la base de datos y aplicar el esquema.** En PowerShell:
   ```powershell
   psql -U postgres -c "CREATE DATABASE todo_plataforma_cfo;"
   psql -U postgres -d todo_plataforma_cfo -f schema.sql
   ```

2. **Copiar y editar `.env`.** Copia el ejemplo y edita el archivo nuevo con la configuración de tu PostgreSQL:
   ```powershell
   Copy-Item .env.example .env
   ```
   Define `CFO_DATABASE_URL` con el usuario, contraseña, host, puerto y nombre de la base de datos. Para desarrollo local por HTTP, conserva `CFO_SECURE_SESSION_COOKIE=false`; deja `CFO_ENABLE_DEMO_DATA=false`.

3. **Crear el entorno virtual e iniciar FastAPI.**
   ```powershell
   py -3.11 -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   .\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000
   ```
   Mantén esta terminal abierta. La API queda en `http://localhost:8000` y su documentación en `http://localhost:8000/docs`.

4. **Instalar e iniciar el frontend** en una segunda terminal desde la raíz del proyecto:
   ```powershell
   npm install
   npm run dev
   ```
   Abre [http://localhost:3000](http://localhost:3000).

5. **Registrarte.** En la pantalla inicial, selecciona **Crear cuenta**, ingresa tu nombre, correo y contraseña. En este MVP, el registro crea la cuenta con el rol `cfo` e inicia la sesión automáticamente; puedes usar la aplicación de inmediato sin que un administrador cambie tu rol.

   | Rol | Permisos principales |
   | --- | --- |
   | `cfo` | Consultar el resumen, cargar archivos, gestionar alertas, eliminar datos de práctica y generar/guardar recomendaciones. |
   | `analista` | Consultar el resumen, cargar archivos, gestionar alertas y eliminar datos de práctica. |
   | `administrador` | Permisos de analista y CFO, además de asignar responsables a las alertas. |

6. **Cargar los archivos de `datos/` desde la vista Carga ERP**, seleccionando el tipo indicado y en este orden:
   - Primero, [`datos/practica_transacciones_erp.csv`](datos/practica_transacciones_erp.csv) como **ERP**.
   - Segundo, [`datos/practica_transacciones_bancarias.csv`](datos/practica_transacciones_bancarias.csv) como **Banco**.
   - Por último, [`datos/practica_presupuestos.csv`](datos/practica_presupuestos.csv) como **Presupuesto**.

   Conserva el prefijo `practica_` en los nombres de los últimos tres archivos para que la acción **Eliminar datos de práctica** pueda reconocerlos. ERP/Banco requieren `fecha` y `monto`; Presupuesto requiere `periodo`, `monto_presupuestado`, `cuenta` y `centro_costo`.

7. **Revisar el resumen.** Después de las cargas, espera ver indicadores de ingresos y gastos, comparaciones frente al presupuesto y, cuando corresponda, alertas y recomendaciones basadas en los datos. El pronóstico de flujo neto requiere al menos 180 días de movimientos bancarios; si el resumen indica que faltan datos o no muestra una proyección, verifica el histórico bancario. El pronóstico es de flujo neto, no de saldo de caja.

En **Reportes**, al pulsar **Exportar reporte** en el resumen se guarda la instantánea junto con su PDF en la plataforma. La sección lista los reportes exportados y permite filtrarlos por la fecha final del resumen; cada reporte con PDF disponible puede descargarse desde allí. Abrir la sección no genera ni guarda reportes.

Si PostgreSQL no está levantado o `CFO_DATABASE_URL` no está configurado correctamente, `/health` indicará que la base de datos no está disponible.

### Migraciones de bases de datos existentes

En instalaciones nuevas, `schema.sql` incluye las migraciones. Para una base existente, aplica una sola vez las migraciones pendientes en orden. La primera registra el archivo de origen de cada presupuesto; la segunda conserva una recomendación por regla y periodo, transfiere su retroalimentación al registro conservado y evita duplicados futuros; la tercera añade el estado de vigencia de las recomendaciones; la cuarta crea la tabla de instantáneas de reportes; la quinta añade el almacenamiento de los PDF:

```powershell
psql -U postgres -d todo_plataforma_cfo -f migrations\001_track_budget_data_source.sql
psql -U postgres -d todo_plataforma_cfo -f migrations\002_deduplicate_recommendations_by_rule.sql
psql -U postgres -d todo_plataforma_cfo -f migrations\003_track_current_recommendations.sql
psql -U postgres -d todo_plataforma_cfo -f migrations\004_store_summary_reports.sql
psql -U postgres -d todo_plataforma_cfo -f migrations\005_store_summary_report_pdfs.sql
```

La acción **Eliminar datos de práctica** en Carga ERP solo elimina registros asociados a fuentes cuyo nombre de archivo inicia con `practica_`; los presupuestos importados conservan su fuente para no borrar presupuestos de otras cargas.

### Formatos de archivos

- **Excel/CSV (ERP y Banco):** deben incluir al menos `fecha` y `monto`. Se reconocen también `cuenta`, `nombre_cuenta`, `categoria`, `centro_costo`, `concepto`, `referencia` y `moneda`.
- **Presupuesto (CSV/Excel):** debe incluir `periodo`, `monto_presupuestado`, `cuenta` y `centro_costo`.
- **PDF:** se procesa mediante texto extraíble y requiere filas con `fecha` y `monto` legibles.
- Cada corrida crea un `sync_log`, conserva el payload original en staging y usa `source_type + source_reference` para evitar duplicados.
- Los archivos de práctica amplían los movimientos ERP y bancarios a una serie diaria continua, suficiente para el mínimo actual de 180 días de entrenamiento del forecast.
