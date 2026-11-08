ALTER TABLE reportes_resumen
    ADD COLUMN IF NOT EXISTS pdf_content BYTEA;

COMMENT ON COLUMN reportes_resumen.pdf_content IS
    'PDF generado y almacenado para descargar la instantánea del reporte.';
