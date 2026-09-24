"use client";

import { useEffect, useState } from "react";
import type { FinancialDashboard } from "@/models/financial-model";

type DashboardViewProps = { dashboard: FinancialDashboard };

export function DashboardView({ dashboard }: DashboardViewProps) {
  const [activeArea, setActiveArea] = useState("Todas");
  const [activeNav, setActiveNav] = useState("Resumen");
  const [showAllAlerts, setShowAllAlerts] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [theme, setTheme] = useState<"light" | "dark">("light");

  useEffect(() => {
    const savedTheme = (localStorage.getItem("cfo-theme") as "light" | "dark") || "light";
    setTheme(savedTheme);
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("cfo-theme", theme);
  }, [theme]);

  const areas = ["Todas", ...new Set(dashboard.alerts.map((alert) => alert.area))];
  const visibleAlerts = dashboard.alerts.filter((alert) => activeArea === "Todas" || alert.area === activeArea);

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
          {["Resumen", "Flujo de caja", "Presupuesto", "Reportes"].map((item) => (
            <button className={activeNav === item ? "nav-item active" : "nav-item"} key={item} onClick={() => setActiveNav(item)}>
              <span className="nav-dot" />{item}
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <button className="nav-item" type="button" onClick={() => setShowSettings((current) => !current)}>
            <span className="nav-dot" />Configuración
          </button>

          {showSettings && (
            <div className="settings-panel">
              <div className="settings-header">
                <strong>Configuración</strong>
                <button type="button" className="ghost-button" onClick={() => setShowSettings(false)}>
                  Cerrar
                </button>
              </div>

              <div className="settings-section">
                <span>Tema</span>
                <button
                  type="button"
                  className="theme-toggle"
                  onClick={() => setTheme((current) => (current === "dark" ? "light" : "dark"))}
                >
                  {theme === "dark" ? "Modo claro" : "Modo oscuro"}
                </button>
              </div>

              <div className="settings-section">
                <span>Fase 2 · Integración</span>
                <small>ERP + Banco · sincronización diaria activa</small>
              </div>
            </div>
          )}

          <div className="profile">
            <div className="avatar">MR</div>
            <div>
              <strong>Mariana Ríos</strong>
              <small>CFO · Administradora</small>
            </div>
            <span className="more">...</span>
          </div>
        </div>
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
            <div className="mini-avatar">MR</div>
          </div>
        </header>

        <div className="page-content">
          <div className="page-heading">
            <div>
              <p className="eyebrow">LUNES, 21 DE SEPTIEMBRE DE 2026</p>
              <h1>Resumen financiero</h1>
              <p className="heading-copy">Una lectura clara de la salud financiera de tu empresa.</p>
            </div>
            <button className="export-button">Exportar reporte <span>↓</span></button>
          </div>

          <div className="filter-row">
            <div className="period-selector">
              <span className="calendar-icon">□</span>
              <span>{dashboard.period}</span>
              <span className="chevron">⌄</span>
            </div>
            <div className="area-filters">
              {areas.map((area) => (
                <button key={area} className={activeArea === area ? "filter active" : "filter"} onClick={() => setActiveArea(area)}>
                  {area}
                </button>
              ))}
            </div>
          </div>

          <section className="integration-banner" aria-label="Integración de datos">
            <div>
              <p className="eyebrow">FASE 2 · INTEGRACIÓN DE DATOS</p>
              <h2>ERP + Banco sincronizados</h2>
            </div>

            <div className="integration-metrics">
              <div>
                <strong>96%</strong>
                <span>cargas completadas</span>
              </div>
              <div>
                <strong>2.4h</strong>
                <span>tiempo de actualización</span>
              </div>
              <div>
                <strong>1,23%</strong>
                <span>errores de validación</span>
              </div>
            </div>
          </section>

          <section className="kpi-grid" aria-label="Indicadores clave">
            {dashboard.kpis.map((kpi) => (
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
                  <h2>Flujo de caja</h2>
                </div>
                <div className="legend">
                  <span>
                    <i className="legend-line actual" />Real
                  </span>
                  <span>
                    <i className="legend-line projected" />Proyectado
                  </span>
                </div>
              </div>

              <div className="forecast-summary">
                <strong>$8.1M</strong>
                <span>
                  saldo esperado a 90 días <b>↗ 22.4%</b>
                </span>
              </div>

              <div className="chart">
                <div className="chart-y">
                  <span>$10M</span>
                  <span>$7.5M</span>
                  <span>$5M</span>
                  <span>$2.5M</span>
                  <span>$0</span>
                </div>

                <div className="chart-body">
                  <div className="chart-grid-lines">
                    <i />
                    <i />
                    <i />
                    <i />
                    <i />
                  </div>
                  <div className="bars">
                    {dashboard.forecast.map((point) => (
                      <div className={`bar-group ${point.actual ? "past" : "future"}`} key={point.month}>
                        <div className="confidence" style={{ height: `${point.upper * 9}%`, bottom: `${point.lower * 3.5}%` }} />
                        <div className="bar" style={{ height: `${point.projected * 8.5}%` }} />
                        <span>{point.month}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <div className="chart-note">
                <span className="note-mark">i</span> El intervalo de confianza se amplía a medida que avanza la proyección.
              </div>
            </section>

            <section className="panel ai-panel">
              <div className="ai-heading">
                <div className="ai-spark">✦</div>
                <div>
                  <p className="eyebrow">ANÁLISIS INTELIGENTE</p>
                  <h2>Lectura ejecutiva</h2>
                </div>
                <span className="ai-badge">IA</span>
              </div>

              <p className="ai-lead">
                El negocio mantiene una posición saludable, con generación de caja al alza y margen operativo por encima del plan.
              </p>

              <div className="ai-divider" />

              <div className="recommendation-list">
                {dashboard.recommendations.map((recommendation) => (
                  <div className="recommendation" key={recommendation.title}>
                    <div className={`priority ${recommendation.priority.toLowerCase()}`}>{recommendation.priority}</div>
                    <strong>{recommendation.title}</strong>
                    <p>{recommendation.detail}</p>
                  </div>
                ))}
              </div>

              <button className="text-button">Ver análisis completo <span>→</span></button>
            </section>
          </div>

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
              {visibleAlerts.slice(0, showAllAlerts ? visibleAlerts.length : 3).map((alert) => (
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
                  <button className="row-action" aria-label={`Abrir alerta de ${alert.title}`}>
                    →
                  </button>
                </div>
              ))}
            </div>
          </section>

          <footer className="footer-note">
            <span className="status-dot" /> Consolidado ERP + Banco · Última sincronización {dashboard.lastSync}
          </footer>
        </div>
      </section>
    </main>
  );
}