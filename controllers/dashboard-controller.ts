import { financialDashboard, type CostCenter, type DashboardFilters, type FinancialDashboard } from "@/models/financial-model";
import type { Alert } from "@/models/financial-model";

type ApiDashboard = {
  period_from: string;
  period_to: string;
  last_sync: string | null;
  kpis: Array<{
    id: number;
    code: string;
    name: string;
    value: number;
    change_pct: number | null;
  }>;
  forecast: {
    values: Array<{
      target_date: string;
      predicted_value: number;
      lower_bound: number | null;
      upper_bound: number | null;
    }>;
  };
  alerts: Array<{
    id: number;
    deviation_pct: number;
    severity: "baja" | "media" | "alta";
    status: Alert["status"];
    period: string;
  }>;
  recommendations: Array<{
    id: number;
    generated_text: string;
  }>;
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

function mapDashboard(data: ApiDashboard, horizonDays: DashboardFilters["horizonDays"]): FinancialDashboard {
  const monthlyForecast = new Map<string, { projected: number; lower: number; upper: number }>();
  for (const point of data.forecast.values.slice(0, horizonDays)) {
    const month = point.target_date.slice(0, 7);
    const values = monthlyForecast.get(month) ?? { projected: 0, lower: 0, upper: 0 };
    values.projected += Number(point.predicted_value);
    values.lower += Number(point.lower_bound ?? point.predicted_value);
    values.upper += Number(point.upper_bound ?? point.predicted_value);
    monthlyForecast.set(month, values);
  }
  return {
    period: `${new Date(`${data.period_from}T00:00:00`).toLocaleDateString("es-MX")} - ${new Date(`${data.period_to}T00:00:00`).toLocaleDateString("es-MX")}`,
    lastSync: data.last_sync ? new Date(data.last_sync).toLocaleString("es-MX") : "Sin sincronización",
    kpis: data.kpis.map((kpi, index) => ({
      label: kpi.name,
      value: ["flujo_neto_bancario", "ingresos_acumulados"].includes(kpi.code) ? formatMoney(kpi.value) : `${kpi.value.toFixed(1)}%`,
      change: kpi.change_pct === null ? "Sin variación" : `${kpi.change_pct > 0 ? "+" : ""}${kpi.change_pct}%`,
      context: kpi.code === "flujo_neto_bancario" ? "flujo neto bancario del mes" : "periodo mensual",
      trend: kpi.change_pct === null || kpi.change_pct === 0 ? "stable" : kpi.change_pct > 0 ? "up" : "down",
      tone: (["teal", "blue", "amber", "coral"] as const)[index % 4],
    })),
    forecast: [...monthlyForecast].map(([month, values]) => ({
      month: new Date(`${month}-01T00:00:00`).toLocaleDateString("es-MX", { month: "short" }),
      projected: values.projected / 1000000,
      lower: values.lower / 1000000,
      upper: values.upper / 1000000,
    })),
    alerts: data.alerts.filter((alert) => alert.status !== "cerrada" && alert.status !== "falsa").map((alert) => ({
      id: alert.id,
      title: "Desviación presupuestal",
      detail: `Periodo ${alert.period}`,
      amount: `${alert.deviation_pct > 0 ? "+" : ""}${alert.deviation_pct}%`,
      severity: alert.severity === "alta" ? "high" : "medium",
      area: "Consolidado",
      status: alert.status,
    })),
    recommendations: data.recommendations.map((recommendation) => ({
      title: `Recomendación ${recommendation.id}`,
      detail: recommendation.generated_text,
      priority: recommendation.id === 1 ? "Alta" : "Media",
    })),
  };
}

export async function getFinancialDashboard(filters: DashboardFilters): Promise<FinancialDashboard> {
  try {
    const query = new URLSearchParams();
    if (filters.periodFrom) query.set("period_from", filters.periodFrom);
    if (filters.periodTo) query.set("period_to", filters.periodTo);
    if (filters.costCenterId) query.set("cost_center_id", filters.costCenterId);
    const suffix = query.size > 0 ? `?${query.toString()}` : "";
    const response = await fetch(`${apiUrl}/dashboard${suffix}`, { credentials: "include", cache: "no-store" });
    if (!response.ok) {
      throw new Error(`Dashboard API returned ${response.status}`);
    }
    return mapDashboard((await response.json()) as ApiDashboard, filters.horizonDays);
  } catch {
    return financialDashboard;
  }
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