import { useAuthStore } from "../../store/auth";
import type { GenerationListItem, GenerationPayload } from "../../types";
import { API_BASE, clearAuthOnUnauthorized, request } from "./client";

export async function fetchHistory(): Promise<GenerationListItem[]> {
  return request<GenerationListItem[]>("/generations?limit=10");
}

export async function deleteHistoryItem(id: string): Promise<void> {
  await request(`/generations/${id}`, { method: "DELETE" });
}

export async function exportMarkdown(id: string): Promise<string> {
  const token = useAuthStore.getState().accessToken;
  const response = await fetch(`${API_BASE}/generations/${id}/export-markdown`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {}
  });
  if (!response.ok) throw new Error("EXPORT_FAILED");
  return response.text();
}

export type StreamCallbacks = {
  onMetadata: (data: Record<string, unknown>) => void;
  onDelta: (text: string) => void;
  onDone: (generationId: string) => void;
  onError: (message: string) => void;
};

export async function streamGeneration(payload: GenerationPayload, callbacks: StreamCallbacks): Promise<void> {
  const token = useAuthStore.getState().accessToken;
  const response = await fetch(`${API_BASE}/generations/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    },
    body: JSON.stringify(payload)
  });
  if (!response.ok || !response.body) {
    const body = await response.json().catch(() => ({}));
    clearAuthOnUnauthorized(response.status, body.detail);
    throw new Error(body.detail || "GENERATION_FAILED");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() ?? "";
    for (const raw of events) {
      const lines = raw.split("\n");
      const eventLine = lines.find((line) => line.startsWith("event: "));
      const dataLine = lines.find((line) => line.startsWith("data: "));
      if (!eventLine || !dataLine) continue;
      const event = eventLine.replace("event: ", "");
      const data = JSON.parse(dataLine.replace("data: ", ""));
      if (event === "metadata") callbacks.onMetadata(data);
      if (event === "delta") callbacks.onDelta(data.text ?? "");
      if (event === "done") callbacks.onDone(data.generation_id);
      if (event === "error") callbacks.onError(data.message ?? data.code ?? "生成失败");
    }
  }
}
