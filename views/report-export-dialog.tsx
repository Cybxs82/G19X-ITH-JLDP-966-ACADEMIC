"use client";

import { useState } from "react";
import { downloadSummaryReportExcel, saveSummaryReport } from "@/controllers/reports-controller";
import type { DashboardFilters } from "@/models/financial-model";

type ReportExportDialogProps = {
  filters: DashboardFilters;
  onClose: () => void;
};

export function ReportExportDialog({ filters, onClose }: ReportExportDialogProps) {
  const [format, setFormat] = useState<"pdf" | "excel">("pdf");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [isExporting, setIsExporting] = useState(false);

  async function exportReport() {
    setError("");
    setSuccess("");
    setIsExporting(true);
    try {
      const report = await saveSummaryReport(filters);
      if (format === "excel") {
        await downloadSummaryReportExcel(report.id);
        setSuccess("El reporte se guardó y se descargó en formato Excel.");
      } else {
        setSuccess("El reporte PDF se guardó. Puedes descargarlo desde la sección Reportes.");
      }
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "No se pudo exportar el reporte.");
    } finally {
      setIsExporting(false);
    }
  }

  return (
    <div className="report-dialog-backdrop">
      <section className="report-dialog" role="dialog" aria-modal="true" aria-labelledby="report-dialog-title">
        <div className="report-dialog-heading">
          <div>
            <p className="eyebrow">EXPORTAR RESUMEN</p>
            <h2 id="report-dialog-title">Elige el formato</h2>
          </div>
          <button type="button" className="report-dialog-close" aria-label="Cerrar" onClick={onClose}>×</button>
        </div>
        <p className="report-dialog-copy">El reporte guardará una instantánea de los filtros y datos financieros actuales.</p>
        <div className="report-format-options">
          <label className={format === "pdf" ? "report-format-option selected" : "report-format-option"}>
            <input type="radio" name="report-format" value="pdf" checked={format === "pdf"} onChange={() => setFormat("pdf")} />
            <span><strong>PDF</strong><small>Guardar una copia lista para compartir e imprimir.</small></span>
          </label>
          <label className={format === "excel" ? "report-format-option selected" : "report-format-option"}>
            <input type="radio" name="report-format" value="excel" checked={format === "excel"} onChange={() => setFormat("excel")} />
            <span><strong>Excel (.xlsx)</strong><small>Descargar hojas de indicadores, pronóstico, alertas y recomendaciones.</small></span>
          </label>
        </div>
        {error && <p className="auth-error report-dialog-message" role="alert">{error}</p>}
        {success && <p className="cash-flow-success report-dialog-message" role="status">{success}</p>}
        <div className="report-dialog-actions">
          <button type="button" className="secondary-button" onClick={onClose} disabled={isExporting}>
            {success ? "Cerrar" : "Cancelar"}
          </button>
          <button type="button" className="export-button" onClick={() => void exportReport()} disabled={isExporting}>
            {isExporting ? "Exportando..." : format === "excel" ? "Guardar y descargar Excel" : "Guardar PDF"}
          </button>
        </div>
      </section>
    </div>
  );
}
