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
  period: string;
  month: string;
  days: number;
  projected: number;
  lower: number;
  upper: number;
};

export type HistoricalCashFlowPoint = {
  period: string;
  month: string;
  net: number;
};

export type Alert = {
  id: number;
  title: string;
  detail: string;
  amount: string;
  severity: "high" | "medium" | "low";
  area: string;
  status: "nueva" | "en_revision" | "cerrada" | "falsa";
  accountId: number;
  costCenterId: number | null;
  budgetedAmount: number;
  actualAmount: number;
  comment: string | null;
};

export type Recommendation = {
  id: number;
  situation: string;
  impact: string | null;
  recommendationText: string;
  priority: "baja" | "media" | "alta";
  evidence: Record<string, unknown> | null;
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
  forecastDays: number;
  kpis: Kpi[];
  cashFlowHistory: HistoricalCashFlowPoint[];
  forecast: ForecastPoint[];
  alerts: Alert[];
  recommendations: Recommendation[];
};

export const financialDashboard: FinancialDashboard = {
  period: "Sin datos",
  lastSync: "Sin cargas",
  forecastDays: 0,
  kpis: [],
  cashFlowHistory: [],
  forecast: [],
  alerts: [],
  recommendations: [],
};