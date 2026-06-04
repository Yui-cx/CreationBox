import { useAuthStore } from "../../store/auth";
import { API_BASE, clearAuthOnUnauthorized } from "./client";

export async function inpaintImage(formData: FormData): Promise<Blob> {
  const token = useAuthStore.getState().accessToken;
  const response = await fetch(`${API_BASE}/images/inpaint`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    clearAuthOnUnauthorized(response.status, body.detail);
    throw new Error(body.detail || "INPAINT_FAILED");
  }
  return response.blob();
}
