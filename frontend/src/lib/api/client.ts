import { useAuthStore } from "../../store/auth";

export const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

export function clearAuthOnUnauthorized(status: number, detail?: unknown) {
  if (status === 401 || detail === "INVALID_TOKEN") {
    useAuthStore.getState().logout();
  }
}

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = useAuthStore.getState().accessToken;
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers ?? {})
    }
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    clearAuthOnUnauthorized(response.status, body.detail);
    throw new Error(body.detail || `HTTP_${response.status}`);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}
