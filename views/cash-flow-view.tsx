"use client";

import { useMemo, useState } from "react";
import type { CostCenter, DashboardFilters, FinancialDashboard } from "@/models/financial-model";
import { ReportExportDialog } from "@/views/report-export-dialog";

type CashFlowViewProps = {
  dashboard: FinancialDashboard;
  filters: DashboardFilters;
  costCenters: CostCenter[];
  isLoading: boolean;
  error: string;
  onFiltersChange: (filters: DashboardFilters) => void;
  onRetry: () => void;
  onOpenDashboard: () => void;
  onOpenIngestion: () => void;
};

function formatCurrency(value: number, compact = false): string {
  return new Intl.NumberFormat("es-MX", {
    style: "currency",
    currency: "MXN",
    notation: compact ? "compact" : "standard",
    maximumFractionDigits: compact ? 1 : 2,
  }).format(value);
}

function formatDate(value: string, monthOnly = false): string {
  return new Date(`${value}T00:00:00`).toLocaleDateString("es-MX", monthOnly
    ? { month: "long", year: "numeric" }
    : { day: "numeric", month: "short", year: "numeric" });
}

function severityLabel(severity: "high" | "medium" | "low"): string {
  if (severity === "high") return "Alta";
  if (severity === "medium") return "Media";
  return "Baja";
}

export function CashFlowView({
  dashboard,
  filters,
  costCenters,
  isLoading,
  error,
  onFiltersChange,
  onRetry,
  onOpenDashboard,
  onOpenIngestion,
}: CashFlowViewProps) {
  const [isExportDialogOpen, setIsExportDialogOpen] = useState(false);

  const actualTotal = useMemo(
    () => dashboard.cashFlowHistory.reduce((total, point) => total + point.net, 0),
    [dashboard.cashFlowHistory],
  );
  const forecastTotal = useMemo(
    () => dashboard.forecast.reduce((total, point) => total + point.projected, 0),
    [dashboard.forecast],
  );
  const negativeForecastMonths = dashboard.forecast.filter((point) => point.projected < 0).length;
  const worstForecast = dashboard.forecast.reduce<FinancialDashboard["forecast"][number] | null>(
    (worst, point) => (!worst || point.projected < worst.projected ? point : worst),
    null,
  );
  const chartRows = [
    ...dashboard.cashFlowHistory.slice(-6).map((point) => ({
      key: `actual-${point.period}`,
      period: point.period,
      month: point.month,
      amount: point.net,
      lower: null as number | null,
      upper: null as number | null,
      kind: "real" as const,
    })),
    ...dashboard.forecast.map((point) => ({
      key: `forecast-${point.period}`,
      period: point.period,
      month: point.month,
      amount: point.projected,
      lower: point.lower,
      upper: point.upper,
      kind: "proyectado" as const,
    })),
  ];
  const chartScale = Math.max(1, ...chartRows.map((point) => Math.abs(point.amount)));
  const openAlerts = dashboard.alerts.filter((alert) => alert.severity === "high");

  return (
    <section className="cash-flow-page">
      {isExportDialogOpen && <ReportExportDialog filters={filters} onClose={() => setIsExportDialogOpen(false)} />}
      <div className="page-heading">
        <div>
          <p className="eyebrow">TESORERÍA · CONTROL DE LIQUIDEZ</p>
          <h1>Flujo de caja</h1>
          <p className="heading-copy">Movimientos bancarios registrados y proyección del flujo neto para anticipar periodos de presión financiera.</p>
        </div>
        <div className="cash-flow-actions">
          <button type="button" className="secondary-button" onClick={onOpenDashboard}>Volver al resumen</button>
          <button type="button" className="export-button" onClick={() => setIsExportDialogOpen(true)}>
            Exportar reporte <span aria-hidden="true">↓</span>
          </button>
        </div>
      </div>

      <div className="cash-flow-filters" aria-label="Filtros de flujo de caja">
        <label className="dashboard-filter">
          <span>Desde</span>
          <input type="date" max={filters.periodTo || undefined} value={filters.periodFrom} onChange={(event) => onFiltersChange({ ...filters, periodFrom: event.target.value })} />
        </label>
        <label className="dashboard-filter">
          <span>Hasta</span>
          <input type="date" min={filters.periodFrom || undefined} value={filters.periodTo} onChange={(event) => onFiltersChange({ ...filters, periodTo: event.target.value })} />
        </label>
        <label className="dashboard-filter">
          <span>Centro de costo</span>
          <select value={filters.costCenterId} onChange={(event) => onFiltersChange({ ...filters, costCenterId: event.target.value })}>
            <option value="">Consolidado</option>
            {costCenters.map((center) => <option key={center.id} value={center.id}>{center.name}</option>)}
          </select>
        </label>
        <label className="dashboard-filter">
          <span>Horizonte de proyección</span>
          <select value={filters.horizonDays} onChange={(event) => onFiltersChange({ ...filters, horizonDays: Number(event.target.value) as DashboardFilters["horizonDays"] })}>
            <option value={30}>30 días</option>
            <option value={60}>60 días</option>
            <option value={90}>90 días</option>
          </select>
        </label>
      </div>
      <p className="cash-flow-filter-note">
        {filters.periodFrom || filters.periodTo
          ? "El periodo seleccionado limita el histórico; la proyección parte de los últimos datos bancarios disponibles y cubre el horizonte elegido."
          : "Por omisión se consulta el último año hasta hoy. El horizonte define los días futuros de la proyección."}
      </p>

      {error && (
        <div className="cash-flow-error" role="alert">
          <p>{error}</p>
          <button type="button" className="secondary-button" onClick={onRetry}>Reintentar</button>
        </div>
      )}
      <section className="cash-flow-caveat" aria-label="Alcance del cálculo de caja">
        <span className="cash-flow-caveat-mark" aria-hidden="true">!</span>
        <div>
          <strong>Flujo neto no es saldo disponible</strong>
          <p>Esta versión muestra el neto de movimientos bancarios y su proyección. No calcula saldo inicial/final, runway ni caja disponible porque aún no recibe saldos de apertura, cuentas por cobrar/pagar ni vencimientos. Valida la liquidez con tu banco antes de tomar decisiones.</p>
        </div>
      </section>

      <section className="cash-flow-metrics" aria-label="Indicadores de flujo de caja">
        <article className="cash-flow-metric">
          <span>Flujo neto registrado</span>
          <strong className={actualTotal < 0 ? "negative-text" : ""}>{formatCurrency(actualTotal, true)}</strong>
          <small>{dashboard.cashFlowHistory.length} periodos mensuales con datos</small>
        </article>
        <article className="cash-flow-metric">
          <span>Flujo neto proyectado</span>
          <strong className={forecastTotal < 0 ? "negative-text" : ""}>{formatCurrency(forecastTotal, true)}</strong>
          <small>Próximos {filters.horizonDays} días · modelo lineal</small>
        </article>
        <article className="cash-flow-metric">
          <span>Meses con neto negativo</span>
          <strong className={negativeForecastMonths > 0 ? "negative-text" : ""}>{negativeForecastMonths}</strong>
          <small>Dentro del horizonte proyectado</small>
        </article>
        <article className="cash-flow-metric">
          <span>Riesgos presupuestales altos</span>
          <strong className={openAlerts.length > 0 ? "negative-text" : ""}>{openAlerts.length}</strong>
          <small>Alertas abiertas en el periodo</small>
        </article>
      </section>

      {isLoading && <p className="cash-flow-loading" aria-live="polite">Actualizando datos de flujo de caja…</p>}

      <section className="panel cash-flow-panel" aria-labelledby="cash-flow-chart-title">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">HISTÓRICO Y PRONÓSTICO</p>
            <h2 id="cash-flow-chart-title">Flujo neto mensual</h2>
            <p className="heading-copy">Importes en MXN · los valores positivos y negativos son movimientos netos, no saldos.</p>
          </div>
          <div className="cash-flow-legend">
            <span><i className="cash-flow-legend-dot actual" />Registrado</span>
            <span><i className="cash-flow-legend-dot projected" />Proyectado</span>
          </div>
        </div>

        {!isLoading && dashboard.cashFlowHistory.length === 0 && dashboard.forecast.length === 0 ? (
          <div className="cash-flow-empty">
            <strong>No hay movimientos bancarios disponibles para este filtro.</strong>
            <p>Carga un archivo de movimientos bancarios para ver el histórico. El pronóstico requiere al menos 180 días de movimientos.</p>
            <button type="button" className="secondary-button" onClick={onOpenIngestion}>Ir a Carga ERP</button>
          </div>
        ) : (
          <div className="cash-flow-timeline">
            {chartRows.map((point) => (
              <article className="cash-flow-period" key={point.key}>
                <div className="cash-flow-period-head">
                  <span>{point.month}</span>
                  <small>{point.kind === "real" ? "Registrado" : "Proyección"}</small>
                </div>
                <div className="cash-flow-track" aria-label={`${point.month}: ${formatCurrency(point.amount)}`}>
                  <i className={`cash-flow-bar ${point.kind} ${point.amount < 0 ? "negative" : ""}`} style={{ width: `${Math.max(2, Math.abs(point.amount) / chartScale * 100)}%` }} />
                </div>
                <strong className={point.amount < 0 ? "negative-text" : ""}>{formatCurrency(point.amount, true)}</strong>
                {point.lower !== null && point.upper !== null ? (
                  <small className="cash-flow-range">Rango 80 %: {formatCurrency(point.lower, true)} a {formatCurrency(point.upper, true)}</small>
                ) : <small className="cash-flow-range">Neto observado</small>}
              </article>
            ))}
          </div>
        )}
      </section>

      <div className="cash-flow-detail-grid">
        <section className="panel cash-flow-panel" aria-labelledby="cash-flow-forecast-title">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">PLANEACIÓN</p>
              <h2 id="cash-flow-forecast-title">Detalle de proyección</h2>
            </div>
            <span className="count-badge">{dashboard.forecast.length}</span>
          </div>
          {dashboard.forecast.length === 0 ? (
            <div className="cash-flow-empty compact">
              <strong>Pronóstico no disponible</strong>
              <p>Se necesitan al menos 180 días calendario de transacciones bancarias para calcularlo.</p>
            </div>
          ) : (
            <>
              {worstForecast && worstForecast.projected < 0 && (
                <div className="cash-flow-risk">
                  <strong>Mes de mayor presión estimada: {formatDate(worstForecast.period, true)}</strong>
                  <span>Flujo neto de {formatCurrency(worstForecast.projected)}. Confirma los movimientos y prepara medidas con Tesorería.</span>
                </div>
              )}
              <div className="cash-flow-table-wrap">
                <table className="cash-flow-table">
                  <thead>
                    <tr><th>Periodo</th><th>Días</th><th>Flujo estimado</th><th>Rango predictivo 80 %</th></tr>
                  </thead>
                  <tbody>
                    {dashboard.forecast.map((point) => (
                      <tr key={point.period}>
                        <th scope="row">{formatDate(point.period, true)}</th>
                        <td>{point.days}</td>
                        <td className={point.projected < 0 ? "negative-text" : "positive-text"}>{formatCurrency(point.projected)}</td>
                        <td>{formatCurrency(point.lower)} – {formatCurrency(point.upper)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="cash-flow-footnote">El intervalo refleja incertidumbre estadística del modelo; no es una garantía ni incluye movimientos futuros no presentes en el histórico.</p>
            </>
          )}
        </section>

        <section className="panel cash-flow-panel" aria-labelledby="cash-flow-watchlist-title">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">SEGUIMIENTO</p>
              <h2 id="cash-flow-watchlist-title">Alertas presupuestales</h2>
            </div>
            <span className="count-badge">{dashboard.alerts.length}</span>
          </div>
          {dashboard.alerts.length === 0 ? (
            <p className="cash-flow-empty compact">No hay alertas presupuestales abiertas para este periodo.</p>
          ) : (
            <ul className="cash-flow-alert-list">
              {dashboard.alerts.slice(0, 5).map((alert) => (
                <li key={alert.id}>
                  <span className={`cash-flow-alert-severity ${alert.severity}`}>{severityLabel(alert.severity)}</span>
                  <div>
                    <strong>{alert.title} · cuenta #{alert.accountId}</strong>
                    <small>{alert.detail} · Presupuesto {formatCurrency(alert.budgetedAmount)} · Real {formatCurrency(alert.actualAmount)}</small>
                  </div>
                  <b className={alert.actualAmount > alert.budgetedAmount ? "negative-text" : ""}>{alert.amount}</b>
                </li>
              ))}
            </ul>
          )}
          <button type="button" className="text-button cash-flow-link" onClick={onOpenDashboard}>Revisar alertas en el resumen <span>→</span></button>
        </section>
      </div>

      <section className="panel cash-flow-method">
        <div>
          <p className="eyebrow">CÓMO INTERPRETAR ESTA VISTA</p>
          <h2>Supuestos y datos necesarios para Tesorería</h2>
        </div>
        <div className="cash-flow-method-grid">
          <article><strong>Base actual</strong><p>Movimientos bancarios importados y agregados por periodo. El neto combina entradas y salidas; aquí no se separan cobros y pagos.</p></article>
          <article><strong>Modelo</strong><p>Regresión lineal diaria con al menos 180 días de histórico. La proyección presenta un intervalo predictivo del 80 % y puede variar con nuevos datos.</p></article>
          <article><strong>Para completar la posición de caja</strong><p>Se requieren saldos de apertura y cierre conciliados, cuentas por cobrar y pagar con fechas de vencimiento, transferencias internas y calendario de deuda e inversiones.</p></article>
        </div>
      </section>
    </section>
  );
}
