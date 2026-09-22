import { getFinancialDashboard } from "@/controllers/dashboard-controller";
import { DashboardView } from "@/views/dashboard-view";

export default async function Home() {
  return <DashboardView dashboard={await getFinancialDashboard()} />;
}
