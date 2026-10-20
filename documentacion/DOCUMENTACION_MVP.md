# Documentación Técnica y Funcional del MVP — Plataforma CFO

**Proyecto:** Plataforma de Inteligencia Financiera para CFO (`todo_plataforma_cfo`)  
**Versión:** 1.0 (MVP)  
**Modalidad de Ejecución:** Exclusivamente Local (`localhost`)  
**Fecha:** Octubre 2026  
**Clasificación:** Documentación Técnica de Arquitectura y Negocio  

---

## 1. Declaración Fundamental: Sin IA generativa en el MVP

> ### PRINCIPIO DE DISEÑO DETERMINISTA, EXPLICABLE Y SIN COSTOS DE IA
> **Este MVP no utiliza IA generativa, redes neuronales, modelos de lenguaje (LLMs) ni servicios externos de IA.** Los cálculos financieros, KPIs, proyecciones y alertas se generan con métodos deterministas y estadísticos; los resúmenes y recomendaciones se construyen con reglas explicables.
>
> Todo el procesamiento descansa de manera exclusiva sobre:
> 1. **Fórmulas Aritméticas y Contables Deterministas:** Implementadas directamente en código Python y funciones de agregación nativas en PostgreSQL.
> 2. **Modelos Estadísticos Clásicos:** Regresión lineal por mínimos cuadrados ordinarios (OLS) para el flujo de caja, con intervalos de confianza analíticos y evaluación de error por MAE.
> 3. **Comparación Directa de Umbrales:** Evaluación aritmética entre gasto real y presupuesto aprobado.
> 4. **Parsers y Validadores de Esquema Estrictos:** Normalización estructurada de archivos sin inferencias heurísticas opacas.

### 1.1 Motivos Fundamentales para No Usar IA en el MVP

1. **Evitar Servicios de Pago y Costos Recurrentes de APIs (OpEx Cero):**
   * Las plataformas y APIs de Inteligencia Artificial comerciales (como Azure OpenAI, OpenAI o modelos LLM propietarios) son **servicios de pago por consumo de tokens y suscripciones recurrentes**.
   * Para este MVP se tomó la decisión estratégica de **no depender de servicios de pago**, eliminando gastos operativos recurrentes, suscripciones mensuales, dependencias de facturación con tarjetas de crédito y riesgos de interrupción por agotamiento de cuotas de pago.
   * Toda la pila tecnológica del MVP (Python, FastAPI, Next.js y PostgreSQL) es de código abierto y opera de manera 100% gratuita y autosuficiente en la máquina local.

2. **Auditoría e Inmutabilidad Contable:**
   * La dirección financiera, la junta directiva y los auditores exigen trazabilidad matemática exacta de cada cifra. Una fórmula contable debe dar siempre exactamente el mismo resultado ante los mismos datos de entrada ($2 + 2 = 4$).

3. **Cero Tolerancia a Alucinaciones:**
   * Los modelos generativos pueden inventar valores, confundir fechas o desviar órdenes de magnitud. En finanzas corporativas, una cifra inventada en la liquidez o en la nómina compromete la viabilidad legal y operativa de la empresa.

4. **Transparencia y Explicabilidad Total:**
   * Cada indicador se desglosa en sus transacciones subyacentes con su número de referencia, cuenta contable y centro de costo.

5. **Rendimiento y Latencia Inmediata:**
   * Las consultas SQL agregadas y las fórmulas matemáticas en Python responden en menos de **50 milisegundos**, sin tiempos de espera de llamadas a APIs externas.

### 1.2 Resúmenes y Recomendaciones Basados en Reglas

El alcance funcional del MVP contempla resúmenes ejecutivos y recomendaciones, pero no mediante IA generativa. Un motor de reglas deterministas aplicará condiciones y plantillas explicables a las **alertas, KPIs y forecast calculados a partir de datos financieros reales**. Cada resultado señalará su periodo, la regla que lo activó y la evidencia numérica correspondiente. Si faltan datos o el forecast no está disponible, el sistema lo indicará y no inventará cifras ni conclusiones. Las recomendaciones serán informativas y no ejecutarán acciones automáticamente.

---

## 2. Alcance Funcional del MVP (Ejecución Local)

### 2.1 Capacidades Incluidas
- **Consolidación de Fuentes (1 ERP + 1 Banco):** Ingesta de movimientos contables y extractos bancarios en formatos `.xlsx`, `.csv` y `.pdf` (con texto seleccionable).
- **Staging Inmutable y Calidad de Datos:** Almacenamiento íntegro de la carga cruda en JSONB (`datos_temporales_erp`, `datos_temporales_banco`) y desvío de filas corruptas a `registros_sincronizacion_rechazados` sin detener el procesamiento del lote válido.
- **Control de Idempotencia:** Prevención de duplicados mediante clave única `(fuente_datos_id, referencia_fuente)`.
- **Catálogo de KPIs Maestros:** Cálculo determinista de liquidez, rentabilidad, cumplimiento presupuestario y eficiencia operativa.
- **Proyección de Flujo de Caja (30, 60 y 90 días):** Regresión lineal diaria condicionada a un mínimo estricto de 180 días de histórico bancario, con intervalo de predicción del 80% y validación cruzada MAE a 30 días.
- **Control Presupuestario y Alertas:** Detección automática de desviaciones sobre el presupuesto mensual por centro de costo y cuenta, con semaforización y flujo de atención (`nueva`, `en_revision`, `cerrada`, `falsa`).
- **Resumen Ejecutivo y Recomendaciones:** Generación determinista mediante reglas y plantillas explicables a partir de alertas, KPIs y forecast disponibles; sin LLMs, APIs externas ni costos por consumo.
- **Seguridad y Cuentas Propias:** Autenticación local respaldada al 100% por PostgreSQL con control de roles (`cfo`, `analista`, `administrador`), sesiones seguras revocables y hashes Argon2id/bcrypt.

### 2.2 Capacidades Fuera del Alcance (Fuera de este MVP)
- Sin servicios ni APIs de IA de pago.
- Sin servidores remotos ni infraestructura cloud (todo corre localmente en `localhost`).
- No incluye conexión automática vía webhooks bancarios (la ingesta se realiza vía web o CLI local).
- No realiza cálculos fiscales, nómina detallada ni contabilidad transaccional directa (solo lectura y consolidación analítica).
- No es multi-empresa (diseñado para una sola empresa / single-tenant).

---

## 3. Catálogo de Fórmulas Matemáticas y Reglas del MVP

Cada métrica que se visualiza en el Dashboard se calcula mediante las siguientes expresiones matemáticas exactas:

### 3.1 KPIs de Liquidez

#### KPI-01: Saldo de Caja Actual
$$\text{Saldo de Caja} = \sum_{i=1}^{n} \text{Saldo Final Cuenta Bancaria}_i$$
* **Fuente:** Movimientos bancarios conciliados.
* **Frecuencia:** Diaria.
* **Regla:** Si falta información de una cuenta bancaria activa, se marca como *cálculo parcial con advertencia*.

#### KPI-02: Días de Caja (Cash Runway)
$$\text{Cash Runway (días)} = \frac{\text{Saldo de Caja Actual}}{\text{Promedio Diario de Egresos de los Últimos 30 Días}}$$
*Donde:*
$$\text{Promedio Diario de Egresos} = \frac{1}{30} \sum_{t=1}^{30} |\text{Egresos Netos}_t|$$
* **Regla:** Requiere al menos 30 días de movimientos bancarios continuos. Si no se cuenta con ellos, no se proyecta y se notifica el motivo.

#### KPI-03: Razón Corriente (Current Ratio)
$$\text{Razón Corriente} = \frac{\text{Total Activo Corriente}}{\text{Total Pasivo Corriente}}$$
* **Fuente:** Cuentas de balance general del ERP.
* **Interpretación:** Mide cuántos pesos de activo líquido respaldan cada peso de deuda a corto plazo.

#### KPI-04: Razón Rápida (Acid Test / Quick Ratio)
$$\text{Razón Rápida} = \frac{\text{Activo Corriente} - \text{Inventarios}}{\text{Pasivo Corriente}}$$
* **Fuente:** Cuentas de balance general del ERP.
* **Interpretación:** Solvencia inmediata sin depender de la venta o liquidación de inventarios.

---

### 3.2 KPIs de Rentabilidad

#### KPI-05: Margen Neto
$$\text{Margen Neto (\%)} = \left(\frac{\text{Utilidad Neta del Periodo}}{\text{Ingresos Totales del Periodo}}\right) \times 100$$
*Donde:*
$$\text{Utilidad Neta} = \sum \text{Ingresos} - \sum \text{Costos y Gastos Operativos}$$

#### KPI-06: ROE (Return on Equity)
$$\text{ROE (\%)} = \left(\frac{\text{Utilidad Neta Anualizada}}{\text{Patrimonio Promedio}}\right) \times 100$$

#### KPI-07: ROA (Return on Assets)
$$\text{ROA (\%)} = \left(\frac{\text{Utilidad Neta Anualizada}}{\text{Activo Total Promedio}}\right) \times 100$$

---

### 3.3 Control Presupuestario y Alertas

#### KPI-08, 09 y 10: Desviación Presupuestal
Para cualquier nivel de agregación (empresa global, centro de costo o línea contable específica):
$$\text{Desviación Absoluta} = \text{Monto Real Ejecutado} - \text{Monto Presupuestado}$$
$$\text{Desviación Porcentual (\%)} = \left(\frac{\text{Monto Real Ejecutado} - \text{Monto Presupuestado}}{\text{Monto Presupuestado}}\right) \times 100$$

#### Matriz de Severidad de Alertas
La generación de alertas compara el porcentaje contra la tabla `umbrales_alerta`:
* 🟢 **Baja:** Desviación menor al $\pm 5\%$. Variación ordinaria de operación.
* 🟡 **Media:** Desviación entre $\pm 5\%$ y $\pm 15\%$. Requiere seguimiento del analista.
* 🔴 **Alta:** Desviación superior al $\pm 15\%$. Genera alerta crítica automática en el panel directivo con asignación obligatoria de responsable.

---

### 3.4 Motor Estadístico de Proyección (Cash Flow Forecast)

El forecast diario a 30, 60 y 90 días no utiliza modelos generativos ni APIs externas. Emplea el método analítico de **Mínimos Cuadrados Ordinarios (OLS)**:

#### 1. Estimación de la Tendencia
Para una serie temporal de flujos netos diarios $(t_i, y_i)$ con $i = 1, \dots, n$ (donde $n \ge 180$ días):
$$\hat{y}(t) = \alpha + \beta \cdot t$$
*Donde los parámetros se calculan analíticamente:*
$$\beta = \frac{\sum_{i=1}^{n} (t_i - \bar{t})(y_i - \bar{y})}{\sum_{i=1}^{n} (t_i - \bar{t})^2}, \quad \alpha = \bar{y} - \beta \bar{t}$$

#### 2. Intervalo de Predicción del 80%
Para cada día proyectado $t_0 > t_n$:
$$\hat{y}(t_0) \pm t_{0.10, \, n-2} \cdot s \cdot \sqrt{1 + \frac{1}{n} + \frac{(t_0 - \bar{t})^2}{\sum_{i=1}^{n} (t_i - \bar{t})^2}}$$
*Donde:*
- $s = \sqrt{\frac{1}{n-2} \sum_{i=1}^{n} (y_i - \hat{y}_i)^2}$ es la desviación estándar de los residuos históricos.
- $t_{0.10, \, n-2}$ es el valor crítico de la distribución t de Student para un nivel de confianza bilateral del 80%.

#### 3. Validación de Calidad (MAE Backtest 30d)
Antes de publicar el pronóstico, el sistema evalúa la precisión del modelo simulando la proyección sobre los últimos 30 días reales observados:
$$\text{MAE} = \frac{1}{30} \sum_{k=1}^{30} |y_{\text{real}, k} - \hat{y}_{\text{predicho}, k}|$$

---

## 4. Pipeline de Procesamiento de Datos Local

```
┌──────────────────────────────────────────────┐
│ Archivo Fuente Local (CSV / Excel / PDF)     │
└──────────────────────┬───────────────────────┘
                       │ Carga web localhost / script CLI
                       ▼
┌──────────────────────────────────────────────┐
│            Staging Crudo (JSONB)             │ ───► Preserva el payload idéntico a la fuente
│       datos_temporales_erp / banco           │      para auditoría y re-procesamiento local.
└──────────────────────┬───────────────────────┘
                       │ Normalización y tipado estricto
                       ▼
┌──────────────────────────────────────────────┐
│            Validación de Esquema             │
└──────────────┬────────────────┬──────────────┘
               │ Válido         │ Inválido (Fecha o monto erróneo)
               ▼                ▼
┌──────────────────────────┐ ┌──────────────────────────────────────┐
│       transacciones      │ │ registros_sincronizacion_rechazados  │
└──────────────┬───────────┘ └──────────────────────────────────────┘
               │ Dispara recálculo síncrono
               ▼
┌──────────────────────────────────────────────┐
│              Recálculo de KPIs               │ ───► Actualiza valores_kpi por periodo
│          y Verificación de Alertas           │ ───► Genera/actualiza alertas en caso de desvío
└──────────────────────────────────────────────┘
```

---

## 5. Especificación de Endpoints del Backend Local (FastAPI en `localhost:8000`)

Todos los endpoints responden en formato JSON y siguen estándares REST bajo `/api/v1`:

| Endpoint | Método | Entrada | Salida / Acción |
|---|---|---|---|
| `/health` | `GET` | Ninguna | Estado del servicio local y verificación activa `SELECT 1` a PostgreSQL. |
| `/api/v1/dashboard` | `GET` | `periodo`, `centro_costo` | Resumen maestro de KPIs, forecast a 90d, alertas activas y fecha de última carga. |
| `/api/v1/kpis` | `GET` | `period`, `cost_center` | Catálogo de métricas calculadas con comparativa contra periodo anterior. |
| `/api/v1/forecast` | `GET` | `days=30\|60\|90` | Puntos diarios de la serie predicha con `limite_inferior` y `limite_superior` (80%) y métrica `mae_30d`. |
| `/api/v1/alerts` | `GET` | `estado`, `severidad` | Listado paginado de alertas presupuestarias detectadas. |
| `/api/v1/alerts/{id}` | `PATCH` | `estado`, `comentario`, `responsable_id` | Atención y resolución de alertas por el analista. |
| `/api/v1/ingestion/files` | `POST` | `source_type`, `file` | Procesa y normaliza archivos en tiempo real desde el equipo local. |
| `/api/v1/ingestion/budgets` | `POST` | `file` (CSV/Excel) | Ingesta metas presupuestarias por periodo, cuenta y centro de costo. |

---

## 6. Esquema de Base de Datos y Persistencia Local

El sistema opera sobre PostgreSQL 15+ local (`localhost:5432`) estructurado en tablas normalizadas con claves foráneas, restricciones únicas y disparadores de auditoría:

```
usuarios (Identidad) ─────────◄ credenciales_usuario (Hashes)
      │
      ├───────────────────────◄ sesiones_autenticacion (Tokens seguros)
      │
      ├───────────────────────◄ alertas (Responsable asignado / Atendido por)
      │
      └───────────────────────◄ registro_auditoria (Trazabilidad)

fuentes_datos ────────────────◄ registros_sincronizacion
                                      │
                                      ├─◄ registros_sincronizacion_rechazados
                                      ├─◄ datos_temporales_erp (JSONB)
                                      └─◄ datos_temporales_banco (JSONB)

cuentas ───────────────┬──────◄ transacciones (Núcleo financiero)
centros_costo ─────────┤              ▲
                       ├──────◄ presupuestos (Versionado de metas)
                       │
                       └──────◄ alertas (Detección de desvíos)

definiciones_kpi ─────────────◄ valores_kpi (Resultados precalculados)

ejecuciones_pronostico ───────◄ valores_pronostico (Predicción 30/60/90d + 80%)
```

---

## 7. Criterios de Rendimiento y Seguridad en Entorno Local

- **Cero Costo Operativo (OpEx $0):** Sin tarifas por llamada a API ni cobros por volumen de datos.
- **Tiempo de Carga del Dashboard Local:** Menor a **1 segundo** en ejecución local.
- **Latencia de la API:** Menor a **50 ms** por comunicación directa en `localhost`.
- **Protección de Datos:**
  - Contraseñas almacenadas exclusivamente con hashes robustos con sal (Argon2id / bcrypt).
  - Variables de entorno en `.env` local sin credenciales expuestas en repositorios públicos.
  - Cookies de sesión con atributos `HttpOnly` y `SameSite=Lax` configuradas para HTTP local (`CFO_SECURE_SESSION_COOKIE=false`).
