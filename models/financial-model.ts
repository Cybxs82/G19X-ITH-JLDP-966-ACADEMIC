export type Trend = "up" | "down" | "stable";

export type Kpi = {
  label: string;
  value: string;
  change: string;
  context: string;
  trend: Trend;
  tone: "teal" | "amber" | "blue" | "coral";
};

export type ForecastPoint = {
  month: string;
  actual?: number;
  projected: number;
  lower: number;
  upper: number;
};

export type Alert = {
  id: number;
  title: string;
  detail: string;
  amount: string;
  severity: "high" | "medium";
  area: string;
  status: "nueva" | "en_revision" | "cerrada" | "falsa";
};

export type Recommendation = {
  title: string;
  detail: string;
  priority: "Alta" | "Media";
};

export type CostCenter = { id: number; name: string };

export type DashboardFilters = {
  periodFrom: string;
  periodTo: string;
  costCenterId: string;
  horizonDays: 30 | 60 | 90;
};

export type FinancialDashboard = {
  period: string;
  lastSync: string;
  kpis: Kpi[];
  forecast: ForecastPoint[];
  alerts: Alert[];
  recommendations: Recommendation[];
};

export const financialDashboard: FinancialDashboard = {
  period: "Sin datos",
  lastSync: "Sin cargas",
  kpis: [],
  forecast: [],
  alerts: [],
  recommendations: [],
};