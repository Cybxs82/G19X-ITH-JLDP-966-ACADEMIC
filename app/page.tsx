"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getFinancialDashboard } from "@/controllers/dashboard-controller";
import { getCurrentUser, login, logout, register, type AuthUser } from "@/controllers/auth-controller";
import { financialDashboard, type FinancialDashboard } from "@/models/financial-model";
import { DashboardView } from "@/views/dashboard-view";

type AuthState = "checking" | "authenticated" | "anonymous";

export default function Home() {
  const router = useRouter();
  const [authState, setAuthState] = useState<AuthState>("checking");
  const [authMode, setAuthMode] = useState<"login" | "signup">("login");
  const [user, setUser] = useState<AuthUser | null>(null);
  const [dashboard, setDashboard] = useState<FinancialDashboard>(financialDashboard);
  const [errorMessage, setErrorMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    void getCurrentUser()
      .then((currentUser) => {
        setUser(currentUser);
        setAuthState(currentUser ? "authenticated" : "anonymous");
      })
      .catch(() => {
        setAuthState("anonymous");
        setErrorMessage("No se pudo comprobar la sesión. Intenta nuevamente.");
      });
  }, []);

  useEffect(() => {
    if (authState !== "authenticated") return;
    void getFinancialDashboard().then(setDashboard);
  }, [authState]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage("");
    setIsSubmitting(true);
    const formData = new FormData(event.currentTarget);
    const email = String(formData.get("email") ?? "");
    const password = String(formData.get("password") ?? "");
    const fullName = String(formData.get("fullName") ?? "");

    try {
      const currentUser = authMode === "login" ? await login(email, password) : await register(email, fullName, password);
      setUser(currentUser);
      setAuthState("authenticated");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "No se pudo completar la operación");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleLogout() {
    await logout();
    setUser(null);
    setAuthState("anonymous");
    setAuthMode("login");
  }

  if (authState === "checking") {
    return <main className="auth-loading">Comprobando sesión...</main>;
  }

  if (authState === "authenticated" && user) {
    return <DashboardView dashboard={dashboard} user={user} onLogout={handleLogout} onEditProfile={() => router.push("/profile")} onOpenDashboard={() => router.push("/")} onOpenIngestion={() => router.push("/ingestion")} />;
  }

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
            <strong>Datos conectados</strong>
            <span>Información financiera normalizada en PostgreSQL</span>
          </div>
          <div>
            <strong>Forecast 90 días</strong>
            <span>Rango de confianza y alertas automáticas</span>
          </div>
          <div>
            <strong>Acceso por roles</strong>
            <span>Usuarios, credenciales y sesiones administradas en PostgreSQL</span>
          </div>
        </div>
      </section>

      <section className="auth-panel auth-form-panel">
        <div className="auth-header">
          <div>
            <p className="eyebrow">ACCESO SEGURO</p>
            <h2>{authMode === "login" ? "Iniciar sesión" : "Crear cuenta"}</h2>
          </div>
          <div className="auth-tabs" aria-label="Modo de acceso">
            <button className={authMode === "login" ? "auth-tab active" : "auth-tab"} type="button" onClick={() => setAuthMode("login")}>
              Iniciar sesión
            </button>
            <button className={authMode === "signup" ? "auth-tab active" : "auth-tab"} type="button" onClick={() => setAuthMode("signup")}>
              Crear cuenta
            </button>
          </div>
        </div>

        {errorMessage && <p className="auth-error" role="alert">{errorMessage}</p>}

        <form className="auth-form" onSubmit={handleSubmit}>
          {authMode === "signup" && (
            <label>
              <span>Nombre completo</span>
              <input name="fullName" type="text" autoComplete="name" required />
            </label>
          )}
          <label>
            <span>Correo corporativo</span>
            <input name="email" type="email" autoComplete="email" required />
          </label>
          <label>
            <span>Contraseña</span>
            <input name="password" type="password" autoComplete={authMode === "login" ? "current-password" : "new-password"} minLength={8} required />
          </label>

          <button type="submit" className="primary-button auth-submit" disabled={isSubmitting}>
            {isSubmitting ? "Procesando..." : authMode === "login" ? "Entrar al dashboard" : "Crear cuenta"}
          </button>
        </form>

        <p className="auth-database-note">Las credenciales se validan y almacenan de forma segura en PostgreSQL.</p>
      </section>
    </main>
  );
}