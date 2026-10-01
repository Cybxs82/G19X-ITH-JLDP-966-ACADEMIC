"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getCurrentUser, logout, type AuthUser } from "@/controllers/auth-controller";
import { financialDashboard } from "@/models/financial-model";
import { DashboardView } from "@/views/dashboard-view";
import { ERPUploadView } from "@/views/erp-upload-view";

export default function IngestionPage() {
  const router = useRouter();
  const [isCheckingSession, setIsCheckingSession] = useState(true);
  const [user, setUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    void getCurrentUser()
      .then((user) => {
        if (!user) {
          router.replace("/");
          return;
        }
        setUser(user);
      })
      .catch(() => router.replace("/"))
      .finally(() => setIsCheckingSession(false));
  }, [router]);

  if (isCheckingSession || !user) return <main className="auth-loading">Comprobando sesión...</main>;

  return (
    <DashboardView
      dashboard={financialDashboard}
      user={user}
      activeSection="Carga ERP"
      onLogout={async () => { await logout(); router.replace("/"); }}
      onEditProfile={() => router.push("/profile")}
      onOpenDashboard={() => router.push("/")}
      onOpenIngestion={() => router.push("/ingestion")}
    >
      <ERPUploadView />
    </DashboardView>
  );
}