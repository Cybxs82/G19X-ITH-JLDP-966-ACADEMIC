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
   py -3.8 -m venv .venv
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

* **Dashboard (`/dashboard` y `/kpis`):** Muestra el resumen de KPIs recalculados desde la tabla `transacciones` (filtrables por periodo), estado de alertas y recomendaciones.
* **Forecast de Flujo de Caja (`/forecast?days=90`):** Proyección a **30, 60 o 90 días** mediante regresión lineal diaria con intervalo predictivo del **80 %** y métrica de error **MAE a 30 días**.
  * *Nota:* Se activa únicamente cuando existen al menos **180 días recientes** de movimientos bancarios (sin datos suficientes, devuelve una serie vacía). Los movimientos netos bancarios no se muestran como saldo de caja final porque aún no se captura el saldo inicial.
* **Alertas (`/alerts`):** Calcula desviaciones al comparar movimientos contra el presupuesto importado. Permite consultar y atender alertas cambiando su estado o dejando comentarios.
* **Recomendaciones (`/recommendations` y `/feedback`):** Consulta de recomendaciones generadas y envío de retroalimentación del CFO.

---

## 🛠️ 5. Verificación Rápida (`/health`)

Si quieres comprobar que el backend y PostgreSQL están bien conectados, abre en el navegador:
* **`http://localhost:8000/health`**
  * Si todo está bien, reportará conexión exitosa (`SELECT 1`).
  * Si dice `database: unavailable`, verifica que PostgreSQL esté encendido y que los datos de tu `.env` sean los correctos.
