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

Esta guía es para Windows y PowerShell. Ejecuta los comandos desde la carpeta raíz del proyecto (donde están `main.py`, `schema.sql` y `package.json`). Necesitas:

- PostgreSQL 15 o superior, instalado como servidor y en ejecución. En Windows, el instalador oficial está disponible en [postgresql.org/download/windows](https://www.postgresql.org/download/windows/). Recuerda la contraseña definida para el usuario administrador durante la instalación.
- Python 3.11 y el launcher `py`.
- Node.js 20.9 o superior y npm.
- El repositorio del proyecto descargado en el dispositivo.

Abre PowerShell y comprueba que las herramientas estén disponibles:

```powershell
psql --version
py -3.11 --version
node --version
npm --version
```

Si un comando no se reconoce, instala el componente correspondiente o agrégalo al `PATH`, cierra y vuelve a abrir PowerShell, y repite la comprobación. `psql` se instala con las herramientas de línea de comandos de PostgreSQL.

1. **Crear la base de datos y aplicar el esquema.** Confirma que el servicio de PostgreSQL esté iniciado. Estos comandos son para una instalación nueva con una base vacía. El ejemplo usa el usuario administrador `postgres`; si elegiste otro durante la instalación, reemplázalo. PostgreSQL solicitará la contraseña:
   ```powershell
   psql -U postgres -c "CREATE DATABASE todo_plataforma_cfo;"
   psql -v ON_ERROR_STOP=1 -U postgres -d todo_plataforma_cfo -f schema.sql
   ```
   El segundo comando debe terminar sin errores. Si la base ya existe y tiene el esquema aplicado, omite ambos comandos; no vuelvas a ejecutar `schema.sql` sobre una base inicializada. Si la base existe pero está vacía, omite solo el comando `CREATE DATABASE` y aplica el esquema.

2. **Configurar `.env`.** Copia el ejemplo y edita el archivo creado con los datos del servidor y el usuario que puede conectarse a la base:
   ```powershell
   Copy-Item .env.example .env
   ```
   `CFO_DATABASE_URL` se compone así:
   ```text
   <esquema>://<usuario>:<contraseña>@<host>:<puerto>/<base>
   ```
   Para este ejemplo usa `postgresql` como esquema, `postgres` como usuario, `localhost` como host, `5432` como puerto y `todo_plataforma_cfo` como base. Reemplaza `<contraseña>` con la contraseña real y quita los marcadores `< >`. Si la contraseña contiene caracteres reservados de URL (por ejemplo `@`, `:` o `/`), codifícalos como URL. Conserva `CFO_API_URL=http://localhost:8000/api/v1`, `CFO_ALLOWED_ORIGINS=http://localhost:3000`, `CFO_ENVIRONMENT=development`, `CFO_SECURE_SESSION_COOKIE=false` y `CFO_ENABLE_DEMO_DATA=false` para el uso local descrito aquí. No compartas ni subas el archivo `.env`.

3. **Instalar dependencias de Python e iniciar FastAPI.** En una terminal PowerShell, desde la raíz del repositorio:
   ```powershell
   py -3.11 -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   .\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000
   ```
   Mantén esta terminal abierta mientras uses la aplicación. La API queda en `http://localhost:8000` y su documentación en `http://localhost:8000/docs`. Si PowerShell indica que no existe `py -3.11`, instala Python 3.11 y vuelve a abrir la terminal.

4. **Instalar e iniciar el frontend** en una segunda terminal, también desde la raíz del repositorio. `npm ci` instala las versiones fijadas en `package-lock.json`:
   ```powershell
   npm ci
   npm run dev
   ```
   Mantén también esta terminal abierta y abre [http://localhost:3000](http://localhost:3000). Para detener los servicios, usa `Ctrl+C` en cada terminal.

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

En **Reportes**, al pulsar **Exportar reporte** en el resumen se guarda una instantánea del reporte en la plataforma y puedes elegir descargarla como PDF o Excel (`.xlsx`). El libro de Excel incluye hojas de indicadores, pronóstico, alertas y recomendaciones; sus importes y porcentajes se guardan como valores numéricos. La sección lista los reportes exportados y permite filtrarlos por la fecha final del resumen; cada reporte puede descargarse en ambos formatos desde allí. Abrir la sección no genera ni guarda reportes.

### Comprobación y solución de problemas

- Si `psql` no puede conectarse a `localhost` o rechaza la conexión, confirma que el servicio de PostgreSQL esté iniciado y que el host y puerto (normalmente `localhost:5432`) sean correctos.
- Si aparece un error de autenticación de PostgreSQL, revisa el usuario y la contraseña en `CFO_DATABASE_URL`. La contraseña de esa URL debe corresponder al usuario configurado en PostgreSQL.
- Si el puerto `8000` o `3000` ya está ocupado, cierra el proceso que lo usa o configura otro puerto. Si cambias el puerto del backend, actualiza `CFO_API_URL` en `.env`; si cambias el del frontend, actualiza `CFO_ALLOWED_ORIGINS` con el origen correspondiente.
- Si el proyecto abre pero faltan forecast, alertas o recomendaciones, carga los archivos de práctica indicados arriba. Para el forecast se requieren al menos 180 días de movimientos bancarios.
- Para comprobar que el frontend está listo para producción, ejecuta `npm run build`; para volver a iniciar después de compilar, usa `npm run start`. El uso local habitual de esta guía es `npm run dev`.

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
