"use client";

import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import type { AuthUser } from "@/controllers/auth-controller";
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
  onUpdateAlert?: (alertId: number, status: Alert["status"], comment: string) => Promise<void>;
  filters?: DashboardFilters;
  costCenters?: CostCenter[];
  onFiltersChange?: (filters: DashboardFilters) => void;
  activeSection?: "Resumen" | "Carga ERP";
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

export function DashboardView({ dashboard, user, dashboardError = "", recommendationsError = "", onLogout, onEditProfile, onOpenDashboard, onOpenIngestion, onUpdateAlert, filters = { periodFrom: "", periodTo: "", costCenterId: "", horizonDays: 90 }, costCenters = [], onFiltersChange, activeSection = "Resumen", children }: DashboardViewProps) {
  const [activeNav, setActiveNav] = useState<string>(activeSection);
  const [showAllAlerts, setShowAllAlerts] = useState(false);
  const [theme, setTheme] = useState<"light" | "dark">(() =>
    typeof window === "undefined" ? "light" : (localStorage.getItem("cfo-theme") as "light" | "dark") || "light",
  );
  const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false);
  const [logoutError, setLogoutError] = useState("");
  const [alertError, setAlertError] = useState("");
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
          {["Resumen", "Flujo de caja", "Presupuesto", "Reportes", "Carga ERP"].map((item) => (
            <button
              className={activeNav === item ? "nav-item active" : "nav-item"}
              key={item}
              onClick={() => {
                setActiveNav(item);
                if (item === "Carga ERP") onOpenIngestion();
                if (item === "Resumen" && activeSection === "Carga ERP") onOpenDashboard();
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
          {activeSection === "Carga ERP" ? children : (
          <>
          <div className="page-heading">
            <div>
              <p className="eyebrow">PERIODO FINANCIERO</p>
              <h1>Resumen financiero</h1>
              <p className="heading-copy">Una lectura clara de la salud financiera de tu empresa.</p>
            </div>
            <button className="export-button">Exportar reporte <span>↓</span></button>
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
                    <i className="legend-line projected" />Proyectado
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
                <span className="note-mark">i</span> Flujo neto en MXN, no saldo de caja; cada mes muestra solo los días incluidos en el horizonte.
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
                      {recommendation.priority}
                    </span>
                    <strong>{recommendation.situation}</strong>
                    <p><b>Impacto:</b> {recommendation.impact || "No cuantificado."}</p>
                    <p><b>Recomendación:</b> {recommendation.recommendationText}</p>
                    <details className="recommendation-evidence">
                      <summary>Evidencia</summary>
                      {recommendation.evidence ? (
                        <pre>{JSON.stringify(recommendation.evidence, null, 2)}</pre>
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
                    <span>{alert.detail}</span>
                  </div>
                  <div className="alert-amount">
                    <strong>{alert.amount}</strong>
                    <span>sobre presupuesto</span>
                  </div>
                  {onUpdateAlert && user.role !== "cfo" && (
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