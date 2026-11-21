import type {
  AspectRatio,
  VideoGenerationRequest,
  VideoProvider,
  VideoQuote,
  VideoResolution,
  VideoTask,
  VideoTaskStatus,
} from "../types.js";
import { VideoEngineError } from "../engine.js";

const API_BASE = "https://api.dev.runwayml.com";
const API_VERSION = "2024-11-06";

export interface RunwayDevProviderOptions {
  apiKey: string;
  priceUsdPerSecond: number;
  model?: string;
  resolution?: VideoResolution;
  fetchImpl?: typeof fetch;
}

const RUNWAY_RATIO: Record<AspectRatio, string> = {
  "9:16": "720:1280",
  "16:9": "1280:720",
  "1:1": "960:960",
};

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" ? value as Record<string, unknown> : {};
}

function normalizeStatus(value: unknown): VideoTaskStatus {
  const status = String(value ?? "").toUpperCase();
  if (["PENDING", "THROTTLED"].includes(status)) return "PENDING";
  if (["RUNNING", "PROCESSING"].includes(status)) return "RUNNING";
  if (["SUCCEEDED", "COMPLETED"].includes(status)) return "SUCCEEDED";
  if (["FAILED", "CANCELLED"].includes(status)) return "FAILED";
  return "UNKNOWN";
}

function extractOutputUrl(payload: Record<string, unknown>): string | undefined {
  const output = payload.output;
  if (typeof output === "string") return output;
  if (Array.isArray(output) && typeof output[0] === "string") return output[0];
  if (typeof payload.outputUrl === "string") return payload.outputUrl;
  return undefined;
}

export class RunwayDevProvider implements VideoProvider {
  readonly id = "runway-dev";
  readonly label = "Runway Dev API";

  private readonly fetchImpl: typeof fetch;
  private readonly model: string;
  private readonly resolution: VideoResolution;

  constructor(private readonly options: RunwayDevProviderOptions) {
    if (!options.apiKey.trim()) throw new VideoEngineError("RUNWAYML_API_SECRET is required.", "MISSING_PROVIDER_KEY");
    if (!Number.isFinite(options.priceUsdPerSecond) || options.priceUsdPerSecond <= 0) {
      throw new VideoEngineError("A current per-second Runway Dev price must be configured on the server.", "MISSING_PRICE_CONFIGURATION");
    }
    this.fetchImpl = options.fetchImpl ?? fetch;
    this.model = options.model ?? "gen4.5";
    this.resolution = options.resolution ?? "720p";
  }

  async quote(request: VideoGenerationRequest): Promise<VideoQuote> {
    const modelId = request.model ?? this.model;
    const resolution = request.resolution ?? this.resolution;
    if (modelId !== this.model || resolution !== this.resolution) {
      throw new VideoEngineError(
        `No price configuration exists for ${modelId} at ${resolution}. Configure a separate provider instance and rate before using it.`,
        "MODEL_PRICE_NOT_CONFIGURED",
      );
    }
    const estimatedCostUsd = Number((this.options.priceUsdPerSecond * request.durationSeconds).toFixed(4));
    return {
      providerId: this.id,
      modelId,
      estimatedCostUsd,
      currency: "USD",
      durationSeconds: request.durationSeconds,
      aspectRatio: request.aspectRatio,
      resolution,
      pricingBasis: `Configured rate $${this.options.priceUsdPerSecond.toFixed(4)} per output second × ${request.durationSeconds} seconds.`,
      notes: ["The server administrator must keep the configured rate aligned with the selected model and settings."],
    };
  }

  async generate(request: VideoGenerationRequest): Promise<VideoTask> {
    const response = await this.fetchImpl(`${API_BASE}/v1/image_to_video`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({
        model: request.model ?? this.model,
        promptImage: request.startImageUrl,
        promptText: request.prompt,
        ratio: RUNWAY_RATIO[request.aspectRatio],
        duration: request.durationSeconds,
      }),
    });

    const payload = await readJson(response);
    if (!response.ok) {
      throw new VideoEngineError(
        `Runway Dev rejected the generation request: ${messageFrom(payload, response.status)}`,
        "PROVIDER_REQUEST_FAILED",
      );
    }

    const record = asRecord(payload);
    const taskId = typeof record.id === "string" ? record.id : typeof record.taskId === "string" ? record.taskId : "";
    if (!taskId) {
      throw new VideoEngineError("Runway Dev accepted no recognizable task id; inspect the provider response before retrying.", "MISSING_PROVIDER_TASK_ID");
    }

    return {
      providerId: this.id,
      taskId,
      status: normalizeStatus(record.status),
      outputUrl: extractOutputUrl(record),
      raw: payload,
    };
  }

  async getTask(taskId: string): Promise<VideoTask> {
    const response = await this.fetchImpl(`${API_BASE}/v1/tasks/${encodeURIComponent(taskId)}`, {
      method: "GET",
      headers: this.headers(),
    });
    const payload = await readJson(response);
    if (!response.ok) {
      throw new VideoEngineError(
        `Runway Dev task lookup failed: ${messageFrom(payload, response.status)}`,
        "PROVIDER_POLL_FAILED",
      );
    }

    const record = asRecord(payload);
    return {
      providerId: this.id,
      taskId,
      status: normalizeStatus(record.status),
      outputUrl: extractOutputUrl(record),
      error: typeof record.failure === "string" ? record.failure : undefined,
      raw: payload,
    };
  }

  private headers(): HeadersInit {
    return {
      Authorization: `Bearer ${this.options.apiKey}`,
      "Content-Type": "application/json",
      "X-Runway-Version": API_VERSION,
    };
  }
}

async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return {};
  }
}

function messageFrom(payload: unknown, status: number): string {
  const record = asRecord(payload);
  if (typeof record.message === "string") return record.message;
  if (typeof record.error === "string") return record.error;
  return `HTTP ${status}`;
}
