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
};

export type Recommendation = {
  title: string;
  detail: string;
  priority: "Alta" | "Media";
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
  period: "Oct 2025 - Sep 2026",
  lastSync: "Hoy, 06:42",
  kpis: [
    { label: "Liquidez inmediata", value: "2.48x", change: "+8.4%", context: "vs. mes anterior", trend: "up", tone: "teal" },
    { label: "Margen operativo", value: "18.6%", change: "+2.1 pp", context: "vs. presupuesto", trend: "up", tone: "blue" },
    { label: "Ingresos acumulados", value: "$24.8M", change: "+12.7%", context: "vs. año anterior", trend: "up", tone: "amber" },
    { label: "Desviación presupuestal", value: "-3.2%", change: "Dentro del umbral", context: "umbral configurado: 5%", trend: "stable", tone: "coral" },
  ],
  forecast: [
    { month: "Oct", actual: 4.2, projected: 4.2, lower: 3.9, upper: 4.5 },
    { month: "Nov", actual: 4.7, projected: 4.7, lower: 4.4, upper: 5.0 },
    { month: "Dic", actual: 5.1, projected: 5.1, lower: 4.7, upper: 5.5 },
    { month: "Ene", actual: 4.5, projected: 4.5, lower: 4.1, upper: 4.9 },
    { month: "Feb", actual: 5.4, projected: 5.4, lower: 4.9, upper: 5.9 },
    { month: "Mar", actual: 5.8, projected: 5.8, lower: 5.2, upper: 6.4 },
    { month: "Abr", projected: 6.1, lower: 5.3, upper: 6.9 },
    { month: "May", projected: 6.5, lower: 5.5, upper: 7.5 },
    { month: "Jun", projected: 6.8, lower: 5.7, upper: 7.9 },
    { month: "Jul", projected: 7.2, lower: 5.9, upper: 8.5 },
    { month: "Ago", projected: 7.7, lower: 6.2, upper: 9.2 },
    { month: "Sep", projected: 8.1, lower: 6.4, upper: 9.8 },
  ],
  alerts: [
    { id: 1, title: "Servicios profesionales", detail: "Área Tecnología · 18 mar 2026", amount: "+14.2%", severity: "high", area: "Tecnología" },
    { id: 2, title: "Logística y distribución", detail: "Área Operaciones · 16 mar 2026", amount: "+7.8%", severity: "medium", area: "Operaciones" },
    { id: 3, title: "Campaña de adquisición", detail: "Área Comercial · 12 mar 2026", amount: "+5.6%", severity: "medium", area: "Comercial" },
  ],
  recommendations: [
    { title: "Revisar renovación de proveedores de tecnología", detail: "El gasto está 14.2% por encima del presupuesto y concentra el 61% de la desviación mensual.", priority: "Alta" },
    { title: "Acelerar cobranza de cuentas por cobrar", detail: "Una reducción de 8 días en el ciclo liberaría aproximadamente $1.2M de caja durante el próximo trimestre.", priority: "Media" },
  ],
};