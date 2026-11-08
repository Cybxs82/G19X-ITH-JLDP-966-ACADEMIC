export type SavedSummaryReport = {
  id: number;
  summary_date: string;
  period_from: string;
  period_to: string;
  report_type: "mensual" | "manual";
  created_at: string;
  pdf_available: boolean;
  snapshot: {
    period_from: string;
    period_to: string;
    last_sync: string | null;
    kpis: Array<{
      code: string;
      name: string;
      value: number | string;
      period: string;
    }>;
    forecast: {
      horizon_days: number;
      monthly_values: Array<{
        period: string;
        days: number;
        predicted_value: number | string;
        lower_bound: number | string;
        upper_bound: number | string;
      }>;
    };
    alerts: Array<{
      id: number;
      period: string;
      deviation_pct: number | string;
      severity: "baja" | "media" | "alta";
      status: string;
    }>;
    recommendations: Array<{
      id: number;
      period: string;
      situation: string;
      impact: string | null;
      recommendation_text: string;
      priority: string;
    }>;
  };
};
