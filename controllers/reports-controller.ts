import type { SavedSummaryReport } from "@/models/report-model";
import type { DashboardFilters } from "@/models/financial-model";

async function readError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string };
    if (typeof body.detail === "string") return body.detail;
  } catch {
    return `La operación de reportes falló (${response.status}).`;
  }
  return `La operación de reportes falló (${response.status}).`;
}

export async function getSavedSummaryReports(): Promise<SavedSummaryReport[]> {
  const response = await fetch("/api/reports", {
    credentials: "same-origin",
    cache: "no-store",
  });
  if (!response.ok) throw new Error(await readError(response));
  return (await response.json()) as SavedSummaryReport[];
}

export async function saveSummaryReport(filters: DashboardFilters): Promise<SavedSummaryReport> {
  const response = await fetch("/api/reports", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      period_from: filters.periodFrom || undefined,
      period_to: filters.periodTo || undefined,
      cost_center_id: filters.costCenterId ? Number(filters.costCenterId) : undefined,
      horizon_days: filters.horizonDays,
    }),
  });
  if (!response.ok) throw new Error(await readError(response));
  return (await response.json()) as SavedSummaryReport;
}

export async function downloadSummaryReportExcel(reportId: number): Promise<void> {
  const response = await fetch(`/api/reports/${reportId}/excel`, {
    credentials: "same-origin",
    cache: "no-store",
  });
  if (!response.ok) throw new Error(await readError(response));
  const file = await response.blob();
  const url = URL.createObjectURL(file);
  const link = document.createElement("a");
  link.href = url;
  link.download = `reporte-resumen-${reportId}.xlsx`;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
