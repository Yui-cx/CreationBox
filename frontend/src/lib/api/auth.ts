import type { Me, TokenResponse } from "../../types";
import { request } from "./client";

export async function register(username: string, password: string, email?: string): Promise<TokenResponse> {
  return request<TokenResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ username, password, email: email || undefined })
  });
}

export async function login(username: string, password: string): Promise<TokenResponse> {
  return request<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password })
  });
}

export async function fetchMe(): Promise<Me> {
  return request<Me>("/me");
}
