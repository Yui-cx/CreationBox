import type { ToolType } from "./tools";

export type GenerationListItem = {
  id: string;
  tool_type: ToolType;
  mode: string;
  status: string;
  output_content: string;
  created_at: string;
  completed_at?: string | null;
};

export type GenerationPayload = {
  tool_type: ToolType;
  mode: string;
  input_text?: string;
  input_url?: string;
  topic?: string;
  materials?: string;
  config: Record<string, string>;
};
