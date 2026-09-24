export type AuthUser = {
  id: string;
  email: string;
  full_name: string;
  role: "cfo" | "analista" | "administrador";
  is_active: boolean;
};

type AuthResponse = { user: AuthUser };

const apiUrl = process.env.CFO_API_URL ?? "http://localhost:8000/api/v1";

function getNetworkError(error: unknown): Error {
  if (error instanceof TypeError && error.message.toLowerCase().includes("fetch")) {
    return new Error("No se puede conectar con la API. Inicia FastAPI en http://localhost:8000.");
  }
  return error instanceof Error ? error : new Error("No se pudo completar la operación");
}

async function readError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string };
    return body.detail ?? "No se pudo completar la operación";
  } catch {
    return "No se pudo completar la operación";
  }
}

export async function getCurrentUser(): Promise<AuthUser | null> {
  try {
    const response = await fetch(`${apiUrl}/auth/session`, { credentials: "include", cache: "no-store" });
    if (response.status === 401) return null;
    if (!response.ok) throw new Error(await readError(response));
    return ((await response.json()) as AuthResponse).user;
  } catch (error) {
    throw getNetworkError(error);
  }
}

export async function login(email: string, password: string): Promise<AuthUser> {
  try {
    const response = await fetch(`${apiUrl}/auth/login`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!response.ok) throw new Error(await readError(response));
    return ((await response.json()) as AuthResponse).user;
  } catch (error) {
    throw getNetworkError(error);
  }
}

export async function register(email: string, fullName: string, password: string): Promise<AuthUser> {
  try {
    const response = await fetch(`${apiUrl}/auth/register`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, full_name: fullName, password }),
    });
    if (!response.ok) throw new Error(await readError(response));
    return ((await response.json()) as AuthResponse).user;
  } catch (error) {
    throw getNetworkError(error);
  }
}

export async function logout(): Promise<void> {
  const response = await fetch(`${apiUrl}/auth/logout`, {
    method: "POST",
    credentials: "include",
  });
  if (!response.ok) throw new Error(await readError(response));
}
