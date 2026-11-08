CREATE TABLE IF NOT EXISTS reportes_resumen (
    id              BIGSERIAL PRIMARY KEY,
    fecha_resumen   DATE NOT NULL,
    periodo_desde   DATE NOT NULL,
    periodo_hasta   DATE NOT NULL,
    tipo_reporte    VARCHAR(20) NOT NULL CHECK (tipo_reporte IN ('mensual', 'manual')),
    instantanea     JSONB NOT NULL,
    generado_por    UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    generado_en     TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (periodo_desde <= periodo_hasta),
    CHECK (fecha_resumen = periodo_hasta)
);

CREATE INDEX IF NOT EXISTS reportes_resumen_fecha_idx
    ON reportes_resumen (fecha_resumen DESC, generado_en DESC);

CREATE UNIQUE INDEX IF NOT EXISTS reportes_resumen_mensual_periodo_key
    ON reportes_resumen (periodo_desde, periodo_hasta)
    WHERE tipo_reporte = 'mensual';
