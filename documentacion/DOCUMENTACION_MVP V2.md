# Documentación Técnica y Funcional del MVP — Plataforma CFO

**Proyecto:** Plataforma de Inteligencia Financiera para CFO (`todo_plataforma_cfo`)  
**Versión:** 1.0 (MVP)  
**Modalidad de Ejecución:** Exclusivamente Local (`localhost`)  
**Fecha:** Octubre 2026  
**Clasificación:** Documentación Técnica de Arquitectura y Negocio  

---

## 1. Declaración sobre el uso de IA

### 1.1 Apoyo de IA durante el desarrollo

Durante el desarrollo se utilizó IA como herramienta de apoyo para proponer y documentar reglas, fórmulas y condiciones de recomendación; colaborar parcialmente en el diseño del esquema de base de datos; y apoyar gran parte del diseño visual y frontend. El desarrollador definió e implementó principalmente el backend, revisó y adaptó las propuestas, integró los componentes y verificó el comportamiento del sistema mediante pruebas y validación del código. La IA fue una herramienta de asistencia al desarrollo; no es un componente ni una dependencia del producto en ejecución.

### 1.2 Funcionamiento sin IA en tiempo de ejecución

**El sistema en funcionamiento no utiliza agentes, modelos generativos, LLM ni servicios externos de IA.** Los cálculos financieros, KPIs, proyecciones y alertas usan código determinista y métodos estadísticos; las recomendaciones usan reglas explicables y plantillas de texto predefinidas. La aplicación no consulta IA para evaluar reglas ni para crear, redactar o modificar mensajes.

El procesamiento se basa en:
1. **Fórmulas aritméticas y contables deterministas:** implementadas en Python y consultas/agregaciones PostgreSQL.
2. **Métodos estadísticos clásicos:** regresión lineal por mínimos cuadrados ordinarios (OLS) para el flujo neto bancario.
3. **Comparación de umbrales:** evaluación aritmética entre gasto real y presupuesto.
4. **Parsers y validadores estrictos:** normalización estructurada de archivos.

### 1.3 Motivos para no usar IA en tiempo de ejecución

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

### 1.4 Resúmenes y recomendaciones basados en reglas

El alcance funcional del MVP contempla resúmenes ejecutivos y recomendaciones. Un motor de reglas deterministas aplica condiciones y plantillas explicables a las **alertas, KPIs y forecast calculados a partir de datos financieros reales**. Cada resultado señala su periodo, la regla que lo activó y la evidencia numérica correspondiente. Si faltan datos o el forecast no está disponible, el sistema lo indica y no inventa cifras ni conclusiones. Las recomendaciones son informativas y no ejecutan acciones automáticamente.

**Compatibilidad de base de datos:** `recomendaciones_ia` y `retroalimentacion_ia` son nombres heredados que se conservan para no romper el esquema existente. También son heredados los nombres de columnas `version_prompt`, `prompt_utilizado` y `texto_generado`: almacenan, respectivamente, la versión de reglas, la regla/plantilla aplicada y el texto resultante. `nombre_modelo` identifica el motor (`reglas-v1`), no un modelo de IA.

---

## 2. Alcance Funcional del MVP (Ejecución Local)

### 2.1 Capacidades Incluidas
- **Consolidación de Fuentes (1 ERP + 1 Banco):** Ingesta de movimientos contables y extractos bancarios en formatos `.xlsx`, `.csv` y `.pdf` (con texto seleccionable).
- **Staging Inmutable y Calidad de Datos:** Almacenamiento íntegro de la carga cruda en JSONB (`datos_temporales_erp`, `datos_temporales_banco`) y desvío de filas corruptas a `registros_sincronizacion_rechazados` sin detener el procesamiento del lote válido.
- **Control de Idempotencia:** Prevención de duplicados mediante clave única `(fuente_datos_id, referencia_fuente)`.
- **KPIs implementados:** Flujo neto bancario mensual, margen operativo, ingresos acumulados y desviación presupuestal. Los demás KPIs descritos como catálogo objetivo no se calculan en este MVP.
- **Proyección de flujo neto bancario (30, 60 y 90 días):** Regresión lineal diaria condicionada a un mínimo de 180 días calendario de histórico bancario, con intervalo de predicción del 80% y MAE de backtest sobre 30 observaciones.
- **Control Presupuestario y Alertas:** Detección automática de desviaciones sobre el presupuesto mensual por centro de costo y cuenta, con semaforización y flujo de atención (`nueva`, `en_revision`, `cerrada`, `falsa`).
- **Resumen Ejecutivo y Recomendaciones:** Generación determinista mediante reglas y plantillas explicables a partir de alertas, KPIs y forecast disponibles; sin LLMs, APIs externas ni costos por consumo.
- **Seguridad y cuentas propias:** Autenticación local respaldada por PostgreSQL con control de roles (`cfo`, `analista`, `administrador`) y sesiones revocables. Las metas de producción y controles no implementados se consideran pendientes.

### 2.2 Capacidades Fuera del Alcance (Fuera de este MVP)
- Sin servicios ni APIs de IA de pago.
- Sin servidores remotos ni infraestructura cloud (todo corre localmente en `localhost`).
- No incluye conexión automática vía webhooks bancarios (la ingesta se realiza vía web o CLI local).
- No realiza cálculos fiscales, nómina detallada ni contabilidad transaccional directa (solo lectura y consolidación analítica).
- No es multi-empresa (diseñado para una sola empresa / single-tenant).

---

## 3. KPIs y fórmulas: estado de implementación

El catálogo separa los indicadores calculados por el código de los indicadores financieros propuestos. Solo se consideran implementados los cuatro del primer apartado; las demás fórmulas describen métricas que no se ofrecen en el MVP.

### 3.1 KPIs implementados

#### Flujo neto bancario mensual
$$\text{Flujo neto bancario} = \sum \text{montos bancarios del mes}$$
* **Estado:** Implementado por periodo y centro de costo.
* **Límite:** Es un flujo neto de movimientos, no saldo de caja; no existe saldo inicial.

#### Margen operativo
$$\text{Margen operativo (\%)} = \frac{\text{ingresos} - \text{gastos}}{\text{ingresos}} \times 100$$
* **Estado:** Implementado con datos ERP cuando los ingresos del periodo son positivos; se agrupa por periodo y centro de costo.

#### Ingresos acumulados del periodo
$$\text{Ingresos acumulados} = \sum \text{montos positivos ERP del periodo}$$
* **Estado:** Implementado con datos ERP, por periodo y centro de costo.

#### Desviación presupuestal
$$\text{Desviación presupuestal (\%)} = \frac{\text{gastos reales} - \text{presupuesto}}{\text{presupuesto}} \times 100$$
* **Estado:** Implementado cuando existe presupuesto positivo; se agrupa por periodo y centro de costo.
* **Nota:** La detección de alertas se realiza separadamente por cuenta y centro de costo.

---

### 3.2 KPIs definidos pero no implementados

Los KPI siguientes describen el catálogo objetivo, pero requieren fuentes de balance, saldos iniciales u otros datos que el MVP actual no ingiere ni procesa.

| KPI del catálogo | Estado | Motivo |
|---|---|---|
| Saldo de caja actual | No implementado | No se captura saldo inicial ni saldo final por cuenta. |
| Días de caja (Cash Runway) | No implementado | Depende de saldo de caja y egresos diarios continuos. |
| Razón corriente | No implementado | No se ingieren activos ni pasivos corrientes del balance. |
| Razón rápida | No implementado | No se ingieren inventarios ni pasivos corrientes. |
| Margen neto | No implementado | No se reciben los datos necesarios para utilidad neta; el KPI disponible es margen operativo. |
| ROE | No implementado | No se ingiere patrimonio promedio. |
| ROA | No implementado | No se ingiere activo total promedio. |
| DSO / eficiencia operativa | No implementado | No se reciben saldos de cuentas por cobrar y ventas a crédito. |

---

### 3.3 Control Presupuestario y Alertas

#### KPI-08, 09 y 10: Desviación Presupuestal
Esta es la fórmula del KPI consolidado, implementado por periodo y centro de costo; los KPI-08, 09 y 10 del catálogo objetivo por empresa/área/línea de gasto no son tres cálculos independientes disponibles en el MVP:
$$\text{Desviación Absoluta} = \text{Monto Real Ejecutado} - \text{Monto Presupuestado}$$
$$\text{Desviación Porcentual (\%)} = \left(\frac{\text{Monto Real Ejecutado} - \text{Monto Presupuestado}}{\text{Monto Presupuestado}}\right) \times 100$$

#### Matriz implementada de severidad de alertas
La ingesta aplica límites fijos; aunque existe la tabla `umbrales_alerta`, actualmente no se consulta para parametrizarlos:
* Sin alerta: desviación absoluta menor a `10 %`.
* 🟡 **Media:** `10 % <= |desviación| < 20 %`.
* 🔴 **Alta:** `|desviación| >= 20 %`.
* Se evalúan desviaciones positivas y negativas. Las alertas se recalculan después de importar archivos/presupuestos, no por sincronización automática diaria.

---

### 3.4 Reglas Explicables de Recomendación

Las reglas se evalúan sobre alertas abiertas (`nueva` o `en_revision`), el último valor disponible de cada KPI por centro de costo y el forecast calculado con transacciones bancarias. Cada recomendación registra el identificador de regla, periodo, situación, impacto, acción, prioridad y evidencia (`alertas_ids`, `kpis_ids` y, para forecast, los horizontes/valores evaluados). Las reglas no ejecutan acciones.

#### REGLA-01: Alerta abierta de severidad alta
- **Condición:** existe al menos una alerta abierta con `severidad = alta` y `desviacion_pct > 0`.
- **Fórmula de impacto:** suma de `monto_real - monto_presupuestado` para las alertas coincidentes.
- **Situación:** «N alerta(s) abierta(s) de severidad alta presentan sobrepaso presupuestal».
- **Texto:** «Revisar las partidas afectadas y acordar acciones de contención con sus responsables».
- **Prioridad:** alta.
- **Evidencia:** IDs de las alertas coincidentes.

#### REGLA-02: Varias alertas abiertas en un centro de costo
- **Condición:** hay dos o más alertas abiertas con el mismo `centro_costo_id`. Un centro nulo se agrupa como ámbito empresa; no se exige que las alertas correspondan a periodos distintos.
- **Fórmula:** `cantidad_alertas_abiertas_por_centro = COUNT(alertas.id)`; se activa cuando el conteo es `>= 2`.
- **Situación:** indica cuántas alertas abiertas hay en el centro de costo o en la empresa.
- **Texto:** «Priorizar una revisión conjunta de las partidas y asignar responsables para cada alerta».
- **Prioridad:** media.
- **Evidencia:** IDs de todas las alertas del grupo y el centro de costo.

#### REGLA-03: Flujo neto bancario negativo
- **Condición:** el último KPI por centro de costo, con código `flujo_neto_bancario`, tiene valor `< 0`.
- **Fórmula de impacto:** se informa el valor del KPI y su magnitud absoluta como reducción del flujo neto; el servicio no lo interpreta como saldo bancario.
- **Situación:** «El flujo neto bancario del periodo es negativo».
- **Texto:** «Revisar pagos y cobros próximos y validar el saldo inicial antes de tomar decisiones de liquidez».
- **Prioridad:** alta.
- **Evidencia:** ID y valor del KPI, periodo y centro de costo.

#### REGLA-04: Margen operativo negativo
- **Condición:** el último KPI por centro de costo, con código `margen_operativo`, tiene valor `< 0`.
- **Fórmula evaluada:** `margen_operativo < 0`; el KPI de origen se calcula como `(ingresos - gastos) / ingresos * 100` cuando los ingresos son positivos.
- **Situación:** «El margen operativo calculado es negativo».
- **Impacto:** porcentaje del margen negativo observado.
- **Texto:** «Analizar ingresos y gastos operativos del periodo para identificar las partidas que presionan el margen».
- **Prioridad:** alta.
- **Evidencia:** ID y valor del KPI, periodo y centro de costo.

#### REGLA-05: Desviación presupuestal positiva
- **Condición:** el último KPI por centro de costo, con código `desviacion_presupuestal`, tiene valor `> 0`.
- **Fórmula evaluada:** `desviacion_presupuestal > 0`; el KPI de origen se calcula como `(gastos - presupuesto) / presupuesto * 100` cuando el presupuesto es positivo.
- **Situación:** «El KPI de desviación presupuestal indica gasto por encima del presupuesto».
- **Impacto:** porcentaje de desviación observado.
- **Texto:** «Revisar el gasto del periodo frente al presupuesto y determinar si requiere ajuste o medidas correctivas».
- **Prioridad:** alta si la desviación es `>= 20 %`; media si es menor a `20 %`.
- **Evidencia:** ID y valor del KPI, periodo y centro de costo.

#### REGLA-06: Flujo neto bancario proyectado negativo
- **Condición:** existe al menos 180 días de histórico bancario y el valor predicho del forecast diario es `< 0` en uno o más de los horizontes de 30, 60 o 90 días.
- **Fórmula evaluada:** `valor_predicho(horizonte) < 0` para `horizonte ∈ {30, 60, 90}`. El forecast de origen usa regresión lineal sobre los flujos diarios; ese valor es flujo neto, no el saldo acumulado de caja.
- **Situación:** identifica los horizontes de 30, 60 o 90 días que proyectan flujo neto negativo.
- **Impacto:** valor predicho negativo en el primer horizonte que presenta la condición; se incluyen los demás horizontes negativos evaluados.
- **Texto:** «Validar el saldo disponible y preparar un plan de liquidez para ese horizonte revisando cobros, pagos y alternativas de financiamiento».
- **Prioridad:** alta si el primer horizonte negativo es a 30 días; media si es a 60 o 90 días.
- **Evidencia:** horizonte, fecha objetivo y valor predicho de cada punto negativo. No se asignan IDs de KPI o alerta al forecast porque el pronóstico no tiene esos identificadores.

#### Aviso de datos insuficientes
Este aviso no es una recomendación financiera ni una séptima regla de decisión. Se registra cuando no hay alertas en la tabla, faltan uno o más KPIs seguidos por el motor, o no puede calcularse el forecast (incluido histórico menor de 180 días). Enumera las fuentes faltantes, usa listas de evidencia vacías y no inventa cifras o impactos.

---

### 3.5 Motor Estadístico de Proyección (Cash Flow Forecast)

El forecast diario a 30, 60 y 90 días no utiliza modelos generativos ni APIs externas. Emplea el método analítico de **Mínimos Cuadrados Ordinarios (OLS)**:

#### 1. Estimación de la Tendencia
Para una serie temporal de flujos netos diarios $(t_i, y_i)$ con $i = 1, \dots, n$ (donde $n \ge 180$ días):
$$\hat{y}(t) = \alpha + \beta \cdot t$$
*Donde los parámetros se calculan analíticamente:*
$$\beta = \frac{\sum_{i=1}^{n} (t_i - \bar{t})(y_i - \bar{y})}{\sum_{i=1}^{n} (t_i - \bar{t})^2}, \quad \alpha = \bar{y} - \beta \bar{t}$$

#### 2. Intervalo de Predicción del 80%
Para cada día proyectado $t_0 > t_n$:
$$\hat{y}(t_0) \pm 1.2815515655 \cdot s \cdot \sqrt{1 + \frac{1}{n} + \frac{(t_0 - \bar{t})^2}{\sum_{i=1}^{n} (t_i - \bar{t})^2}}$$
*Donde:*
- $s = \sqrt{\frac{1}{n-2} \sum_{i=1}^{n} (y_i - \hat{y}_i)^2}$ es la desviación estándar de los residuos históricos.
- El factor fijo `1.2815515655` es el cuantil normal usado por la implementación para un intervalo bilateral aproximado del 80 %; no se calcula el cuantil t de Student.

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
| `/api/v1/dashboard` | `GET` | `period_from`, `period_to`, `cost_center_id` | Resumen de KPIs, forecast de 90 días, alertas y recomendaciones guardadas; estas últimas no se leen cuando `CFO_ENABLE_DEMO_DATA=false`. |
| `/api/v1/kpis` | `GET` | `period_from`, `period_to` | KPIs calculados, con comparativa contra el periodo anterior. |
| `/api/v1/forecast` | `GET` | `days=30\|60\|90` | Puntos diarios de flujo neto con `lower_bound` y `upper_bound` (80 %). La respuesta no incluye MAE. |
| `/api/v1/alerts` | `GET` | `status`, `severity`, `period_from`, `period_to`, `cost_center_id` | Alertas presupuestarias detectadas (sin paginación). |
| `/api/v1/alerts/{id}` | `PATCH` | `status`, `comment`, `responsible_id` | Atención y resolución de alertas por el analista. |
| `/api/v1/recommendations` | `GET` | `period` (opcional) | Lista recomendaciones guardadas; actualmente devuelve vacío si `CFO_ENABLE_DEMO_DATA=false`. |
| `/api/v1/recommendations/generate` | `POST` | Sesión autenticada | Evalúa las reglas explicables y persiste resultados, versión y evidencia en `recomendaciones_ia`. |
| `/api/v1/feedback` | `POST` | `recommendation_id`, `user_id`, `feedback`, `comment` (opcional) | Registra retroalimentación autenticada del usuario sobre una recomendación. |
| `/api/v1/ingestion/files` | `POST` | `source_type`, `file` | Procesa y normaliza archivos en tiempo real desde el equipo local. |
| `/api/v1/ingestion/documents` | `POST` | `file` (PDF/CSV/Excel) | Ingresa un documento ERP compatible. |
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
