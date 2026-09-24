"use client";

import { useEffect, useState } from "react";
import { getFinancialDashboard } from "@/controllers/dashboard-controller";
import { financialDashboard, type FinancialDashboard } from "@/models/financial-model";
import { DashboardView } from "@/views/dashboard-view";

export default function Home() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [authMode, setAuthMode] = useState<"login" | "signup">("login");
  const [dashboard, setDashboard] = useState<FinancialDashboard>(financialDashboard);

  useEffect(() => {
    void getFinancialDashboard().then(setDashboard);
  }, []);

  if (!isAuthenticated) {
    return (
      <main className="auth-shell">
        <section className="auth-panel left-panel">
          <div className="auth-brand">
            <span>F</span>
            <div>
              <strong>Foresight</strong>
              <small>FINANCE INTELLIGENCE</small>
            </div>
          </div>

          <div className="auth-copy-block">
            <p className="eyebrow">PLATAFORMA CFO</p>
            <h1>Control financiero inteligente para decisiones de dirección.</h1>
            <p>
              Consolida ERP + banco, monitoriza liquidez, valida presupuesto y proyecta flujo de caja con
              recomendaciones accionables para el equipo ejecutivo.
            </p>
          </div>

          <div className="auth-feature-list">
            <div>
              <strong>Fase 2</strong>
              <span>Integración de datos ERP + banco</span>
            </div>
            <div>
              <strong>Forecast 90 días</strong>
              <span>Rango de confianza y alertas automáticas</span>
            </div>
            <div>
              <strong>Microsoft Entra ID</strong>
              <span>Autenticación corporativa con roles</span>
            </div>
          </div>
        </section>

        <section className="auth-panel auth-form-panel">
          <div className="auth-header">
            <div>
              <p className="eyebrow">ACCESO SEGURIZADO</p>
              <h2>{authMode === "login" ? "Iniciar sesión" : "Crear cuenta"}</h2>
            </div>
            <div className="auth-tabs" aria-label="Modo de acceso">
              <button
                className={authMode === "login" ? "auth-tab active" : "auth-tab"}
                type="button"
                onClick={() => setAuthMode("login")}
              >
                Iniciar sesión
              </button>
              <button
                className={authMode === "signup" ? "auth-tab active" : "auth-tab"}
                type="button"
                onClick={() => setAuthMode("signup")}
              >
                Crear cuenta
              </button>
            </div>
          </div>

          <form
            className="auth-form"
            onSubmit={(event) => {
              event.preventDefault();
              setIsAuthenticated(true);
            }}
          >
            <label>
              <span>Correo corporativo</span>
              <input type="email" defaultValue="cfo@empresa.com" />
            </label>
            <label>
              <span>{authMode === "login" ? "Contraseña" : "Contraseña temporal"}</span>
              <input type="password" defaultValue="••••••••" />
            </label>

            {authMode === "signup" && (
              <label>
                <span>Nombre completo</span>
                <input type="text" defaultValue="Mariana Ríos" />
              </label>
            )}

            <button type="submit" className="primary-button auth-submit">
              {authMode === "login" ? "Entrar al dashboard" : "Crear cuenta de Microsoft Entra ID"}
            </button>
          </form>

          <div className="auth-divider">
            <span>o</span>
          </div>

          <button type="button" className="secondary-button auth-entra">
            Continuar con Microsoft Entra ID
          </button>
        </section>
      </main>
    );
  }

  return <DashboardView dashboard={dashboard} />;
}
