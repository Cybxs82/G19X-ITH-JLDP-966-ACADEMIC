"use client";

import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import type { AuthUser } from "@/controllers/auth-controller";
import { saveSummaryReport } from "@/controllers/reports-controller";
import type { Alert, CostCenter, DashboardFilters, FinancialDashboard } from "@/models/financial-model";

type DashboardViewProps = {
  dashboard: FinancialDashboard;
  user: AuthUser;
  dashboardError?: string;
  recommendationsError?: string;
  onLogout: () => Promise<void>;
  onEditProfile: () => void;
  onOpenDashboard: () => void;
  onOpenIngestion: () => void;
  onOpenReports: () => void;
  onOpenGuide: () => void;
  onUpdateAlert?: (alertId: number, status: Alert["status"], comment: string) => Promise<void>;
  filters?: DashboardFilters;
  costCenters?: CostCenter[];
  onFiltersChange?: (filters: DashboardFilters) => void;
  activeSection?: "Resumen" | "Reportes" | "Carga ERP" | "Guía de uso";
  children?: ReactNode;
};

function getForecastScale(forecast: FinancialDashboard["forecast"]): { min: number; max: number; step: number } {
  const values = forecast.flatMap((point) => [point.lower, point.upper, point.projected]);
  const rawMin = Math.min(0, ...values);
  const rawMax = Math.max(0, ...values);
  const rawStep = Math.max((rawMax - rawMin) / 4, 1);
  const magnitude = 10 ** Math.floor(Math.log10(rawStep));
  const fraction = rawStep / magnitude;
  const step = (fraction <= 1 ? 1 : fraction <= 2 ? 2 : fraction <= 5 ? 5 : 10) * magnitude;
  let min = Math.floor(rawMin / step) * step;
  let max = Math.ceil(rawMax / step) * step;
  if (max <= min) {
    min -= step;
    max += step;
  }
  return { min, max, step };
}

function getForecastTicks(forecast: FinancialDashboard["forecast"]): number[] {
  const { min, max, step } = getForecastScale(forecast);
  const count = Math.round((max - min) / step);
  return Array.from({ length: count + 1 }, (_, index) => max - step * index)
    .map((tick) => Math.abs(tick) < step / 1000 ? 0 : tick);
}

function getForecastPercent(value: number, forecast: FinancialDashboard["forecast"]): number {
  const { min, max } = getForecastScale(forecast);
  return ((value - min) / (max - min)) * 100;
}

function formatForecastAmount(value: number): string {
  return new Intl.NumberFormat("es-MX", {
    style: "currency",
    currency: "MXN",
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

function formatExactAmount(value: number): string {
  return new Intl.NumberFormat("es-MX", {
    style: "currency",
    currency: "MXN",
    maximumFractionDigits: 2,
  }).format(value);
}

const evidenceLabels: Record<string, string> = {
  regla: "Regla aplicada",
  alertas_ids: "Alertas relacionadas",
  kpis_ids: "Indicadores relacionados",
  centro_costo_id: "Centro de costo",
  valor: "Valor observado",
  forecast: "Proyección relacionada",
  dia_horizonte: "Horizonte",
  fecha_objetivo: "Fecha estimada",
  valor_predicho: "Flujo neto estimado",
  fuentes_faltantes: "Datos faltantes",
  kpi_codigos_faltantes: "Indicadores faltantes",
  motivo_forecast_no_disponible: "Disponibilidad del forecast",
};

const ruleLabels: Record<string, string> = {
  alerta_abierta_severidad_alta: "Alerta abierta de severidad alta",
  alertas_recurrentes_por_centro: "Alertas recurrentes por centro",
  flujo_neto_bancario_negativo: "Flujo neto bancario negativo",
  margen_operativo_negativo: "Margen operativo negativo",
  kpi_desviacion_presupuestal_positiva: "Desviación presupuestal positiva",
  forecast_caja_negativa: "Flujo neto proyectado negativo",
  datos_insuficientes: "Datos insuficientes",
};

function formatEvidenceValue(value: unknown, key: string, rule?: string): string {
  if (value === null || value === undefined || value === "") return "No disponible";
  if (typeof value === "boolean") return value ? "Sí" : "No";
  if (typeof value === "number") {
    if (key.endsWith("_ids")) return `#${value}`;
    if (key === "dia_horizonte") return `${value} días`;
    if (key === "valor_predicho" || (key === "valor" && rule === "flujo_neto_bancario_negativo")) {
      return formatExactAmount(value);
    }
    if (key === "valor" && ["margen_operativo_negativo", "kpi_desviacion_presupuestal_positiva"].includes(rule ?? "")) {
      return `${value.toLocaleString("es-MX", { maximumFractionDigits: 2 })}%`;
    }
    return value.toLocaleString("es-MX");
  }
  if (typeof value === "string") {
    if (key === "regla") return ruleLabels[value] ?? value.replaceAll("_", " ");
    if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
      return new Date(`${value}T00:00:00`).toLocaleDateString("es-MX", {
        day: "numeric",
        month: "long",
        year: "numeric",
      });
    }
    return value.replaceAll("_", " ");
  }
  return "Detalle adicional disponible";
}

function renderEvidenceValue(value: unknown, key: string, rule?: string): ReactNode {
  if (Array.isArray(value)) {
    if (value.length === 0) return <>Ninguno</>;
    return (
      <ul className="evidence-values">
        {value.map((item, index) => (
          <li key={`${key}-${index}`}>{renderEvidenceValue(item, key, rule)}</li>
        ))}
      </ul>
    );
  }
  if (typeof value === "object" && value !== null) {
    return (
      <dl className="evidence-list evidence-nested">
        {Object.entries(value).map(([nestedKey, nestedValue]) => (
          <div className="evidence-item" key={nestedKey}>
            <dt>{evidenceLabels[nestedKey] ?? nestedKey.replaceAll("_", " ")}</dt>
            <dd>{renderEvidenceValue(nestedValue, nestedKey, rule)}</dd>
          </div>
        ))}
      </dl>
    );
  }
  return <>{formatEvidenceValue(value, key, rule)}</>;
}

function RecommendationEvidence({ evidence }: { evidence: Record<string, unknown> }) {
  const rule = typeof evidence.regla === "string" ? evidence.regla : undefined;
  const forecast = Array.isArray(evidence.forecast) ? evidence.forecast : [];
  const fields = Object.entries(evidence).filter(([key]) => key !== "forecast");

  return (
    <div className="recommendation-evidence-content">
      {fields.length > 0 && (
        <dl className="evidence-list">
          {fields.map(([key, value]) => (
            <div className="evidence-item" key={key}>
              <dt>{evidenceLabels[key] ?? key.replaceAll("_", " ")}</dt>
              <dd>{renderEvidenceValue(value, key, rule)}</dd>
            </div>
          ))}
        </dl>
      )}
      {forecast.length > 0 && (
        <div className="evidence-table-wrap">
          <table className="evidence-table">
            <thead>
              <tr><th>Horizonte</th><th>Fecha estimada</th><th>Flujo neto</th></tr>
            </thead>
            <tbody>
              {forecast.map((point, index) => {
                if (typeof point !== "object" || point === null) return null;
                const row = point as Record<string, unknown>;
                return (
                  <tr key={`${String(row.dia_horizonte)}-${index}`}>
                    <td>{formatEvidenceValue(row.dia_horizonte, "dia_horizonte", rule)}</td>
                    <td>{formatEvidenceValue(row.fecha_objetivo, "fecha_objetivo", rule)}</td>
                    <td>{formatEvidenceValue(row.valor_predicho, "valor_predicho", rule)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export function DashboardView({ dashboard, user, dashboardError = "", recommendationsError = "", onLogout, onEditProfile, onOpenDashboard, onOpenIngestion, onOpenReports, onOpenGuide, onUpdateAlert, filters = { periodFrom: "", periodTo: "", costCenterId: "", horizonDays: 90 }, costCenters = [], onFiltersChange, activeSection = "Resumen", children }: DashboardViewProps) {
  const [activeNav, setActiveNav] = useState<string>(activeSection);
  const [underDevelopmentSection, setUnderDevelopmentSection] = useState<"Flujo de caja" | "Presupuesto" | null>(null);
  const [showAllAlerts, setShowAllAlerts] = useState(false);
  const [theme, setTheme] = useState<"light" | "dark">(() =>
    typeof window === "undefined" ? "light" : (localStorage.getItem("cfo-theme") as "light" | "dark") || "light",
  );
  const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false);
  const [logoutError, setLogoutError] = useState("");
  const [alertError, setAlertError] = useState("");
  const [reportError, setReportError] = useState("");
  const [isSavingReport, setIsSavingReport] = useState(false);
  const [alertComments, setAlertComments] = useState<Record<number, string>>({});
  const [updatingAlertId, setUpdatingAlertId] = useState<number | null>(null);

  async function handleLogout() {
    setLogoutError("");
    try {
      await onLogout();
    } catch (error) {
      setLogoutError(error instanceof Error ? error.message : "No se pudo cerrar la sesión.");
    }
  }

  async function updateAlert(alertId: number, status: Alert["status"]) {
    if (!onUpdateAlert) return;
    setAlertError("");
    setUpdatingAlertId(alertId);
    try {
      await onUpdateAlert(alertId, status, alertComments[alertId] ?? "");
      setAlertComments((current) => ({ ...current, [alertId]: "" }));
    } catch (error) {
      setAlertError(error instanceof Error ? error.message : "No se pudo actualizar la alerta.");
    } finally {
      setUpdatingAlertId(null);
    }
  }

  async function exportSummary() {
    setReportError("");
    setIsSavingReport(true);
    try {
      await saveSummaryReport(filters);
    } catch (error) {
      setReportError(error instanceof Error ? error.message : "No se pudo guardar el reporte.");
    } finally {
      setIsSavingReport(false);
    }
  }

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("cfo-theme", theme);
  }, [theme]);

  const visibleAlerts = dashboard.alerts;

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand-mark">
          <span>F</span>
          <div>
            <strong>Foresight</strong>
            <small>FINANCE INTELLIGENCE</small>
          </div>
        </div>

        <div className="workspace-label">PLATAFORMA CFO</div>

        <nav className="main-nav" aria-label="Navegación principal">
          {["Resumen", "Flujo de caja", "Presupuesto", "Reportes", "Carga ERP", "Guía de uso"].map((item) => (
            <button
              className={activeNav === item ? "nav-item active" : "nav-item"}
              key={item}
              onClick={() => {
                setActiveNav(item);
                setUnderDevelopmentSection(
                  item === "Flujo de caja" || item === "Presupuesto" ? item : null,
                );
                if (item === "Carga ERP") onOpenIngestion();
                if (item === "Reportes") onOpenReports();
                if (item === "Guía de uso") onOpenGuide();
                if (item === "Resumen" && activeSection !== "Resumen") onOpenDashboard();
              }}
            >
              <span className="nav-dot" />{item}
            </button>
          ))}
        </nav>

      </aside>

      <section className="content-area">
        <header className="topbar">
          <div className="mobile-brand">Foresight</div>
          <div className="topbar-actions">
            <span className="sync-status">
              <span className="status-dot" />Datos actualizados {dashboard.lastSync}
            </span>
            <button className="icon-button" aria-label="Notificaciones">
              3
            </button>
            <button
              type="button"
              className="icon-button theme-badge"
              aria-label="Cambiar tema"
              onClick={() => setTheme((current) => (current === "dark" ? "light" : "dark"))}
            >
              {theme === "dark" ? "☀" : "☾"}
            </button>
            <button type="button" className="mini-avatar profile-trigger" aria-label="Abrir menú de perfil" aria-expanded={isProfileMenuOpen} aria-haspopup="menu" onClick={() => setIsProfileMenuOpen((current) => !current)}>
              {user.full_name.slice(0, 2).toUpperCase()}
            </button>
            {isProfileMenuOpen && (
              <div className="profile-menu profile-menu-header" role="menu">
                <button type="button" role="menuitem" onClick={() => { setIsProfileMenuOpen(false); onEditProfile(); }}>Editar perfil</button>
                <button type="button" role="menuitem" onClick={() => void handleLogout()}>Cerrar sesión</button>
              </div>
            )}
          </div>
        </header>

        <div className="page-content">
          {logoutError && <p className="auth-error" role="alert">{logoutError}</p>}
          {dashboardError && <p className="auth-error" role="alert">{dashboardError}</p>}
          {alertError && <p className="auth-error" role="alert">{alertError}</p>}
          {reportError && <p className="auth-error" role="alert">{reportError}</p>}
          {underDevelopmentSection ? (
            <section className="panel under-development" aria-labelledby="under-development-title" aria-live="polite">
              <p className="eyebrow">EN DESARROLLO</p>
              <h1 id="under-development-title">{underDevelopmentSection}</h1>
              <p className="heading-copy">
                Esta sección se encuentra en desarrollo y estará disponible en una próxima actualización.
              </p>
            </section>
          ) : activeSection !== "Resumen" ? children : (
          <>
          <div className="page-heading">
            <div>
              <p className="eyebrow">PERIODO FINANCIERO</p>
              <h1>Resumen financiero</h1>
              <p className="heading-copy">Una lectura clara de la salud financiera de tu empresa.</p>
            </div>
            <button type="button" className="export-button" onClick={() => void exportSummary()} disabled={isSavingReport}>
              {isSavingReport ? "Guardando..." : "Exportar reporte"} <span aria-hidden="true">↓</span>
            </button>
          </div>

          <div className="filter-row">
            <label className="dashboard-filter"><span>Desde</span><input type="date" max={filters.periodTo || undefined} value={filters.periodFrom} onChange={(event) => onFiltersChange?.({ ...filters, periodFrom: event.target.value })} /></label>
            <label className="dashboard-filter"><span>Hasta</span><input type="date" min={filters.periodFrom || undefined} value={filters.periodTo} onChange={(event) => onFiltersChange?.({ ...filters, periodTo: event.target.value })} /></label>
            <label className="dashboard-filter"><span>Área</span><select value={filters.costCenterId} onChange={(event) => onFiltersChange?.({ ...filters, costCenterId: event.target.value })}><option value="">Todas</option>{costCenters.map((center) => <option key={center.id} value={center.id}>{center.name}</option>)}</select></label>
            <label className="dashboard-filter"><span>Forecast</span><select value={filters.horizonDays} onChange={(event) => onFiltersChange?.({ ...filters, horizonDays: Number(event.target.value) as DashboardFilters["horizonDays"] })}><option value={30}>30 días</option><option value={60}>60 días</option><option value={90}>90 días</option></select></label>
          </div>

          <section className="integration-banner" aria-label="Integración de datos">
            <div>
              <p className="eyebrow">ÚLTIMA ACTUALIZACIÓN</p>
              <h2>{dashboard.lastSync}</h2>
            </div>
            <p className="heading-copy">ERP y banco · carga manual para MVP</p>
          </section>

          <section className="kpi-grid" aria-label="Indicadores clave">
            {dashboard.kpis.length === 0 ? <p className="data-empty">Carga movimientos para calcular los indicadores.</p> : dashboard.kpis.map((kpi) => (
              <article className={`kpi-card ${kpi.tone}`} key={kpi.label}>
                <div className="kpi-top">
                  <span>{kpi.label}</span>
                  <span className="kpi-trend">{kpi.trend === "up" ? "↗" : kpi.trend === "down" ? "↘" : "—"}</span>
                </div>
                <strong>{kpi.value}</strong>
                <p>
                  <b>{kpi.change}</b> {kpi.context}
                </p>
              </article>
            ))}
          </section>

          <div className="main-grid">
            <section className="panel forecast-panel">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">PROYECCIÓN</p>
                  <h2>Flujo neto mensual</h2>
                </div>
                <div className="legend">
                  <span>
                    <i className="legend-bar projected" />Proyectado
                  </span>
                  <span><i className="legend-band" />Intervalo 80 %</span>
                </div>
              </div>

              {dashboard.forecast.length === 0 ? (
                <p className="data-empty">Aún no hay histórico suficiente para calcular el forecast.</p>
              ) : (
              <>
              <div className="forecast-summary">
                <strong>{dashboard.forecastDays} días</strong>
                <span>de proyección calculada</span>
              </div>
              <div className="chart">
                <div className="chart-y">
                  {getForecastTicks(dashboard.forecast).map((tick) => (
                    <span key={tick}>{formatForecastAmount(tick)}</span>
                  ))}
                </div>

                <div className="chart-body">
                  <div className="chart-grid-lines">
                    {getForecastTicks(dashboard.forecast).map((tick) => (
                      <i
                        className={tick === 0 ? "zero" : ""}
                        key={tick}
                        style={{ bottom: `${getForecastPercent(tick, dashboard.forecast)}%` }}
                      />
                    ))}
                  </div>
                  <div className="bars">
                    {dashboard.forecast.map((point) => (
                      <div className="bar-group future" key={point.month}>
                        <div
                          className="confidence"
                          title={`Intervalo estimado ${point.month}: ${formatForecastAmount(point.lower)} a ${formatForecastAmount(point.upper)}`}
                          style={{
                            height: `${getForecastPercent(point.upper, dashboard.forecast) - getForecastPercent(point.lower, dashboard.forecast)}%`,
                            bottom: `${getForecastPercent(point.lower, dashboard.forecast)}%`,
                          }}
                        />
                        <div
                          className={`bar ${point.projected < 0 ? "negative" : ""}`}
                          title={`${point.month}: ${formatForecastAmount(point.projected)}`}
                          style={{
                            height: `${Math.abs(getForecastPercent(point.projected, dashboard.forecast) - getForecastPercent(0, dashboard.forecast))}%`,
                            bottom: `${Math.min(getForecastPercent(point.projected, dashboard.forecast), getForecastPercent(0, dashboard.forecast))}%`,
                          }}
                        />
                        <span title={`${point.month}: ${point.days} días proyectados`}>{point.month} · {point.days}d</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <div className="chart-note">
                <span className="note-mark">i</span> Barra sólida: flujo neto mensual proyectado. Franja clara: rango estimado (80 %) entre los límites inferior y superior. Valores en MXN, no saldo de caja; los días indican cuánto del mes incluye la proyección.
              </div>
              </>
              )}
            </section>

          </div>

          <section className="panel ai-panel" aria-label="Recomendaciones financieras">
            <div className="panel-heading">
              <div className="ai-heading">
                <span className="ai-spark" aria-hidden="true">✦</span>
                <div>
                  <p className="eyebrow">REGLAS FINANCIERAS</p>
                  <h2>Recomendaciones</h2>
                </div>
              </div>
              <span className="count-badge">{dashboard.recommendations.length}</span>
            </div>

            {dashboard.recommendations.length === 0 ? (
              <p className={recommendationsError ? "auth-error" : "data-empty"} role={recommendationsError ? "alert" : undefined}>
                {recommendationsError || "No hay recomendaciones para mostrar."}
              </p>
            ) : (
              <div className="recommendations-list">
                {dashboard.recommendations.map((recommendation) => (
                  <article className="recommendation" key={recommendation.id}>
                    <span className={`priority ${recommendation.priority}`}>
                      Prioridad {recommendation.priority}
                    </span>
                    <strong>{recommendation.situation}</strong>
                    <p><b>Impacto:</b> {recommendation.impact || "No cuantificado."}</p>
                    <p><b>Recomendación:</b> {recommendation.recommendationText}</p>
                    <details className="recommendation-evidence">
                      <summary>Evidencia</summary>
                      {recommendation.evidence ? (
                        <RecommendationEvidence evidence={recommendation.evidence} />
                      ) : (
                        <p>Sin evidencia disponible.</p>
                      )}
                    </details>
                  </article>
                ))}
              </div>
            )}
          </section>

          <section className="panel alerts-panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">CONTROL PRESUPUESTAL</p>
                <h2>
                  Alertas recientes <span className="count-badge">{visibleAlerts.length}</span>
                </h2>
              </div>
              <button className="text-button" onClick={() => setShowAllAlerts(!showAllAlerts)}>
                {showAllAlerts ? "Mostrar menos" : "Ver todas"} <span>→</span>
              </button>
            </div>

            <div className="alerts-list">
              {visibleAlerts.length === 0 ? <p className="data-empty">No hay alertas para los filtros seleccionados.</p> : visibleAlerts.slice(0, showAllAlerts ? visibleAlerts.length : 3).map((alert) => (
                <div className="alert-row" key={alert.id}>
                  <div className={`alert-icon ${alert.severity}`} />
                  <div className="alert-copy">
                    <strong>{alert.title}</strong>
                    <span>{alert.detail} · Cuenta #{alert.accountId}</span>
                    <div className="alert-tags">
                      <span className={`alert-severity ${alert.severity}`}>Severidad {alert.severity === "high" ? "alta" : alert.severity === "medium" ? "media" : "baja"}</span>
                      <span className="alert-status">{alert.status === "en_revision" ? "En revisión" : alert.status === "nueva" ? "Nueva" : alert.status}</span>
                    </div>
                  </div>
                  <div className="alert-amount">
                    <strong>{alert.amount}</strong>
                    <span>desviación presupuestal</span>
                  </div>
                  <dl className="alert-details">
                    <div><dt>Presupuesto</dt><dd>{formatExactAmount(alert.budgetedAmount)}</dd></div>
                    <div><dt>Gasto real</dt><dd>{formatExactAmount(alert.actualAmount)}</dd></div>
                    <div><dt>Centro de costo</dt><dd>{alert.costCenterId ? `#${alert.costCenterId}` : "General"}</dd></div>
                  </dl>
                  {alert.comment && <p className="alert-comment"><b>Comentario:</b> {alert.comment}</p>}
                  {onUpdateAlert && (
                    <details className="alert-management">
                      <summary>Gestionar</summary>
                      <label>
                        <span>Comentario</span>
                        <textarea
                          value={alertComments[alert.id] ?? ""}
                          maxLength={2000}
                          onChange={(event) => setAlertComments((current) => ({ ...current, [alert.id]: event.target.value }))}
                        />
                      </label>
                      <div className="alert-management-actions">
                        <button type="button" disabled={updatingAlertId === alert.id} onClick={() => void updateAlert(alert.id, "en_revision")}>Revisar</button>
                        <button type="button" disabled={updatingAlertId === alert.id} onClick={() => void updateAlert(alert.id, "cerrada")}>Cerrar</button>
                        <button type="button" disabled={updatingAlertId === alert.id} onClick={() => void updateAlert(alert.id, "falsa")}>Marcar falsa</button>
                      </div>
                    </details>
                  )}
                </div>
              ))}
            </div>
          </section>

          <footer className="footer-note">
            <span className="status-dot" /> Consolidado ERP + Banco · Última sincronización {dashboard.lastSync}
          </footer>
          </>
          )}
        </div>
      </section>
    </main>
  );
}