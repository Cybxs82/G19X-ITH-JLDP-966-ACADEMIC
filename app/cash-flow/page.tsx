"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getCostCenters, getFinancialDashboard } from "@/controllers/dashboard-controller";
import { getCurrentUser, logout, type AuthUser } from "@/controllers/auth-controller";
import { financialDashboard, type CostCenter, type DashboardFilters, type FinancialDashboard } from "@/models/financial-model";
import { CashFlowView } from "@/views/cash-flow-view";
import { DashboardView } from "@/views/dashboard-view";

const initialFilters: DashboardFilters = {
  periodFrom: "",
  periodTo: "",
  costCenterId: "",
  horizonDays: 90,
};

export default function CashFlowPage() {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [dashboard, setDashboard] = useState<FinancialDashboard>(financialDashboard);
  const [filters, setFilters] = useState<DashboardFilters>(initialFilters);
  const [costCenters, setCostCenters] = useState<CostCenter[]>([]);
  const [costCentersError, setCostCentersError] = useState("");
  const [isCheckingSession, setIsCheckingSession] = useState(true);
  const [error, setError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  const [loadedRequestKey, setLoadedRequestKey] = useState("");
  const requestKey = `${filters.periodFrom}|${filters.periodTo}|${filters.costCenterId}|${filters.horizonDays}|${reloadKey}`;
  const isLoading = Boolean(user) && loadedRequestKey !== requestKey;

  useEffect(() => {
    let active = true;
    void getCurrentUser()
      .then((currentUser) => {
        if (!active) return;
        if (!currentUser) {
          router.replace("/");
          return;
        }
        setUser(currentUser);
        void getCostCenters()
          .then((centers) => { if (active) setCostCenters(centers); })
          .catch(() => { if (active) setCostCentersError("No se pudieron cargar los centros de costo; el filtro por área no está disponible."); });
      })
      .catch(() => {
        if (active) {
          setError("No se pudo comprobar la sesión. Inicia sesión e inténtalo de nuevo.");
          router.replace("/");
        }
      })
      .finally(() => { if (active) setIsCheckingSession(false); });
    return () => { active = false; };
  }, [router]);

  useEffect(() => {
    if (!user) return;
    let active = true;
    void getFinancialDashboard(filters)
      .then((result) => {
        if (!active) return;
        setDashboard(result);
        setError("");
        setLoadedRequestKey(requestKey);
      })
      .catch((failure) => {
        if (!active) return;
        setError(failure instanceof Error ? failure.message : "No se pudo cargar el flujo de caja.");
        setLoadedRequestKey(requestKey);
      });
    return () => { active = false; };
  }, [filters, reloadKey, requestKey, user]);

  const retry = useCallback(() => setReloadKey((key) => key + 1), []);

  if (isCheckingSession || !user) return <main className="auth-loading">Comprobando sesión...</main>;

  return (
    <DashboardView
      dashboard={dashboard}
      user={user}
      activeSection="Flujo de caja"
      filters={filters}
      costCenters={costCenters}
      onFiltersChange={setFilters}
      onLogout={async () => { await logout(); router.replace("/"); }}
      onEditProfile={() => router.push("/profile")}
      onOpenDashboard={() => router.push("/")}
      onOpenCashFlow={() => router.push("/cash-flow")}
      onOpenIngestion={() => router.push("/ingestion")}
      onOpenReports={() => router.push("/reports")}
      onOpenGuide={() => router.push("/guide")}
    >
      <CashFlowView
        dashboard={dashboard}
        filters={filters}
        costCenters={costCenters}
        isLoading={isLoading}
        error={error || costCentersError}
        onFiltersChange={setFilters}
        onRetry={retry}
        onOpenDashboard={() => router.push("/")}
        onOpenIngestion={() => router.push("/ingestion")}
      />
    </DashboardView>
  );
}
