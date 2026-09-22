import { getFinancialDashboard } from "@/controllers/dashboard-controller";
import { DashboardView } from "@/views/dashboard-view";

export default function Home() {
  return <DashboardView dashboard={getFinancialDashboard()} />;
}
