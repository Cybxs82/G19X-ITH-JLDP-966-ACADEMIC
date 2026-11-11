"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getCurrentUser, logout, type AuthUser } from "@/controllers/auth-controller";
import { downloadSummaryReportExcel, getSavedSummaryReports } from "@/controllers/reports-controller";
import { financialDashboard } from "@/models/financial-model";
import type { SavedSummaryReport } from "@/models/report-model";
import { DashboardView } from "@/views/dashboard-view";

function formatDate(value: string): string {
  return new Date(`${value}T00:00:00`).toLocaleDateString("es-MX", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

function formatAmount(value: number | string, code: string): string {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return String(value);
  if (code === "flujo_neto_bancario" || code === "ingresos_acumulados") {
    return new Intl.NumberFormat("es-MX", {
      style: "currency",
      currency: "MXN",
      maximumFractionDigits: 2,
    }).format(amount);
  }
  return `${amount.toFixed(2)}${code === "margen_operativo" || code === "desviacion_presupuestal" ? "%" : ""}`;
}

function SavedReportDetails({ report }: { report: SavedSummaryReport }) {
  const { snapshot } = report;
  return (
    <div className="saved-report-details">
      <div className="saved-report-kpis">
        {snapshot.kpis.length === 0 ? (
          <p className="data-empty">No había indicadores disponibles para este periodo.</p>
        ) : snapshot.kpis.map((kpi) => (
          <article className="saved-report-kpi" key={`${kpi.code}-${kpi.period}`}>
            <span>{kpi.name}</span>
            <strong>{formatAmount(kpi.value, kpi.code)}</strong>
            <small>{formatDate(kpi.period)}</small>
          </article>
        ))}
      </div>

      <section className="saved-report-section">
        <h3>Proyección de flujo neto</h3>
        {snapshot.forecast.monthly_values.length === 0 ? (
          <p className="data-empty">No hay histórico bancario suficiente para la proyección.</p>
        ) : (
          <ul>
            {snapshot.forecast.monthly_values.map((point) => (
              <li key={point.period}>
                <strong>{formatDate(point.period)}:</strong>{" "}
                {formatAmount(point.predicted_value, "flujo_neto_bancario")} proyectados
                {" · "}intervalo {formatAmount(point.lower_bound, "flujo_neto_bancario")} a{" "}
                {formatAmount(point.upper_bound, "flujo_neto_bancario")}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="saved-report-section">
        <h3>Alertas ({snapshot.alerts.length})</h3>
        {snapshot.alerts.length === 0 ? (
          <p className="data-empty">No hay alertas para este periodo.</p>
        ) : (
          <ul>
            {snapshot.alerts.map((alert) => (
              <li key={alert.id}>
                {formatDate(alert.period)} · {alert.severity} · desviación {Number(alert.deviation_pct).toFixed(2)}%
                {" · "}{alert.status}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="saved-report-section">
        <h3>Recomendaciones ({snapshot.recommendations.length})</h3>
        {snapshot.recommendations.length === 0 ? (
          <p className="data-empty">No hay recomendaciones disponibles para este resumen.</p>
        ) : (
          <ul>
            {snapshot.recommendations.map((recommendation) => (
              <li key={recommendation.id}>
                <strong>{recommendation.situation}</strong>
                <p>{recommendation.recommendation_text}</p>
              </li>
            ))}
          </ul>
        )}
      </section>
      <p className="saved-report-sync">
        Última sincronización registrada: {snapshot.last_sync ? new Date(snapshot.last_sync).toLocaleString("es-MX") : "Sin sincronización"}
      </p>
    </div>
  );
}

export default function ReportsPage() {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [reports, setReports] = useState<SavedSummaryReport[]>([]);
  const [summaryDate, setSummaryDate] = useState("");
  const [selectedReportId, setSelectedReportId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");
  const [downloadError, setDownloadError] = useState("");
  const [downloadingExcelReportId, setDownloadingExcelReportId] = useState<number | null>(null);

  async function downloadExcel(reportId: number) {
    setDownloadError("");
    setDownloadingExcelReportId(reportId);
    try {
      await downloadSummaryReportExcel(reportId);
    } catch (error) {
      setDownloadError(error instanceof Error ? error.message : "No se pudo descargar el archivo Excel.");
    } finally {
      setDownloadingExcelReportId(null);
    }
  }

  useEffect(() => {
    let active = true;
    void getCurrentUser()
      .then(async (currentUser) => {
        if (!active) return;
        if (!currentUser) {
          router.replace("/");
          return;
        }
        setUser(currentUser);
        const savedReports = await getSavedSummaryReports();
        if (active) setReports(savedReports);
      })
      .catch((error: unknown) => {
        if (active) {
          setErrorMessage(error instanceof Error ? error.message : "No se pudieron cargar los reportes.");
        }
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => { active = false; };
  }, [router]);

  const filteredReports = reports.filter((report) => !summaryDate || report.summary_date === summaryDate);
  const selectedReport = reports.find((report) => report.id === selectedReportId);

  if (isLoading || !user) return <main className="auth-loading">Cargando reportes...</main>;

  return (
    <DashboardView
      dashboard={financialDashboard}
      user={user}
      activeSection="Reportes"
      onLogout={async () => { await logout(); router.replace("/"); }}
      onEditProfile={() => router.push("/profile")}
      onOpenDashboard={() => router.push("/")}
      onOpenCashFlow={() => router.push("/cash-flow")}
      onOpenIngestion={() => router.push("/ingestion")}
      onOpenReports={() => router.push("/reports")}
      onOpenGuide={() => router.push("/guide")}
    >
      <section className="reports-page">
        <div className="page-heading">
          <div>
            <p className="eyebrow">RESÚMENES GUARDADOS</p>
            <h1>Reportes</h1>
            <p className="heading-copy">Aquí aparecen los reportes guardados al exportarlos desde el resumen. La fecha corresponde al último día del periodo resumido.</p>
          </div>
        </div>

        <div className="reports-filter-row">
          <label className="dashboard-filter">
            <span>Fecha del resumen</span>
            <input type="date" value={summaryDate} onChange={(event) => setSummaryDate(event.target.value)} />
          </label>
          {summaryDate && (
            <button type="button" className="text-button reports-clear-filter" onClick={() => setSummaryDate("")}>
              Limpiar filtro
            </button>
          )}
        </div>

        {errorMessage && <p className="auth-error" role="alert">{errorMessage}</p>}
        {downloadError && <p className="auth-error" role="alert">{downloadError}</p>}
        {!errorMessage && filteredReports.length === 0 && (
          <p className="data-empty reports-empty">
            {reports.length === 0 ? "Aún no hay reportes guardados." : "No hay reportes para esa fecha."}
          </p>
        )}

        <div className="reports-list">
          {filteredReports.map((report) => (
            <article className={`panel saved-report${selectedReportId === report.id ? " selected" : ""}`} key={report.id}>
              <div className="saved-report-heading">
                <div>
                  <p className="eyebrow">{report.report_type === "mensual" ? "REPORTE MENSUAL" : "REPORTE GUARDADO"}</p>
                  <h2>Resumen al {formatDate(report.summary_date)}</h2>
                  <p className="heading-copy">
                    Periodo {formatDate(report.period_from)} – {formatDate(report.period_to)}
                    {" · "}Guardado {new Date(report.created_at).toLocaleString("es-MX")}
                  </p>
                </div>
                <div className="saved-report-actions">
                  <button
                    type="button"
                    className="secondary-button"
                    onClick={() => setSelectedReportId(selectedReportId === report.id ? null : report.id)}
                  >
                    {selectedReportId === report.id ? "Ocultar resumen" : "Ver resumen"}
                  </button>
                  {report.pdf_available && (
                    <a className="export-button" href={`/api/reports/${report.id}/pdf`}>
                      Descargar PDF
                    </a>
                  )}
                  <button
                    type="button"
                    className="secondary-button"
                    onClick={() => void downloadExcel(report.id)}
                    disabled={downloadingExcelReportId === report.id}
                  >
                    {downloadingExcelReportId === report.id ? "Preparando Excel..." : "Descargar Excel"}
                  </button>
                </div>
              </div>
              {selectedReport && selectedReport.id === report.id && <SavedReportDetails report={report} />}
            </article>
          ))}
        </div>
      </section>
    </DashboardView>
  );
}
