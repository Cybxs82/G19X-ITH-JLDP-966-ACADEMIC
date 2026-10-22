# Manual de Usuario — Plataforma CFO

Dashboard en **Next.js** con API en **FastAPI** y base de datos **PostgreSQL** para inteligencia financiera.

---

## ⚠️ 1. Configuración Obligatoria (Antes de Iniciar)

Para que el proyecto conecte con tu base de datos local, debes hacer estos **2 pasos** antes de arrancar:

### Paso 1: Cargar el Esquema de Base de Datos (`schema.sql`)
Crea tu base de datos en PostgreSQL (15+) y ejecuta el esquema incluido en el proyecto:

```powershell
psql -U postgres -c "CREATE DATABASE todo_plataforma_cfo;"
psql -U postgres -d todo_plataforma_cfo -f schema.sql
```

### Paso 2: Cambiar los Valores del Archivo `.env`
Abre el archivo **`.env`** que te compartí y **cambia `USUARIO`, `CONTRASENA`, `HOST` y `NOMBRE_BASE`** por los datos de tu propio PostgreSQL para que se conecte correctamente:

```env
CFO_DATABASE_URL=postgresql+psycopg2://USUARIO:CONTRASENA@localhost:5432/todo_plataforma_cfo
CFO_ENABLE_DEMO_DATA=false
CFO_SECURE_SESSION_COOKIE=false
```
*(En ejecución local por HTTP, mantén `CFO_SECURE_SESSION_COOKIE=false` para que la sesión no se cierre).*

---

## 🚀 2. Cómo Encender el Proyecto Localmente

1. **Encender el Backend (FastAPI en puerto `8000`):**
   ```powershell
   py -3.11 -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   .\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000
   ```
   *API disponible en `http://localhost:8000` y documentación en `http://localhost:8000/docs`.*

2. **Encender el Frontend (Next.js en puerto `3000`):**
   ```bash
   npm install
   npm run dev
   ```
   *Abre **`http://localhost:3000`** en tu navegador e **inicia sesión**.*

---

## 📂 3. Importación de Datos (Después de Iniciar Sesión)

**Una vez que ya iniciaste sesión y estás dentro del proyecto**, es obligatorio importar los archivos de prueba para calcular KPIs y desviaciones:

1. En la **carpeta raíz del proyecto** hay una carpeta llamada **`datos/`** que contiene los documentos listos para probar la importación.
2. Dentro de la plataforma web, ve a la vista **Carga ERP**.
3. **Se impulsa a usar sí o sí los archivos de la carpeta `datos/`** en este orden para el correcto funcionamiento y demostración del proyecto:
   * **Primero:** Selecciona origen **ERP** y sube **`datos/erp_datasheet_50_lineas.csv`**.
   * **Segundo:** Selecciona origen **Presupuesto** y sube **`datos/presupuesto_template.csv`**.
   * **Tercero (Opcional):** Selecciona **Banco** para cargar archivos de movimientos bancarios de `datos/`.

*(También puedes importarlos por terminal si lo prefieres):*
```powershell
.\.venv\Scripts\python.exe scripts\ingest_financial_files.py .\datos\erp_datasheet_50_lineas.csv --source-type erp
.\.venv\Scripts\python.exe scripts\ingest_financial_files.py .\datos\presupuesto_template.csv --source-type presupuesto
```

### Reglas de los Archivos de Carga
* **Excel / CSV de movimientos:** Deben incluir al menos `fecha` y `monto`. También reconoce `cuenta`, `nombre_cuenta`, `categoria`, `centro_costo`, `concepto`, `referencia` y `moneda`.
* **Presupuesto (CSV / Excel):** Debe incluir `periodo`, `monto_presupuestado`, `cuenta` y `centro_costo`.
* **PDF:** Se procesa mediante texto extraíble y requiere filas con `fecha` y `monto` legibles.
* **Control de calidad:** Cada carga guarda el archivo original en staging (`datos_temporales_erp` o `datos_temporales_banco`), envía filas con errores a `registros_sincronizacion_rechazados`, evita duplicados usando `source_type + source_reference` y recalcula los KPIs automáticamente.

---

## 📊 4. Uso de las Vistas del Sistema

* **Dashboard (`/`):** Muestra los KPIs calculados desde `transacciones`, el estado de alertas y el forecast. `/kpis` no es una ruta de página; el endpoint de datos es `GET /api/v1/kpis`.
* **Forecast (`GET /api/v1/forecast?days=90`):** Proyecta flujo neto bancario a **30, 60 o 90 días** mediante regresión lineal diaria, con intervalo predictivo del **80 %**. El MAE de backtest se calcula internamente y no forma parte de la respuesta de este endpoint.
  * *Nota:* Requiere al menos **180 días calendario** entre la primera y la última transacción bancaria. Si no hay datos suficientes, devuelve una serie vacía. El flujo neto no es saldo de caja final porque no se captura el saldo inicial.
* **Alertas (`GET /api/v1/alerts`):** Calcula desviaciones al comparar movimientos con el presupuesto importado. Se genera alerta desde una desviación absoluta de **10 %**; es media entre **10 % y menos de 20 %**, y alta desde **20 %**. Permite cambiar el estado y añadir comentarios con `PATCH /api/v1/alerts/{id}`.
* **Recomendaciones y retroalimentación (API):** `POST /api/v1/recommendations/generate` evalúa reglas deterministas y guarda sus resultados y evidencia; `GET /api/v1/recommendations` consulta registros, y `POST /api/v1/feedback` registra retroalimentación. Importante: en la configuración actual, el endpoint GET devuelve una lista vacía con `CFO_ENABLE_DEMO_DATA=false`; no actives el modo demo en una base con datos reales, pues la inicialización de demo puede borrar filas financieras. Si faltan datos, el sistema indica su ausencia sin inventar cifras.

Para conocer el uso de IA como herramienta de apoyo durante el desarrollo y confirmar que no se utiliza en tiempo de ejecución, consulta `DOCUMENTACION_MVP.md`, sección 1.

---

## 🛠️ 5. Verificación Rápida (`/health`)

Si quieres comprobar que el backend y PostgreSQL están bien conectados, abre en el navegador:
* **`http://localhost:8000/health`**
  * Si todo está bien, reportará conexión exitosa (`SELECT 1`).
  * Si dice `database: unavailable`, verifica que PostgreSQL esté encendido y que los datos de tu `.env` sean los correctos.
