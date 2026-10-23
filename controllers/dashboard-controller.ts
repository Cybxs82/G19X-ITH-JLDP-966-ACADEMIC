import type { CostCenter, DashboardFilters, FinancialDashboard } from "@/models/financial-model";
import type { Alert } from "@/models/financial-model";

type ApiDashboard = {
  period_from: string;
  period_to: string;
  last_sync: string | null;
  kpis: Array<{
    id: number;
    code: string;
    name: string;
    value: number | string;
    period: string;
    change_pct: number | string | null;
  }>;
  forecast: {
    horizon_days: number;
    values: Array<{
      target_date: string;
      predicted_value: number;
      lower_bound: number | null;
      upper_bound: number | null;
    }>;
    monthly_values: Array<{
      period: string;
      days: number;
      predicted_value: number;
      lower_bound: number;
      upper_bound: number;
    }>;
  };
  alerts: Array<{
    id: number;
    deviation_pct: number | string;
    severity: "baja" | "media" | "alta";
    status: Alert["status"];
    period: string;
  }>;
};

type ApiRecommendation = {
  id: number;
  situation: string;
  impact: string | null;
  recommendation_text: string;
  priority: "baja" | "media" | "alta";
  evidence: Record<string, unknown> | null;
};

const apiUrl = process.env.CFO_API_URL ?? "http://localhost:8000/api/v1";

export async function getCostCenters(): Promise<CostCenter[]> {
  const response = await fetch(`${apiUrl}/cost-centers`, { credentials: "include", cache: "no-store" });
  if (!response.ok) throw new Error(`Cost center API returned ${response.status}`);
  return (await response.json()) as CostCenter[];
}

function formatMoney(value: number): string {
  return new Intl.NumberFormat("es-MX", {
    style: "currency",
    currency: "MXN",
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

function mapRecommendations(recommendations: ApiRecommendation[]): FinancialDashboard["recommendations"] {
  return recommendations.map((recommendation) => ({
    id: recommendation.id,
    situation: recommendation.situation,
    impact: recommendation.impact,
    recommendationText: recommendation.recommendation_text,
    priority: recommendation.priority,
    evidence: recommendation.evidence,
  }));
}

function mapDashboard(data: ApiDashboard, horizonDays: DashboardFilters["horizonDays"]): FinancialDashboard {
  const latestKpis = new Map<string, ApiDashboard["kpis"][number]>();
  for (const kpi of data.kpis) {
    const current = latestKpis.get(kpi.code);
    if (!current || kpi.period > current.period) latestKpis.set(kpi.code, kpi);
  }
  return {
    period: `${new Date(`${data.period_from}T00:00:00`).toLocaleDateString("es-MX")} - ${new Date(`${data.period_to}T00:00:00`).toLocaleDateString("es-MX")}`,
    lastSync: data.last_sync ? new Date(data.last_sync).toLocaleString("es-MX") : "Sin sincronización",
    forecastDays: Math.min(data.forecast.horizon_days, horizonDays),
    kpis: [...latestKpis.values()].map((kpi, index) => {
      const value = Number(kpi.value);
      const changePct = kpi.change_pct === null ? null : Number(kpi.change_pct);
      return {
        label: kpi.name,
        value: ["flujo_neto_bancario", "ingresos_acumulados"].includes(kpi.code) ? formatMoney(value) : `${value.toFixed(1)}%`,
        change: changePct === null
          ? "Sin comparación"
          : `${changePct > 0 ? "+" : ""}${changePct.toFixed(2)}${["margen_operativo", "desviacion_presupuestal"].includes(kpi.code) ? " pp" : "%"}`,
        context: `${kpi.code === "desviacion_presupuestal" ? "gastos vs presupuesto" : kpi.name.toLowerCase()} · ${new Date(`${kpi.period}T00:00:00`).toLocaleDateString("es-MX", { month: "short", year: "numeric" })}`,
        trend: changePct === null || changePct === 0 ? "stable" : changePct > 0 ? "up" : "down",
        tone: (["teal", "blue", "amber", "coral"] as const)[index % 4],
      };
    }),
    forecast: data.forecast.monthly_values.map((point) => ({
      month: new Date(`${point.period}T00:00:00`).toLocaleDateString("es-MX", { month: "short", year: "2-digit" }),
      days: point.days,
      projected: point.predicted_value,
      lower: point.lower_bound,
      upper: point.upper_bound,
    })),
    alerts: data.alerts.filter((alert) => alert.status !== "cerrada" && alert.status !== "falsa").map((alert) => {
      const deviation = Number(alert.deviation_pct);
      return {
        id: alert.id,
        title: "Desviación presupuestal",
        detail: `Periodo ${alert.period}`,
        amount: `${deviation > 0 ? "+" : ""}${deviation.toFixed(2)}%`,
        severity: alert.severity === "alta" ? "high" : "medium",
        area: "Consolidado",
        status: alert.status,
      };
    }),
    recommendations: [],
  };
}

export async function getRecommendations(): Promise<FinancialDashboard["recommendations"]> {
  const response = await fetch("/api/recommendations", {
    credentials: "same-origin",
    cache: "no-store",
  });
  if (!response.ok) {
    if (response.headers.get("content-type")?.includes("application/json")) {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") throw new Error(body.detail);
    }
    throw new Error(`Recommendations API returned ${response.status}`);
  }
  return mapRecommendations((await response.json()) as ApiRecommendation[]);
}

export async function getFinancialDashboard(filters: DashboardFilters): Promise<FinancialDashboard> {
  const query = new URLSearchParams();
  if (filters.periodFrom) query.set("period_from", filters.periodFrom);
  if (filters.periodTo) query.set("period_to", filters.periodTo);
  if (filters.costCenterId) query.set("cost_center_id", filters.costCenterId);
  query.set("horizon_days", String(filters.horizonDays));
  const suffix = query.size > 0 ? `?${query.toString()}` : "";
  const response = await fetch(`/api/dashboard${suffix}`, { credentials: "same-origin", cache: "no-store" });
  if (!response.ok) throw new Error(`Dashboard API returned ${response.status}`);
  return mapDashboard((await response.json()) as ApiDashboard, filters.horizonDays);
}

export async function updateAlertStatus(alertId: number, status: Alert["status"], comment: string): Promise<void> {
  const response = await fetch(`${apiUrl}/alerts/${alertId}`, {
    method: "PATCH",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status, comment: comment || undefined }),
  });
  if (!response.ok) throw new Error(`No se pudo actualizar la alerta (${response.status})`);
}