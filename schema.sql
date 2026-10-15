-- ============================================================================
-- Esquema de Base de Datos — Plataforma de Inteligencia Financiera para CFO
-- Motor: PostgreSQL 15+
-- ============================================================================
-- Organización del esquema:
--   1. Seguridad, usuarios, credenciales y sesiones
--   2. Ingesta de datos (staging / trazabilidad de sincronización)
--   3. Datos financieros consolidados (núcleo)
--   4. KPIs
--   5. Forecasting
--   6. Alertas
--   7. IA generativa (recomendaciones y feedback)
--   8. Auditoría
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto"; -- necesario para gen_random_uuid()

-- ============================================================================
-- Tipos enumerados
-- ============================================================================
CREATE TYPE rol_usuario     AS ENUM ('cfo', 'analista', 'administrador');
CREATE TYPE fuente_tipo     AS ENUM ('erp', 'banco');
CREATE TYPE estado_sincronizacion AS ENUM ('pendiente', 'en_proceso', 'exitoso', 'fallido');
CREATE TYPE severidad_alerta AS ENUM ('baja', 'media', 'alta');
CREATE TYPE estado_alerta  AS ENUM ('nueva', 'en_revision', 'cerrada', 'falsa');
CREATE TYPE tipo_feedback  AS ENUM ('util', 'no_util');
CREATE TYPE prioridad_recomendacion AS ENUM ('alta', 'media', 'baja');

-- ============================================================================
-- FUNCIÓN DE SOPORTE: mantener actualizado_en al día en cada UPDATE
-- ============================================================================
CREATE OR REPLACE FUNCTION set_actualizado_en()
RETURNS TRIGGER AS $$
BEGIN
    NEW.actualizado_en = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
COMMENT ON FUNCTION set_actualizado_en() IS 'Trigger genérico: fija actualizado_en = now() en cada UPDATE. Se reutiliza en todas las tablas que tienen esa columna.';

-- ============================================================================
-- 1. SEGURIDAD Y USUARIOS
-- ============================================================================

CREATE TABLE usuarios (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    correo          VARCHAR(255) NOT NULL,
    nombre_completo VARCHAR(255) NOT NULL,
    rol             rol_usuario NOT NULL DEFAULT 'analista',
    esta_activo     BOOLEAN NOT NULL DEFAULT TRUE,
    correo_verificado BOOLEAN NOT NULL DEFAULT FALSE,
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_en  TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE usuarios IS 'Cuentas y perfiles de la plataforma; PostgreSQL es la fuente de identidad y autorización.';

CREATE UNIQUE INDEX usuarios_correo_minusculas_key ON usuarios (lower(correo));

CREATE TRIGGER trg_usuarios_actualizado_en
BEFORE UPDATE ON usuarios
FOR EACH ROW EXECUTE FUNCTION set_actualizado_en();

CREATE TABLE credenciales_usuario (
    usuario_id              UUID PRIMARY KEY REFERENCES usuarios(id) ON DELETE CASCADE,
    hash_contrasena         VARCHAR(255) NOT NULL,
    contrasena_cambiada_en  TIMESTAMPTZ NOT NULL DEFAULT now(),
    intentos_fallidos_inicio_sesion INT NOT NULL DEFAULT 0 CHECK (intentos_fallidos_inicio_sesion >= 0),
    bloqueado_hasta         TIMESTAMPTZ,
    ultimo_inicio_sesion_en TIMESTAMPTZ,
    creado_en               TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_en          TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE credenciales_usuario IS 'Credenciales locales; hash_contrasena debe contener un hash Argon2id o bcrypt, nunca una contraseña en texto plano.';

CREATE TRIGGER trg_credenciales_usuario_actualizado_en
BEFORE UPDATE ON credenciales_usuario
FOR EACH ROW EXECUTE FUNCTION set_actualizado_en();

CREATE TABLE sesiones_autenticacion (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id      UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    hash_token      VARCHAR(255) UNIQUE NOT NULL,
    agente_usuario  TEXT,
    direccion_ip    INET,
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT now(),
    ultimo_acceso_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    expira_en       TIMESTAMPTZ NOT NULL,
    revocado_en     TIMESTAMPTZ,
    CHECK (expira_en > creado_en)
);
COMMENT ON TABLE sesiones_autenticacion IS 'Sesiones activas o revocadas; el token original solo vive en la cookie segura del cliente y aquí se guarda su hash.';

CREATE TABLE tokens_reinicio_contrasena (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id      UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    hash_token      VARCHAR(255) UNIQUE NOT NULL,
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT now(),
    expira_en       TIMESTAMPTZ NOT NULL,
    usado_en        TIMESTAMPTZ,
    CHECK (expira_en > creado_en)
);
COMMENT ON TABLE tokens_reinicio_contrasena IS 'Tokens de recuperación de un solo uso y con expiración; nunca almacena el token original.';

-- ============================================================================
-- 2. INGESTA DE DATOS (staging y trazabilidad)
-- ============================================================================

CREATE TABLE fuentes_datos (
    id                  SERIAL PRIMARY KEY,
    nombre              VARCHAR(100) NOT NULL,
    tipo                fuente_tipo NOT NULL,
    configuracion_conexion JSONB,            -- config no sensible; credenciales van en un vault, no aquí
    esta_activa          BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE registros_sincronizacion (
    id              BIGSERIAL PRIMARY KEY,
    fuente_datos_id INT NOT NULL REFERENCES fuentes_datos(id),
    iniciado_en     TIMESTAMPTZ NOT NULL DEFAULT now(),
    finalizado_en   TIMESTAMPTZ,
    estado          estado_sincronizacion NOT NULL DEFAULT 'pendiente',
    filas_ingresadas INT,
    filas_rechazadas INT NOT NULL DEFAULT 0 CHECK (filas_rechazadas >= 0),
    mensaje_error   TEXT
);
COMMENT ON TABLE registros_sincronizacion IS 'Historial de cada corrida de ETL: cuándo, de qué fuente, si tuvo éxito, cuántos registros trajo y cuántos rechazó (métrica de calidad, objetivo < 1% del PRD).';

CREATE TABLE registros_sincronizacion_rechazados (
    id              BIGSERIAL PRIMARY KEY,
    registro_sincronizacion_id BIGINT NOT NULL REFERENCES registros_sincronizacion(id) ON DELETE CASCADE,
    carga_cruda     JSONB NOT NULL,     -- fila original que no pasó validación/normalización
    motivo_rechazo  TEXT NOT NULL,      -- ej. 'cuenta_no_encontrada', 'monto_invalido', 'fecha_faltante'
    ingresado_en    TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE registros_sincronizacion_rechazados IS 'Detalle de cada fila rechazada durante una corrida de ETL, para que el analista pueda revisarlas y corregir problemas de calidad (historia de usuario de la sección 17 del PRD).';

CREATE TABLE datos_temporales_erp (
    id              BIGSERIAL PRIMARY KEY,
    registro_sincronizacion_id BIGINT REFERENCES registros_sincronizacion(id),
    carga_cruda     JSONB NOT NULL,     -- dato tal cual llega del ERP, sin transformar
    ingresado_en    TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE datos_temporales_erp IS 'Staging crudo del ERP. Crece indefinidamente si no se purga: definir job periódico (ej. borrar/archivar filas con ingresado_en más viejo que N meses) o particionar por rango de ingresado_en.';

CREATE TABLE datos_temporales_banco (
    id              BIGSERIAL PRIMARY KEY,
    registro_sincronizacion_id BIGINT REFERENCES registros_sincronizacion(id),
    carga_cruda     JSONB NOT NULL,     -- dato tal cual llega del banco, sin transformar
    ingresado_en    TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE datos_temporales_banco IS 'Staging crudo del banco. Misma recomendación de retención/particionamiento que datos_temporales_erp.';

-- ============================================================================
-- 3. DATOS FINANCIEROS CONSOLIDADOS (núcleo)
-- ============================================================================

CREATE TABLE centros_costo (
    id      SERIAL PRIMARY KEY,
    codigo  VARCHAR(50) UNIQUE NOT NULL,
    nombre  VARCHAR(150) NOT NULL
);
COMMENT ON TABLE centros_costo IS 'Centros de costo / áreas de la empresa (ventas, operaciones, etc.).';

CREATE TABLE cuentas (
    id          SERIAL PRIMARY KEY,
    codigo      VARCHAR(50) UNIQUE NOT NULL,
    nombre      VARCHAR(150) NOT NULL,
    categoria   VARCHAR(50) NOT NULL    -- activo, pasivo, ingreso, egreso, capital
);
COMMENT ON TABLE cuentas IS 'Catálogo de cuentas contables consolidado desde el ERP.';

CREATE TABLE transacciones (
    id                  BIGSERIAL PRIMARY KEY,
    cuenta_id           INT NOT NULL REFERENCES cuentas(id),
    centro_costo_id     INT REFERENCES centros_costo(id),
    fuente_datos_id     INT NOT NULL REFERENCES fuentes_datos(id),
    tipo_fuente         fuente_tipo NOT NULL,
    referencia_fuente   VARCHAR(255) NOT NULL,  -- identificador original del movimiento dentro de su fuente
    monto               NUMERIC(18,2) NOT NULL,
    moneda              CHAR(3) NOT NULL DEFAULT 'MXN' CHECK (moneda ~ '^[A-Z]{3}$'),
    fecha_transaccion   DATE NOT NULL,
    descripcion         TEXT,
    creado_en           TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (fuente_datos_id, referencia_fuente)
);
COMMENT ON TABLE transacciones IS 'Movimientos financieros reales, ya normalizados desde ERP y banco. Es la tabla más grande y más consultada.';

CREATE TABLE presupuestos (
    id                  BIGSERIAL PRIMARY KEY,
    cuenta_id           INT NOT NULL REFERENCES cuentas(id),
    centro_costo_id     INT REFERENCES centros_costo(id),
    periodo             DATE NOT NULL,      -- primer día del mes que representa
    monto_presupuestado NUMERIC(18,2) NOT NULL,
    version             INT NOT NULL DEFAULT 1,   -- para versionar escenarios de presupuesto
    creado_en           TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE NULLS NOT DISTINCT (cuenta_id, centro_costo_id, periodo, version)
);
COMMENT ON TABLE presupuestos IS 'Presupuesto por cuenta/centro de costo/periodo. El campo version permite comparar escenarios (original vs. revisado).';

-- ============================================================================
-- 4. KPIs
-- ============================================================================

CREATE TABLE definiciones_kpi (
    id                      SERIAL PRIMARY KEY,
    codigo                  VARCHAR(50) UNIQUE NOT NULL,   -- ej. 'margen_ebitda'
    nombre                  VARCHAR(150) NOT NULL,
    categoria               VARCHAR(50) NOT NULL,          -- liquidez, rentabilidad, presupuesto, riesgo
    descripcion_formula     TEXT
);

CREATE TABLE valores_kpi (
    id                  BIGSERIAL PRIMARY KEY,
    definicion_kpi_id   INT NOT NULL REFERENCES definiciones_kpi(id),
    centro_costo_id     INT REFERENCES centros_costo(id),   -- NULL = consolidado a nivel empresa
    periodo             DATE NOT NULL,
    valor               NUMERIC(18,4) NOT NULL,
    calculado_en        TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE NULLS NOT DISTINCT (definicion_kpi_id, centro_costo_id, periodo)
);
COMMENT ON TABLE valores_kpi IS 'Valor ya calculado de cada KPI por periodo; el dashboard lee de aquí, no recalcula en caliente.';

-- ============================================================================
-- 5. FORECASTING
-- ============================================================================

CREATE TABLE ejecuciones_pronostico (
    id                      BIGSERIAL PRIMARY KEY,
    nombre_modelo           VARCHAR(100) NOT NULL,     -- ej. 'prophet_cashflow_v1'
    ejecutado_en            TIMESTAMPTZ NOT NULL DEFAULT now(),
    datos_entrenamiento_desde DATE NOT NULL,
    datos_entrenamiento_hasta DATE NOT NULL,
    notas                   TEXT
);
COMMENT ON TABLE ejecuciones_pronostico IS 'Cada vez que se corre el modelo de proyección queda registrada aquí, para poder comparar versiones del modelo.';

CREATE TABLE valores_pronostico (
    id                  BIGSERIAL PRIMARY KEY,
    ejecucion_pronostico_id BIGINT NOT NULL REFERENCES ejecuciones_pronostico(id),
    fecha_objetivo      DATE NOT NULL,
    valor_predicho      NUMERIC(18,2) NOT NULL,
    limite_inferior     NUMERIC(18,2),      -- límite inferior del intervalo de confianza
    limite_superior     NUMERIC(18,2),      -- límite superior del intervalo de confianza
    UNIQUE (ejecucion_pronostico_id, fecha_objetivo)
);

-- ============================================================================
-- 6. ALERTAS
-- ============================================================================

CREATE TABLE umbrales_alerta (
    id                  SERIAL PRIMARY KEY,
    cuenta_id           INT REFERENCES cuentas(id),          -- NULL = aplica a todas las cuentas/líneas de gasto
    centro_costo_id     INT REFERENCES centros_costo(id),    -- NULL = aplica a toda la empresa
    desviacion_maxima_pct NUMERIC(5,2) NOT NULL,              -- ej. 8.00 = 8%
    severidad           severidad_alerta NOT NULL DEFAULT 'media',
    esta_activo         BOOLEAN NOT NULL DEFAULT TRUE
);
COMMENT ON TABLE umbrales_alerta IS 'Umbrales configurables por el CFO/admin (ej. ±10% media, ±20% alta), por cuenta/línea de gasto y/o centro de costo; NO deben quedar fijos en el código.';

CREATE TABLE alertas (
    id                  BIGSERIAL PRIMARY KEY,
    cuenta_id           INT NOT NULL REFERENCES cuentas(id),          -- concepto / línea presupuestaria
    centro_costo_id     INT REFERENCES centros_costo(id),             -- área
    periodo             DATE NOT NULL,
    monto_presupuestado NUMERIC(18,2) NOT NULL,
    monto_real          NUMERIC(18,2) NOT NULL,
    desviacion_pct      NUMERIC(6,2) NOT NULL,
    severidad           severidad_alerta NOT NULL,
    estado              estado_alerta NOT NULL DEFAULT 'nueva',
    detectado_en        TIMESTAMPTZ NOT NULL DEFAULT now(),
    responsable_id       UUID REFERENCES usuarios(id),                -- responsable asignado (puede diferir de quién la atendió)
    atendido_por        UUID REFERENCES usuarios(id),
    atendido_en         TIMESTAMPTZ,
    comentario          TEXT,
    UNIQUE NULLS NOT DISTINCT (periodo, centro_costo_id, cuenta_id)   -- deduplicación también cuando centro_costo_id es NULL
);
COMMENT ON TABLE alertas IS 'Alertas de desviación presupuestal (periodo + área + concepto), con montos presupuestado/real, severidad, estado del flujo de atención y responsable asignado, según sección 15 del PRD.';

-- ============================================================================
-- 7. IA GENERATIVA
-- ============================================================================

CREATE TABLE recomendaciones_ia (
    id                  BIGSERIAL PRIMARY KEY,
    usuario_id          UUID REFERENCES usuarios(id),   -- quién la solicitó/consumió; NULL si fue generada por un job programado
    periodo             DATE NOT NULL,
    situacion           TEXT NOT NULL,          -- descripción del hecho detectado
    impacto             TEXT,                   -- impacto cuantificado cuando sea posible
    recomendacion_texto TEXT NOT NULL,          -- acción concreta recomendada
    prioridad           prioridad_recomendacion NOT NULL DEFAULT 'media',
    evidencia           JSONB,                  -- referencias a valores_kpi.id / alertas.id que sustentan la recomendación
    version_prompt      VARCHAR(50) NOT NULL,   -- versión del prompt/plantilla usada (distinta del texto completo)
    prompt_utilizado    TEXT NOT NULL,      -- se guarda para trazabilidad/auditoría
    texto_generado      TEXT NOT NULL,
    nombre_modelo       VARCHAR(100) NOT NULL,   -- ej. 'gpt-4o-mini'
    generado_en         TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE recomendaciones_ia IS 'Cada resumen/recomendación generado por el servicio de IA: situación, impacto, recomendación, prioridad y evidencia (sección 16 del PRD), con prompt exacto, versión del prompt, modelo y usuario, para trazabilidad/auditoría y explicabilidad.';

CREATE TABLE retroalimentacion_ia (
    id                  BIGSERIAL PRIMARY KEY,
    recomendacion_id    BIGINT NOT NULL REFERENCES recomendaciones_ia(id),
    usuario_id          UUID NOT NULL REFERENCES usuarios(id),
    retroalimentacion   tipo_feedback NOT NULL,
    comentario          TEXT,
    creado_en           TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE retroalimentacion_ia IS 'Feedback del CFO sobre cada recomendación, para medir utilidad y ajustar el prompt/modelo con el tiempo.';

-- ============================================================================
-- 8. AUDITORÍA
-- ============================================================================

CREATE TABLE registro_auditoria (
    id              BIGSERIAL PRIMARY KEY,
    usuario_id      UUID REFERENCES usuarios(id),
    accion          VARCHAR(100) NOT NULL,     -- ej. 'inicio_sesion', 'sincronizacion_disparada', 'alerta_atendida'
    tipo_entidad    VARCHAR(50),
    id_entidad      VARCHAR(50),
    detalles        JSONB,
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE registro_auditoria IS 'Bitácora general de acciones relevantes de usuarios en la plataforma. Tabla de alto crecimiento: considerar particionar por rango de creado_en (mensual/anual) y definir política de retención/archivado.';

-- ============================================================================
-- ÍNDICES (consultas más frecuentes del dashboard)
-- ============================================================================

CREATE INDEX idx_transacciones_fecha         ON transacciones (fecha_transaccion);
CREATE INDEX idx_transacciones_cuenta        ON transacciones (cuenta_id);
CREATE INDEX idx_transacciones_centro_costo  ON transacciones (centro_costo_id);
-- Compuesto: cubre filtros combinados de fecha + cuenta, comunes en reportes del dashboard
CREATE INDEX idx_transacciones_fecha_cuenta  ON transacciones (fecha_transaccion, cuenta_id);
-- La restricción UNIQUE (fuente_datos_id, referencia_fuente) ya crea un índice útil por fuente.
-- GIN sobre JSONB para filtrar/auditar por claves específicas dentro de la carga cruda o config
CREATE INDEX idx_fuentes_datos_config_gin        ON fuentes_datos USING GIN (configuracion_conexion);
CREATE INDEX idx_datos_temporales_erp_carga_gin  ON datos_temporales_erp USING GIN (carga_cruda);
CREATE INDEX idx_datos_temporales_banco_carga_gin ON datos_temporales_banco USING GIN (carga_cruda);
CREATE INDEX idx_registro_auditoria_detalles_gin ON registro_auditoria USING GIN (detalles);
CREATE INDEX idx_presupuestos_periodo        ON presupuestos (periodo);
CREATE INDEX idx_valores_kpi_periodo         ON valores_kpi (periodo);
CREATE INDEX idx_valores_kpi_definicion      ON valores_kpi (definicion_kpi_id);
CREATE INDEX idx_valores_pronostico_ejecucion ON valores_pronostico (ejecucion_pronostico_id);
CREATE INDEX idx_alertas_estado              ON alertas (estado);
CREATE INDEX idx_alertas_periodo             ON alertas (periodo);
CREATE INDEX idx_alertas_cuenta              ON alertas (cuenta_id);
CREATE INDEX idx_alertas_responsable         ON alertas (responsable_id);
CREATE INDEX idx_umbrales_alerta_cuenta      ON umbrales_alerta (cuenta_id);
CREATE INDEX idx_umbrales_alerta_centro_costo ON umbrales_alerta (centro_costo_id);
CREATE INDEX idx_recomendaciones_ia_periodo  ON recomendaciones_ia (periodo);
CREATE INDEX idx_recomendaciones_ia_usuario  ON recomendaciones_ia (usuario_id);
CREATE INDEX idx_recomendaciones_ia_evidencia_gin ON recomendaciones_ia USING GIN (evidencia);
CREATE INDEX idx_registro_auditoria_usuario  ON registro_auditoria (usuario_id);
CREATE INDEX idx_registros_sincronizacion_fuente ON registros_sincronizacion (fuente_datos_id);
CREATE INDEX idx_registros_rechazados_sincronizacion ON registros_sincronizacion_rechazados (registro_sincronizacion_id);
CREATE INDEX idx_registros_rechazados_carga_gin ON registros_sincronizacion_rechazados USING GIN (carga_cruda);
CREATE INDEX idx_sesiones_autenticacion_usuario ON sesiones_autenticacion (usuario_id);
CREATE INDEX idx_sesiones_autenticacion_activas ON sesiones_autenticacion (usuario_id, expira_en) WHERE revocado_en IS NULL;
CREATE INDEX idx_tokens_reinicio_usuario     ON tokens_reinicio_contrasena (usuario_id, expira_en);
