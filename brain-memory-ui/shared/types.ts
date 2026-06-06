export interface ModelProfile {
  id: string;
  name: string;
  provider: "ollama" | "openai" | "openai_compatible";
  base_url: string;
  model: string;
  api_key_set: boolean;
  is_default: boolean;
  enabled: boolean;
}

export interface RuntimeState {
  cognitive_state: Record<string, unknown>;
  stability_metrics: Record<string, number>;
  personality_dna: Record<string, number>;
  narrative: { summary: string; coherence: number; version: number };
  beliefs: Record<string, { content: string; confidence: number }>;
  working_memory_count: number;
  timestamp: string;
}

export interface CaptureRequest {
  role: string;
  content: string;
  layer: string;
  importance?: number;
}

export interface ChatRequest {
  message: string;
  model_id?: string;
  use_memory?: boolean;
  temperature?: number;
}
