```markdown
# PRD — Plataforma de Inteligencia Financiera para CFO (v3)

## 0. Resumen ejecutivo

**Qué es:**  
Plataforma web (MVC) que consolida datos del ERP y del banco, calcula KPIs financieros, proyecta el flujo de caja a 90 días, detecta desviaciones presupuestales y genera un resumen ejecutivo y recomendaciones mediante reglas explicables para el CFO, sin IA generativa ni servicios de pago.

**Problema que resuelve:**  
El CFO depende de reportes manuales y dispersos, con días de retraso para detectar desviaciones y sin capacidad predictiva.

**Objetivo:**  
Reducir el tiempo de preparación de información financiera de días a horas y ofrecer proyecciones y recomendaciones accionables.

**Usuarios principales:**  
- CFO: vista ejecutiva y decisiones rápidas.  
- Analista financiero: mantener y validar datos, atender alertas.  
- Administrador: operar la plataforma (usuarios, umbrales, configuración).

**Alcance MVP:**  
- Integración: 1 ERP + 1 banco.  
- KPIs: liquidez, rentabilidad, cumplimiento presupuestal.  
- Forecast: flujo de caja a 90 días.  
- Alertas: desviaciones presupuestales.  
- Resumen ejecutivo y recomendaciones generados por reglas deterministas y explicables a partir de alertas, KPIs y forecast calculados con datos reales; sin IA generativa ni APIs de pago.
- Dashboard único con filtros por periodo y área.  
- Seguridad: autenticación propia con PostgreSQL y control de acceso por roles.

**Criterios de éxito clave:**  
- Reducir preparación de reportes de 2 días a < 2 horas.  
- ≥ 95 % de cargas diarias completadas antes de la hora objetivo.  
- MAE del forecast por debajo del objetivo acordado.  
- Interfaz validada como intuitiva por el CFO y al menos una recomendación accionable en un ciclo real.

---

## 1. Qué es el proyecto

Plataforma web bajo arquitectura **MVC (Modelo-Vista-Controlador)** que consolida datos financieros (ERP + banco), calcula KPIs clave, proyecta flujo de caja, detecta desviaciones presupuestales y construye un resumen ejecutivo y recomendaciones con reglas explicables a partir de alertas, KPIs y forecast calculados con datos reales.

---

## 2. Qué hace (capacidades principales)

- Extrae y consolida datos financieros de forma automatizada (sin captura manual).
- Calcula KPIs de liquidez, rentabilidad y cumplimiento presupuestal.
- Proyecta el flujo de caja a 30/60/90 días con un modelo predictivo.
- Detecta y alerta desviaciones presupuestales que superen un umbral configurable.
- Genera un resumen ejecutivo y recomendaciones mediante reglas deterministas, con plantillas explicables y evidencia ligada a las alertas, KPIs y forecast disponibles.
- Muestra todo en un dashboard único, con acceso diferenciado por rol.

---

## 3. Qué NO es / NO hace (fuera de alcance)

- No es un ERP ni sistema contable/transaccional; solo lee datos del ERP.
- No calcula nómina ni contabilidad fiscal/legal.
- No es un chatbot financiero de conversación abierta; no hay RAG en esta versión.
- No evalúa riesgo de crédito ni de mercado en esta versión.
- No es multi-empresa (multi-tenant); diseñado para una sola empresa.
- No tiene app móvil nativa; solo web responsiva.
- No migra datos históricos ilimitados; histórico inicial acotado a 24 meses.

---

## 4. Problema y objetivos

**Problema:**  
El CFO depende de reportes manuales y dispersos entre sistemas, con días de retraso para detectar desviaciones y sin capacidad predictiva.

**Objetivo del producto:**  
Reducir el tiempo de detección de desviaciones y de generación de proyecciones de días a horas, con recomendaciones accionables y explicables generadas por reglas a partir de datos financieros calculados.

**Objetivos medibles (MVP):**

- Reducir la preparación del reporte financiero de **2 días a menos de 2 horas**.
- Actualizar el **95 % de las cargas diarias antes de la hora objetivo** (ej. 8:00 a. m. local).
- Mantener una **tasa de errores de integración < 1 %** (registros rechazados / totales).
- Lograr un **MAE del forecast** inferior al objetivo acordado con el CFO.
- Que al menos el **80 % de los usuarios de prueba** complete las tareas principales sin asistencia.

---

## 5. Usuarios y roles

| Rol | Qué necesita | Acceso |
|---|---|---|
| CFO | Vista ejecutiva y decisiones rápidas | Lectura completa: KPIs, forecast, alertas y recomendaciones basadas en reglas |
| Analista financiero | Mantener y validar los datos | Lectura completa + sincronizar datos, atender alertas (revisar, comentar, cerrar, marcar como falsa, asignar responsable) |
| Administrador | Operar la plataforma | Gestión de usuarios/roles, configuración de umbrales, logs |

Notas:

- Habrá múltiples usuarios dentro de la misma empresa.
- En esta versión no hay multi-tenant; todos los usuarios pertenecen a la misma organización.
- El rol de Auditor/Controller queda como posible extensión en v2.

---

## 6. Alcance funcional (por módulo)

| Módulo | Alcance de este PRD |
|---|---|
| Datos | ERP + 1 banco, actualización automática (mínimo diaria, horario y zona horaria definidos en Fase 1) |
| KPIs | Liquidez, rentabilidad, cumplimiento presupuestal (catálogo detallado en sección 13) |
| Predicción | Forecast de flujo de caja a 90 días, con vistas a 30/60/90 días e intervalo de confianza (sección 14) |
| Alertas | Desviación presupuestal por encima de umbral configurable, con severidad, estado y responsable (sección 15) |
| Reglas explicables | Resumen ejecutivo y recomendaciones deterministas basados en alertas, KPIs y forecast disponibles, con evidencia y controles de datos insuficientes (sección 16) |
| Dashboard | Vista única con KPIs, gráfica de forecast, panel de alertas y recomendaciones; filtros por periodo/área aplicables a KPIs, forecast y alertas |
| Seguridad | Inicio de sesión y creación de cuentas contra PostgreSQL, control de acceso por rol y auditoría de accesos y cambios |

---

## 7. Arquitectura del sistema (MVC)

La aplicación sigue una arquitectura **MVC** desacoplada:

- **Modelo (Model):**  
  - PostgreSQL + SQLAlchemy/ORM.  
  - Entidades: KPIs, Staging, Usuarios, Credenciales, Sesiones, Histórico Financiero.  
  - Lógica de persistencia, relaciones y consultas analíticas optimizadas.

- **Vista (View):**  
  - React (SPA).  
  - Dashboards interactivos, componentes gráficos y alertas tras cada sincronización.  
  - Indicador visible de “Datos actualizados el [fecha/hora]”.

- **Controlador (Controller):**  
  - Python + FastAPI.  
  - Lógica de negocio, cálculo de KPIs, coordinación del forecasting y aplicación de reglas explicables para resúmenes y recomendaciones.

- **Infraestructura y seguridad:**  
  - Docker + GitHub Actions (CI/CD).  
  - PostgreSQL como fuente única de usuarios, credenciales, sesiones y roles.
  - Contraseñas almacenadas únicamente como hashes seguros; nunca se persisten contraseñas en texto plano.

Nota: MVC aplica principalmente a la aplicación web; ETL, forecasting y jobs son componentes separados que alimentan el modelo.

### 7.1 Autenticación y cuentas

La autenticación de la plataforma será propia y estará respaldada completamente por PostgreSQL; no dependerá de proveedores externos de identidad para iniciar sesión ni crear cuentas.

- **Inicio de sesión:** correo corporativo o usuario registrado más contraseña, validado contra PostgreSQL.
- **Creación de cuentas:** alta de usuario en PostgreSQL con nombre, correo único, nombre de usuario opcional, teléfono opcional, hash de contraseña, rol y estado de activación.
- **Roles:** `cfo`, `analista` y `administrador`, almacenados y validados desde PostgreSQL.
- **Sesiones:** sesión segura gestionada por el backend, con expiración, revocación y protección contra fijación de sesión.
- **Recuperación de acceso:** flujo de recuperación con token temporal de un solo uso y expiración; nunca se devuelve ni se almacena la contraseña original.
- **Seguridad de credenciales:** hash adaptativo con Argon2id o bcrypt, sal por contraseña, política de longitud mínima y protección contra intentos repetidos.
- **Auditoría:** registrar inicio de sesión exitoso, intento fallido, creación de cuenta, cambio de contraseña, cierre de sesión, bloqueo y cambios de rol.
- **Autorización:** el backend debe verificar el rol almacenado en PostgreSQL en cada operación protegida; la vista no es un mecanismo de seguridad.
- **Alta administrativa:** el administrador puede activar, desactivar y cambiar el rol de una cuenta desde la plataforma.
- **Restricción de duplicados:** el correo debe ser único sin distinguir mayúsculas y minúsculas.
- **Perfil:** el usuario puede editar nombre, correo, teléfono y nombre de usuario; los datos sensibles requieren validar la contraseña actual.

---

## 8. Diseño de páginas y UX/UI

Principios: claridad cognitiva, velocidad de análisis y reducción de carga informativa.

**Dashboard Principal (CFO Overview):**

- Jerarquía de lectura:  
  - KPIs clave arriba.  
  - Gráficas de tendencia en el centro.  
  - Alertas, resumen ejecutivo y recomendaciones basadas en reglas a los lados.
- Claridad en alertas y tendencias:  
  - Códigos de color (verde/rojo/amarillo).  
  - Sparklines para evolución inmediata de cada KPI.
- Navegación fluida:  
  - Filtros globales (rango de fechas, área) aplicables a todo el dashboard sin recarga.
- Indicador de actualización visible en todo momento.

**Diseño adaptativo y consistencia visual:**

- Responsivo para escritorios, laptops y tablets ejecutivas.
- Design System limpio: tarjetas de KPI, tablas con paginación, modales de detalle y alertas emergentes.

---

## 9. Fases del proyecto

### Fase 1 — Descubrimiento y diseño (2–3 semanas) XXXXXXXXXXX

- Validar con el CFO catálogo de KPIs y umbrales de alerta.
- Mapeo técnico de fuentes (ERP y banco: API, archivos, BD).
- Diseñar wireframes y modelo de datos (tablas staging y consolidadas).
- Diseñar endpoints de la API.

**Salida:** Arquitectura MVC + prototipo UX/UI + diccionario de datos + catálogo de KPIs aprobado + objetivos medibles.

### Fase 2 — Integración de datos (2–3 semanas) XXXXXXXXXXXXXX

- Scripts de extracción del ERP y del banco (Python).
- Normalización y carga a PostgreSQL (staging → consolidado).
- Programación de ejecución automática y validación de calidad.

**Salida:** Pipeline de datos automático con métricas de calidad y registros de errores.

### Fase 3 — Backend, KPIs y forecasting (3–4 semanas)

- Endpoints FastAPI para cálculo de KPIs.
- Entrenamiento y backtesting del modelo de forecast.
- Lógica de detección de desviaciones y generación de alertas.
- Motor determinista de reglas y plantillas explicables para generar resúmenes y recomendaciones desde alertas, KPIs y forecast calculados.

**Salida:** API funcional que devuelve KPIs, forecast, alertas y recomendaciones.

### Fase 4 — Dashboard / Capa de vista (2–3 semanas)

- Implementación del dashboard en React según UX/UI aprobada.
- Conexión a endpoints de la API.
- Filtros interactivos por periodo/área.
- Vistas diferenciadas por rol.

**Salida:** Dashboard funcional con datos reales y UX validada.

### Fase 5 — Seguridad y despliegue (1–2 semanas)

- Implementación del inicio de sesión y creación de cuentas respaldados por PostgreSQL.
- Hash seguro de contraseñas, expiración y revocación de sesiones.
- Roles almacenados en PostgreSQL y protección de endpoints mediante autorización en backend.
- Auditoría de accesos, intentos fallidos, altas, bajas y cambios de permisos.
- Contenerización con Docker.
- CI/CD con GitHub Actions.

**Salida:** Plataforma desplegada en productivo con acceso controlado.

### Fase 6 — Validación (2 semanas)

- Pruebas funcionales y de usabilidad.
- Pruebas de seguridad.
- UAT con CFO y analista (KPIs, forecast, recomendaciones).

**Salida:** Reporte de pruebas + ajustes aprobados por el CFO.

### Fase 7 — Documentación y entrega (1 semana)

- Documentación técnica (arquitectura, API, modelo de datos).
- Manual de usuario por rol.
- Plan de soporte.

**Salida:** Plataforma en producción + documentación completa.

---

## 10. Criterios de éxito (revisados)

- Forecast a 90 días con **MAE** inferior al objetivo acordado (ej. < 10 % del flujo neto promedio mensual).
- Alertas de desviación con:
  - Precisión y tasa de falsos positivos dentro de umbrales acordados.
  - Tiempo desde dato hasta alerta **< 1 hora**.
- Actualización diaria automática con **≥ 95 % de ejecuciones antes de la hora objetivo**.
- Interfaz validada como intuitiva por el CFO y al menos una recomendación accionable en un ciclo real.
- ≥ 80 % de usuarios de prueba completan tareas principales sin asistencia.

---

## 11. Roadmap posterior (fuera de este PRD)

- Integrar CRM y más fuentes de datos.
- Evaluación de riesgo de crédito/mercado.
- Chat conversacional con búsqueda semántica (RAG).
- Rol de Auditor/Controller.
- Escenarios “qué pasaría si”.
- Multi-empresa.

---

## 12. Requisitos no funcionales

**Rendimiento:**

- Dashboard principal carga en **< 3 segundos** (24 meses de histórico, hasta 100 usuarios).
- API responde al 95 % de solicitudes en **< 500 ms** (excluyendo forecasting pesado).

**Disponibilidad y resiliencia:**

- Disponibilidad objetivo: **≥ 99 %** en horario laboral.
- **RPO ≤ 24 horas**, **RTO ≤ 4 horas**.

**Datos y retención:**

- Histórico inicial: **24 meses**.
- Retención operativa: mínimo **36 meses** para datos consolidados.
- Backups diarios con retención mínima de **7 días**.

**Escalabilidad y volumen:**

- Hasta **100 usuarios registrados** y **20 concurrentes**.
- Hasta **500.000 registros financieros** en el consolidado.

**Compatibilidad y accesibilidad:**

- Últimas 2 versiones de Chrome, Edge, Safari y Firefox.
- Diseño responsivo desde 1280 px hasta tablets.
- Cumplimiento básico de **WCAG 2.1 AA** (contraste, tamaño de fuente, teclado).

**Observabilidad:**

- Logs de acceso, errores y cambios críticos retenidos ≥ 90 días.
- Métricas de salud del servicio en tiempo real.

**Límites de resúmenes y recomendaciones:**

- No se utiliza IA generativa ni se realizan llamadas a servicios externos de IA.
- Las salidas se construyen únicamente con reglas y plantillas versionadas; cada recomendación debe mostrar sus datos de evidencia.
- Si faltan alertas, KPIs o un forecast válido, el sistema debe indicarlo y no inferir ni inventar resultados.

---

## 13. Catálogo de KPIs (estructura y ejemplos concretos)

Cada KPI se define con:

- Nombre  
- Fórmula  
- Fuente de cada dato  
- Periodicidad  
- Nivel de agregación  
- Moneda y tipo de cambio  
- Tratamiento de datos faltantes  
- Ejemplo de resultado  
- Responsable de validación  

### 13.1 Liquidez

**KPI-01 — Saldo de caja actual**

- Fórmula: Suma de saldos finales de cuentas bancarias consolidadas.  
- Fuente: Banco.  
- Periodicidad: Diaria.  
- Nivel: Empresa.  
- Moneda: Moneda local; otras monedas convertidas con tipo de cambio oficial del día.  
- Datos faltantes: Si falta el saldo de una cuenta, el KPI se marca como “parcial” con advertencia.  
- Ejemplo: 1.250.000 USD.  
- Responsable: Analista financiero.

**KPI-02 — Días de caja (Cash Runway)**

- Fórmula: Saldo de caja actual / promedio diario de salidas de los últimos 30 días.  
- Fuente: Banco (saldo y movimientos).  
- Periodicidad: Diaria.  
- Nivel: Empresa.  
- Moneda: Moneda local.  
- Datos faltantes: Si no hay 30 días de histórico, no se calcula y se muestra motivo.  
- Ejemplo: 45 días.  
- Responsable: CFO.

**KPI-03 — Razón corriente (Current Ratio)**

- Fórmula: Activo corriente / Pasivo corriente.  
- Fuente: ERP (balance).  
- Periodicidad: Mensual.  
- Nivel: Empresa.  
- Moneda: Moneda local.  
- Datos faltantes: Si falta activo o pasivo corriente, no se calcula y se marca como “no disponible”.  
- Ejemplo: 1,8.  
- Responsable: CFO.

**KPI-04 — Razón rápida (Quick Ratio)**

- Fórmula: (Activo corriente – Inventarios) / Pasivo corriente.  
- Fuente: ERP (balance).  
- Periodicidad: Mensual.  
- Nivel: Empresa.  
- Moneda: Moneda local.  
- Datos faltantes: Igual que KPI-03.  
- Ejemplo: 1,2.  
- Responsable: CFO.

### 13.2 Rentabilidad

**KPI-05 — Margen neto**

- Fórmula: Utilidad neta / Ingresos totales.  
- Fuente: ERP (estado de resultados).  
- Periodicidad: Mensual.  
- Nivel: Empresa.  
- Moneda: Moneda local.  
- Datos faltantes: Si falta utilidad o ingresos, no se calcula.  
- Ejemplo: 12 %.  
- Responsable: CFO.

**KPI-06 — ROE (Return on Equity)**

- Fórmula: Utilidad neta / Patrimonio promedio.  
- Fuente: ERP (estado de resultados y balance).  
- Periodicidad: Mensual.  
- Nivel: Empresa.  
- Moneda: Moneda local.  
- Datos faltantes: Si falta utilidad o patrimonio, no se calcula.  
- Ejemplo: 18 %.  
- Responsable: CFO.

**KPI-07 — ROA (Return on Assets)**

- Fórmula: Utilidad neta / Activo total promedio.  
- Fuente: ERP.  
- Periodicidad: Mensual.  
- Nivel: Empresa.  
- Moneda: Moneda local.  
- Datos faltantes: Si falta utilidad o activo total, no se calcula.  
- Ejemplo: 9 %.  
- Responsable: CFO.

### 13.3 Cumplimiento presupuestal

**KPI-08 — Desviación presupuestal global**

- Fórmula: (Real – Presupuesto) / Presupuesto (total empresa).  
- Fuente: ERP (presupuesto y real).  
- Periodicidad: Mensual (acumulado año a la fecha).  
- Nivel: Empresa.  
- Moneda: Moneda local.  
- Datos faltantes: Si no hay presupuesto definido, no se calcula.  
- Ejemplo: +5 % (sobrepresupuesto).  
- Responsable: CFO.

**KPI-09 — Desviación presupuestal por área**

- Fórmula: (Real – Presupuesto) / Presupuesto, por área.  
- Fuente: ERP (presupuesto y real por área).  
- Periodicidad: Mensual (acumulado YTD).  
- Nivel: Área.  
- Moneda: Moneda local.  
- Datos faltantes: Si falta presupuesto para un área, no se calcula para esa área.  
- Ejemplo: Comercial +12 %, Operaciones –3 %.  
- Responsable: CFO.

**KPI-10 — Desviación presupuestal por línea de gasto clave**

- Fórmula: (Real – Presupuesto) / Presupuesto, por línea (ej. viajes, marketing, TI).  
- Fuente: ERP.  
- Periodicidad: Mensual (YTD).  
- Nivel: Línea de gasto.  
- Moneda: Moneda local.  
- Datos faltantes: Igual que KPI-09.  
- Ejemplo: Viajes +25 %.  
- Responsable: Analista financiero.

### 13.4 Eficiencia operativa (opcional para MVP, pero definido)

**KPI-11 — DSO (Días de cartera)**

- Fórmula: (Cuentas por cobrar / Ventas a crédito) × número de días del periodo.  
- Fuente: ERP.  
- Periodicidad: Mensual.  
- Nivel: Empresa.  
- Moneda: Moneda local.  
- Datos faltantes: Si falta cartera o ventas a crédito, no se calcula.  
- Ejemplo: 42 días.  
- Responsable: CFO.

**KPI-12 — DPO (Días de proveedor)**

- Fórmula: (Cuentas por pagar / Compras a crédito) × número de días del periodo.  
- Fuente: ERP.  
- Periodicidad: Mensual.  
- Nivel: Empresa.  
- Moneda: Moneda local.  
- Datos faltantes: Si falta cartera de proveedores o compras a crédito, no se calcula.  
- Ejemplo: 55 días.  
- Responsable: CFO.

*(El catálogo puede ampliarse en v2; para MVP se priorizará un subconjunto acordado con el CFO.)*

---

## 14. Especificación del forecast (flujo de caja a 90 días)

**Qué se pronostica:**

- Flujo neto diario (entradas – salidas) y saldo proyectado de caja.

**Horizonte y granularidad:**

- Horizonte: **90 días** desde la fecha de corte.  
- Granularidad: **diaria**, con vistas agregadas a 30, 60 y 90 días.

**Modelo inicial:**

- Modelo estadístico (ARIMA / Prophet / regresión con estacionalidad semanal y mensual) entrenado con ≥ 12 meses de histórico.  
- Variables: histórico de entradas, salidas y saldo; opcionalmente indicadores internos (ciclo de facturación, estacionalidad).

**Eventos extraordinarios:**

- Movimientos atípicos se marcarán y podrán excluirse del entrenamiento bajo supervisión del analista.

**Métrica de evaluación:**

- **MAE** del flujo neto a 30 días como métrica principal.  
- Secundarias: RMSE y MAPE para análisis interno.

**Backtesting:**

- Sobre los últimos **6–12 meses**, simulando predicciones a 30/60/90 días.

**Intervalo de confianza:**

- Se mostrará un intervalo (ej. 80 %) alrededor de la proyección, explicado como “rango probable”.

**Falta de datos históricos:**

- Si hay < 6 meses de histórico, el forecast se desactiva con mensaje explicativo.

---

## 15. Especificación de alertas

**Tipo de alerta (MVP):**

- Desviación presupuestal por encima de umbral configurable.

**Estructura de una alerta:**

- Periodo (mes/año).  
- Área o centro de costo.  
- Concepto (línea presupuestaria).  
- Monto presupuestado.  
- Monto real.  
- Porcentaje de desviación.  
- Severidad (baja, media, alta).  
- Fecha de detección.  
- Estado (nueva, en revisión, cerrada, falsa).  
- Responsable asignado.

**Reglas de generación:**

- Se ejecutan tras cada sincronización diaria.  
- Se generan si la desviación supera el umbral (ej. ±10 % y ±20 % para severidad media y alta).  
- Deduplicación por periodo + área + concepto; se actualiza la alerta existente si persiste.

**Métricas de alertas:**

- Precisión de alertas.  
- Tasa de falsos positivos.  
- Tiempo desde dato hasta alerta.  
- Porcentaje de alertas revisadas y cerradas en plazo acordado (ej. 5 días hábiles).

**“Atender alertas” (analista):**

- Revisar detalle numérico.  
- Añadir comentarios.  
- Asignar responsable.  
- Marcar como falsa si corresponde.  
- Cerrar cuando esté resuelta o justificada.

---

## 16. Resumen ejecutivo y recomendaciones con reglas explicables

**Alcance:**

- Generar un **resumen ejecutivo** y **recomendaciones** mediante reglas deterministas y plantillas a partir de alertas activas, KPIs calculados y forecast disponible.
- Identificar las reglas que se activaron y vincular cada resultado con el periodo y las métricas de origen.
- No se utiliza IA generativa, LLM, Azure OpenAI ni otro servicio de pago. No se ofrecen preguntas abiertas o guiadas en este MVP.

**Controles de explicabilidad y confianza:**

- Las reglas solo usan datos ya calculados y autorizados.
- Cada recomendación muestra:
  - Periodo de referencia.  
  - Métricas de origen.  
- Regla que la generó y evidencia asociada.
- Distingue claramente entre **hechos** e **interpretaciones de regla**.
- Indica cuando **no hay datos suficientes**.  
- No inventa cifras ni periodos; no genera conclusiones si faltan sus datos requeridos.
- Las recomendaciones **no ejecutan acciones automáticamente**.

**Auditoría:**

- Se registra la versión de la regla, la evidencia utilizada, la respuesta, la fecha y el usuario cuando corresponda.

**Privacidad:**

- Los datos financieros no se envían a proveedores externos de IA.

**Estructura de una recomendación:**

- Situación.  
- Impacto (cuantificado si es posible).  
- Recomendación (acción concreta).  
- Prioridad (alta, media, baja).  
- Evidencia (referencia a KPIs y alertas).

---

## 17. Historias de usuario prioritarias (MVP)

**Forecast y caja:**

- Como CFO, quiero ver el saldo de caja actual y proyectado a 90 días para decidir si puedo asumir un pago extraordinario.  
- Como CFO, quiero ver el intervalo de confianza del forecast para entender el grado de incertidumbre.

**Datos y calidad:**

- Como analista, quiero revisar los registros rechazados de la sincronización para corregir problemas de calidad.  
- Como analista, quiero ver un resumen diario de la ejecución de las cargas (éxito/errores) para asegurar que los datos están actualizados.

**Alertas:**

- Como analista, quiero configurar umbrales de desviación por tipo de KPI y área.  
- Como analista, quiero atender alertas (revisar, comentar, asignar, cerrar, marcar como falsa) desde el dashboard.

**Resumen y recomendaciones:**

- Como CFO, quiero ver la regla y evidencia numérica detrás de cada recomendación para entender por qué se generó.
- Como CFO, quiero recibir un resumen y recomendaciones basados en alertas, KPIs y forecast calculados con datos reales, sin depender de servicios de IA de pago.

**General:**

- Como usuario, quiero saber cuándo se actualizaron por última vez los datos mostrados.  
- Como usuario, quiero iniciar sesión con una cuenta registrada en PostgreSQL para acceder a la plataforma.
- Como usuario, quiero crear una cuenta con mi correo, nombre y contraseña para acceder posteriormente.
- Como usuario, quiero cerrar sesión y recuperar mi acceso mediante un flujo seguro.
- Como administrador, quiero gestionar usuarios y roles desde la plataforma.

---

## 18. MVP vs. post-MVP

**MVP imprescindible:**

- 1 integración ERP + 1 banco.  
- Carga diaria automatizada.  
- Catálogo limitado de KPIs (liquidez, rentabilidad, desviación presupuestal).  
- Forecast básico de flujo de caja a 90 días.  
- Alertas de desviación presupuestal.  
- Dashboard CFO.  
- Autenticación PostgreSQL y 3 roles.  
- Auditoría básica y manejo de errores.

**Post-MVP:**

- Preguntas guiadas avanzadas.  
- Recomendaciones más sofisticadas.  
- Más fuentes (CRM, otros bancos, sistemas internos).  
- Escenarios “qué pasaría si”.  
- RAG sobre documentos financieros.  
- Multiempresa.  
- Rol de auditor.

---

## 19. Dependencias y supuestos

**Dependencias:**

- TI o proveedor del ERP: credenciales de solo lectura y documentación de datos.  
- Banco: acceso a extractos o API con histórico ≥ 24 meses.  
- CFO y equipo financiero: definición de presupuesto, validación de KPIs y umbrales, datos históricos y contexto de eventos extraordinarios.  
- Seguridad/TI: definición de política de contraseñas, cifrado, gestión de secretos y protección de sesiones.  
- Infraestructura: políticas de backup y recuperación; no se requiere una suscripción de IA generativa.

**Supuestos:**

- ERP y banco tienen disponibilidad suficiente para extracciones diarias.  
- Existe histórico mínimo de **12 meses** para entrenar el forecast.  
- CFO y analista estarán disponibles para UAT y validación.
```