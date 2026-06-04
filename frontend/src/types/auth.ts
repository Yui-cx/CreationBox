export type Me = {
  id: number;
  username: string;
  email?: string | null;
  is_admin: boolean;
  quota_total: number;
  quota_used: number;
  quota_remaining: number;
};

export type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};
