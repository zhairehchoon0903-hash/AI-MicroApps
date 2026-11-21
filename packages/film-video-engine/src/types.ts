export type AspectRatio = "9:16" | "16:9" | "1:1";

export type VideoTaskStatus =
  | "PENDING"
  | "RUNNING"
  | "SUCCEEDED"
  | "FAILED"
  | "UNKNOWN";

export interface VideoGenerationRequest {
  prompt: string;
  startImageUrl: string;
  durationSeconds: number;
  aspectRatio: AspectRatio;
  model?: string;
  /** Optional project/shot labels. Never put end-user personal information here. */
  tags?: string[];
}

export interface VideoQuote {
  providerId: string;
  modelId: string;
  estimatedCostUsd: number;
  currency: "USD";
  durationSeconds: number;
  aspectRatio: AspectRatio;
  pricingBasis: string;
  notes?: string[];
}

export interface VideoTask {
  providerId: string;
  taskId: string;
  status: VideoTaskStatus;
  outputUrl?: string;
  error?: string;
  raw: unknown;
}

export interface VideoProvider {
  readonly id: string;
  readonly label: string;
  quote(request: VideoGenerationRequest): Promise<VideoQuote>;
  generate(request: VideoGenerationRequest): Promise<VideoTask>;
  getTask(taskId: string): Promise<VideoTask>;
}

export interface VideoProviderSummary {
  id: string;
  label: string;
}
