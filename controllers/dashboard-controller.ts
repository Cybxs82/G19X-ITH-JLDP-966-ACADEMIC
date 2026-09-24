import { financialDashboard, type FinancialDashboard } from "@/models/financial-model";

type ApiDashboard = {
  last_sync: string | null;
  kpis: Array<{
    id: number;
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
    status: "nueva" | "en_revision" | "cerrada" | "falsa";
    period: string;
  }>;
  recommendations: Array<{
    id: number;
    generated_text: string;
  }>;
};

const apiUrl = process.env.CFO_API_URL ?? "http://localhost:8000/api/v1";

function formatMoney(value: number): string {
  return new Intl.NumberFormat("es-MX", {
    style: "currency",
    currency: "MXN",
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

function mapDashboard(data: ApiDashboard): FinancialDashboard {
  return {
    period: "Últimos 12 meses",
    lastSync: data.last_sync ? new Date(data.last_sync).toLocaleString("es-MX") : "Sin sincronización",
    kpis: data.kpis.map((kpi, index) => ({
      label: kpi.name,
      value: index === 0 ? `${kpi.value.toFixed(2)}x` : index === 2 ? formatMoney(kpi.value) : `${kpi.value.toFixed(1)}%`,
      change: kpi.change_pct === null ? "Sin variación" : `${kpi.change_pct > 0 ? "+" : ""}${kpi.change_pct}%`,
      context: "vs. periodo anterior",
      trend: kpi.change_pct === null || kpi.change_pct === 0 ? "stable" : kpi.change_pct > 0 ? "up" : "down",
      tone: (["teal", "blue", "amber", "coral"] as const)[index % 4],
    })),
    forecast: data.forecast.values.map((point) => ({
      month: new Date(`${point.target_date}T00:00:00`).toLocaleDateString("es-MX", { month: "short" }),
      projected: Number(point.predicted_value) / 1000000,
      lower: Number(point.lower_bound ?? point.predicted_value) / 1000000,
      upper: Number(point.upper_bound ?? point.predicted_value) / 1000000,
    })),
    alerts: data.alerts.filter((alert) => alert.status !== "cerrada" && alert.status !== "falsa").map((alert) => ({
      id: alert.id,
      title: "Desviación presupuestal",
      detail: `Periodo ${alert.period}`,
      amount: `+${alert.deviation_pct}%`,
      severity: alert.severity === "alta" ? "high" : "medium",
      area: "Consolidado",
    })),
    recommendations: data.recommendations.map((recommendation) => ({
      title: `Recomendación ${recommendation.id}`,
      detail: recommendation.generated_text,
      priority: recommendation.id === 1 ? "Alta" : "Media",
    })),
  };
}

export async function getFinancialDashboard(): Promise<FinancialDashboard> {
  try {
    const response = await fetch(`${apiUrl}/dashboard`, { credentials: "include", cache: "no-store" });
    if (!response.ok) {
      throw new Error(`Dashboard API returned ${response.status}`);
    }
    return mapDashboard((await response.json()) as ApiDashboard);
  } catch {
    return financialDashboard;
  }
}