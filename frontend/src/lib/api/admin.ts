import type { AdminCreateUserPayload, AdminUserItem, ModelConfig } from "../../types";
import { request } from "./client";

export async function fetchAdminUsers(): Promise<AdminUserItem[]> {
  return request<AdminUserItem[]>("/admin/users");
}

export async function createAdminUser(payload: AdminCreateUserPayload): Promise<AdminUserItem> {
  return request<AdminUserItem>("/admin/users", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function updateAdminUser(id: number, payload: Partial<Pick<AdminUserItem, "email" | "status" | "is_admin">>): Promise<AdminUserItem> {
  return request<AdminUserItem>(`/admin/users/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export async function updateAdminUserQuota(id: number, totalQuota: number, usedQuota: number): Promise<AdminUserItem> {
  return request<AdminUserItem>(`/admin/users/${id}/quota`, {
    method: "PATCH",
    body: JSON.stringify({ total_quota: totalQuota, used_quota: usedQuota })
  });
}

export async function resetAdminUserPassword(id: number, password: string): Promise<AdminUserItem> {
  return request<AdminUserItem>(`/admin/users/${id}/reset-password`, {
    method: "POST",
    body: JSON.stringify({ password })
  });
}

export async function fetchModelConfig(): Promise<ModelConfig> {
  return request<ModelConfig>("/admin/model-config");
}

export async function updateModelConfig(provider: string, model: string): Promise<ModelConfig> {
  return request<ModelConfig>("/admin/model-config", {
    method: "PUT",
    body: JSON.stringify({ provider, model })
  });
}

export async function validateModelConfig(provider?: string, model?: string): Promise<{ ok: boolean; provider: string; model: string }> {
  return request<{ ok: boolean; provider: string; model: string }>("/admin/model-config/validate", {
    method: "POST",
    body: JSON.stringify({ provider, model })
  });
}
