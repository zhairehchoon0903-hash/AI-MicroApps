import type {
  VideoGenerationRequest,
  VideoProvider,
  VideoQuote,
  VideoResolution,
  VideoTask,
  VideoTaskStatus,
} from "../types.js";
import { VideoEngineError } from "../engine.js";

const QUEUE_BASE = "https://queue.fal.run";
type FalPriceTable = Record<VideoResolution, number>;

export interface FalWan3ProviderOptions {
  apiKey: string;
  priceUsdPerSecond: FalPriceTable;
  endpointId?: string;
  fetchImpl?: typeof fetch;
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" ? value as Record<string, unknown> : {};
}

function normalizeStatus(value: unknown, failed: boolean): VideoTaskStatus {
  if (failed) return "FAILED";
  const status = String(value ?? "").toUpperCase();
  if (status === "IN_QUEUE") return "PENDING";
  if (status === "IN_PROGRESS") return "RUNNING";
  if (status === "COMPLETED") return "SUCCEEDED";
  return "UNKNOWN";
}

export class FalWan3Provider implements VideoProvider {
  readonly id = "fal-wan3";
  readonly label = "fal.ai — Wan 3.0";

  private readonly fetchImpl: typeof fetch;
  private readonly endpointId: string;

  constructor(private readonly options: FalWan3ProviderOptions) {
    if (!options.apiKey.trim()) throw new VideoEngineError("FAL_KEY is required.", "MISSING_PROVIDER_KEY");
    for (const resolution of ["480p", "720p", "1080p"] as const) {
      const price = options.priceUsdPerSecond[resolution];
      if (!Number.isFinite(price) || price <= 0) {
        throw new VideoEngineError(`A current fal.ai price is required for ${resolution}.`, "MISSING_PRICE_CONFIGURATION");
      }
    }
    this.fetchImpl = options.fetchImpl ?? fetch;
    this.endpointId = options.endpointId ?? "alibaba/wan-3.0/image-to-video";
  }

  async quote(request: VideoGenerationRequest): Promise<VideoQuote> {
    const resolution = request.resolution ?? "720p";
    const rate = this.options.priceUsdPerSecond[resolution];
    return {
      providerId: this.id,
      modelId: this.endpointId,
      estimatedCostUsd: Number((rate * request.durationSeconds).toFixed(4)),
      currency: "USD",
      durationSeconds: request.durationSeconds,
      aspectRatio: request.aspectRatio,
      resolution,
      pricingBasis: `Configured fal.ai rate $${rate.toFixed(4)} per output second × ${request.durationSeconds} seconds.`,
      notes: ["The server administrator must keep the price table aligned with the current endpoint pricing."],
    };
  }

  async generate(request: VideoGenerationRequest): Promise<VideoTask> {
    const response = await this.fetchImpl(`${QUEUE_BASE}/${this.endpointId}`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({
        prompt: request.prompt,
        start_image_url: request.startImageUrl,
        duration: request.durationSeconds,
        resolution: request.resolution ?? "720p",
        aspect_ratio: request.aspectRatio,
        audio: request.audio ?? false,
      }),
    });

    const payload = await readJson(response);
    if (!response.ok) {
      throw new VideoEngineError(
        `fal.ai rejected the generation request: ${messageFrom(payload, response.status)}`,
        "PROVIDER_REQUEST_FAILED",
      );
    }

    const record = asRecord(payload);
    const taskId = typeof record.request_id === "string" ? record.request_id : "";
    if (!taskId) {
      throw new VideoEngineError("fal.ai accepted no recognizable request id; inspect the provider response before retrying.", "MISSING_PROVIDER_TASK_ID");
    }

    return {
      providerId: this.id,
      taskId,
      status: normalizeStatus(record.status, false),
      raw: payload,
    };
  }

  async getTask(taskId: string): Promise<VideoTask> {
    const encodedId = encodeURIComponent(taskId);
    const statusResponse = await this.fetchImpl(
      `${QUEUE_BASE}/${this.endpointId}/requests/${encodedId}/status`,
      { method: "GET", headers: this.headers() },
    );
    const statusPayload = await readJson(statusResponse);
    if (!statusResponse.ok) {
      throw new VideoEngineError(
        `fal.ai status lookup failed: ${messageFrom(statusPayload, statusResponse.status)}`,
        "PROVIDER_POLL_FAILED",
      );
    }

    const statusRecord = asRecord(statusPayload);
    const failed = typeof statusRecord.error === "string" && statusRecord.error.length > 0;
    const status = normalizeStatus(statusRecord.status, failed);
    if (status !== "SUCCEEDED") {
      return {
        providerId: this.id,
        taskId,
        status,
        error: failed ? String(statusRecord.error) : undefined,
        raw: statusPayload,
      };
    }

    const resultResponse = await this.fetchImpl(
      `${QUEUE_BASE}/${this.endpointId}/requests/${encodedId}`,
      { method: "GET", headers: this.headers() },
    );
    const resultPayload = await readJson(resultResponse);
    if (!resultResponse.ok) {
      throw new VideoEngineError(
        `fal.ai result retrieval failed: ${messageFrom(resultPayload, resultResponse.status)}`,
        "PROVIDER_RESULT_FAILED",
      );
    }

    const resultRecord = asRecord(resultPayload);
    const video = asRecord(resultRecord.video);
    return {
      providerId: this.id,
      taskId,
      status: "SUCCEEDED",
      outputUrl: typeof video.url === "string" ? video.url : undefined,
      raw: resultPayload,
    };
  }

  private headers(): HeadersInit {
    return {
      Authorization: `Key ${this.options.apiKey}`,
      "Content-Type": "application/json",
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
