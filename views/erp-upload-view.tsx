"use client";

import { FormEvent, useState } from "react";
import { uploadERPDocument, type ERPDocumentIngestion } from "@/controllers/auth-controller";

const MAX_FILE_SIZE = 20 * 1024 * 1024;
const ACCEPTED_TYPES = ".pdf,.csv,.xlsx,.xlsm";

export function ERPUploadView() {
  const [file, setFile] = useState<File | null>(null);
  const [sourceType, setSourceType] = useState<"erp" | "banco" | "presupuesto">("erp");
  const [errorMessage, setErrorMessage] = useState("");
  const [result, setResult] = useState<ERPDocumentIngestion | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage("");
    setResult(null);
    if (!file) {
      setErrorMessage("Selecciona un archivo para continuar.");
      return;
    }
    if (file.size > MAX_FILE_SIZE) {
      setErrorMessage("El archivo supera el límite de 20 MB.");
      return;
    }

    setIsUploading(true);
    try {
      setResult(await uploadERPDocument(file, sourceType));
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "No se pudo guardar el archivo.");
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <section className="erp-upload-content">
      <div className="page-heading">
        <div>
        <p className="eyebrow">IMPORTACIÓN DE DATOS</p>
        <h1>Carga ERP</h1>
        <p className="heading-copy">Consolida archivos ERP o bancarios y conserva los valores originales para auditoría.</p>
        </div>
      </div>

      <form className="erp-upload-form" onSubmit={handleSubmit}>
          <label className="erp-file-field">
            <span>Fuente de datos</span>
            <select
              value={sourceType}
              onChange={(event) => {
                setSourceType(event.target.value as "erp" | "banco" | "presupuesto");
                setFile(null);
                setResult(null);
                setErrorMessage("");
              }}
            >
              <option value="erp">ERP</option>
              <option value="banco">Banco</option>
              <option value="presupuesto">Presupuesto</option>
            </select>
          </label>
          <label className="erp-file-field">
            <span>Archivo financiero</span>
            <input
              type="file"
              accept={sourceType === "presupuesto" ? ".csv,.xlsx,.xlsm" : ACCEPTED_TYPES}
              required
              onChange={(event) => {
                setFile(event.target.files?.[0] ?? null);
                setErrorMessage("");
                setResult(null);
              }}
            />
            <small>{sourceType === "presupuesto" ? "CSV o Excel con periodo, monto_presupuestado, cuenta y centro_costo." : "PDF, CSV o Excel (.xlsx, .xlsm)."} Máximo 20 MB.</small>
          </label>
          {errorMessage && <p className="auth-error" role="alert">{errorMessage}</p>}
          {result && (
            <p className="upload-success" role="status">
              Carga completada: {result.rows_ingested} {sourceType === "presupuesto" ? "presupuestos" : "movimientos"} guardados y {result.rows_rejected} rechazados. Los valores originales quedaron en staging.
            </p>
          )}
          <div className="erp-upload-actions">
            <button type="submit" className="primary-button" disabled={isUploading || !file}>
              {isUploading ? "Guardando..." : "Subir y guardar"}
            </button>
          </div>
      </form>
    </section>
  );
}