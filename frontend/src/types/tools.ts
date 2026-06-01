export type ToolType = "humanize" | "aigc_reduce" | "generate";

export type ToolMode = {
  id: string;
  label: string;
  limit?: number;
};

export type ToolConfig = {
  id: ToolType;
  title: string;
  kicker: string;
  description: string;
  tag: string;
  modes: ToolMode[];
  generateLabel: string;
  sourceLabel: string;
  sourceHelper: string;
  textPlaceholder: string;
  linkPlaceholder?: string;
  linkHelper?: string;
  styleLabel?: string;
  toneLabel?: string;
  styles: string[];
  tones: string[];
  examples: string[];
};
