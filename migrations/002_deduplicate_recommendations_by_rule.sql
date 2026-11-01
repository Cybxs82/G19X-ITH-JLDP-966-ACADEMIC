BEGIN;

WITH ranked_recommendations AS (
    SELECT
        id,
        first_value(usuario_id) OVER (
            PARTITION BY periodo, evidencia->>'regla'
            ORDER BY (usuario_id IS NOT NULL) DESC, generado_en DESC, id DESC
        ) AS preferred_user_id,
        row_number() OVER (
            PARTITION BY periodo, evidencia->>'regla'
            ORDER BY generado_en DESC, id DESC
        ) AS row_number
    FROM recomendaciones_ia
    WHERE evidencia->>'regla' IS NOT NULL
)
UPDATE recomendaciones_ia recommendation
SET usuario_id = ranked.preferred_user_id
FROM ranked_recommendations ranked
WHERE recommendation.id = ranked.id
  AND ranked.row_number = 1;

WITH ranked_recommendations AS (
    SELECT
        id,
        first_value(id) OVER (
            PARTITION BY periodo, evidencia->>'regla'
            ORDER BY generado_en DESC, id DESC
        ) AS keeper_id
    FROM recomendaciones_ia
    WHERE evidencia->>'regla' IS NOT NULL
)
UPDATE retroalimentacion_ia feedback
SET recomendacion_id = ranked.keeper_id
FROM ranked_recommendations ranked
WHERE feedback.recomendacion_id = ranked.id
  AND ranked.id <> ranked.keeper_id;

WITH ranked_recommendations AS (
    SELECT
        id,
        row_number() OVER (
            PARTITION BY periodo, evidencia->>'regla'
            ORDER BY generado_en DESC, id DESC
        ) AS row_number
    FROM recomendaciones_ia
    WHERE evidencia->>'regla' IS NOT NULL
)
DELETE FROM recomendaciones_ia recommendation
USING ranked_recommendations ranked
WHERE recommendation.id = ranked.id
  AND ranked.row_number > 1;

CREATE UNIQUE INDEX IF NOT EXISTS idx_recomendaciones_ia_periodo_regla
    ON recomendaciones_ia (periodo, (evidencia->>'regla'))
    WHERE evidencia->>'regla' IS NOT NULL;

COMMIT;
