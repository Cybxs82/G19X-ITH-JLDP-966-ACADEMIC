ALTER TABLE presupuestos
    ADD COLUMN IF NOT EXISTS fuente_datos_id INT REFERENCES fuentes_datos(id);

ALTER TABLE presupuestos
    DROP CONSTRAINT IF EXISTS presupuestos_cuenta_id_centro_costo_id_periodo_version_key;

CREATE UNIQUE INDEX IF NOT EXISTS idx_presupuestos_fuente_unica
    ON presupuestos (
        cuenta_id,
        centro_costo_id,
        periodo,
        version,
        fuente_datos_id
    )
    NULLS NOT DISTINCT;

WITH practice_budget_rows AS (
    SELECT DISTINCT b.id AS presupuesto_id, f.id AS fuente_datos_id
    FROM presupuestos b
    JOIN cuentas c ON c.id = b.cuenta_id
    JOIN centros_costo cc ON cc.id = b.centro_costo_id
    JOIN datos_temporales_erp dte
      ON dte.carga_cruda->>'file_name' LIKE 'practica\_%' ESCAPE '\'
    JOIN registros_sincronizacion rs
      ON rs.id = dte.registro_sincronizacion_id
    JOIN fuentes_datos f
      ON f.id = rs.fuente_datos_id
     AND f.nombre = dte.carga_cruda->>'file_name'
    WHERE b.fuente_datos_id IS NULL
      AND f.tipo = 'erp'::fuente_tipo
      AND lower(f.nombre) LIKE 'practica\_%' ESCAPE '\'
      AND c.codigo = dte.carga_cruda #>> '{values,cuenta}'
      AND cc.codigo = dte.carga_cruda #>> '{values,centro_costo}'
      AND b.periodo = date_trunc(
          'month',
          (dte.carga_cruda #>> '{values,periodo}')::date
      )::date
      AND b.monto_presupuestado = (dte.carga_cruda #>> '{values,monto_presupuestado}')::numeric
), unambiguous_practice_budgets AS (
    SELECT presupuesto_id, MIN(fuente_datos_id) AS fuente_datos_id
    FROM practice_budget_rows
    GROUP BY presupuesto_id
    HAVING COUNT(DISTINCT fuente_datos_id) = 1
)
UPDATE presupuestos b
SET fuente_datos_id = u.fuente_datos_id
FROM unambiguous_practice_budgets u
WHERE b.id = u.presupuesto_id;
