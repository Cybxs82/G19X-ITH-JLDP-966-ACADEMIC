"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getCurrentUser, type AuthUser } from "@/controllers/auth-controller";
import { ProfileView } from "@/views/profile-view";

export default function ProfilePage() {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isCheckingSession, setIsCheckingSession] = useState(true);

  useEffect(() => {
    void getCurrentUser()
      .then((currentUser) => {
        if (!currentUser) {
          router.replace("/");
          return;
        }
        setUser(currentUser);
      })
      .catch(() => router.replace("/"))
      .finally(() => setIsCheckingSession(false));
  }, [router]);

  if (isCheckingSession || !user) return <main className="auth-loading">Comprobando sesión...</main>;

  return <ProfileView user={user} onCancel={() => router.push("/")} onSaved={(updatedUser) => setUser(updatedUser)} />;
}