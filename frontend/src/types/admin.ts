export type AdminUserItem = {
  id: number;
  username: string;
  email?: string | null;
  status: "active" | "inactive";
  is_admin: boolean;
  quota_total: number;
  quota_used: number;
  quota_remaining: number;
  generation_count: number;
  created_at: string;
  last_login_at?: string | null;
};

export type AdminCreateUserPayload = {
  username: string;
  password: string;
  email?: string;
  is_admin: boolean;
  daily_quota_total?: number;
};

export type ProviderOption = {
  provider: string;
  label: string;
  models: string[];
  key_configured: boolean;
};

export type ModelConfig = {
  provider: string;
  model: string;
  options: ProviderOption[];
  updated_at?: string | null;
  updated_by?: number | null;
};
