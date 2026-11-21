import type {
  VideoGenerationRequest,
  VideoProvider,
  VideoProviderSummary,
  VideoQuote,
  VideoTask,
} from "./types.js";

export class VideoEngineError extends Error {
  constructor(message: string, readonly code: string) {
    super(message);
    this.name = "VideoEngineError";
  }
}

export class SpendApprovalRequiredError extends VideoEngineError {
  constructor(
    readonly quote: VideoQuote,
    readonly approvedMaxSpendUsd: number,
  ) {
    super(
      `Estimated cost $${quote.estimatedCostUsd.toFixed(2)} exceeds the approved ceiling of $${approvedMaxSpendUsd.toFixed(2)}.`,
      "SPEND_APPROVAL_REQUIRED",
    );
    this.name = "SpendApprovalRequiredError";
  }
}

export class VideoEngine {
  private readonly providers = new Map<string, VideoProvider>();

  register(provider: VideoProvider): this {
    if (this.providers.has(provider.id)) {
      throw new VideoEngineError(`Provider "${provider.id}" is already registered.`, "DUPLICATE_PROVIDER");
    }
    this.providers.set(provider.id, provider);
    return this;
  }

  listProviders(): VideoProviderSummary[] {
    return [...this.providers.values()].map(({ id, label }) => ({ id, label }));
  }

  private provider(providerId: string): VideoProvider {
    const provider = this.providers.get(providerId);
    if (!provider) {
      throw new VideoEngineError(`Video provider "${providerId}" is not configured.`, "PROVIDER_NOT_FOUND");
    }
    return provider;
  }

  async quote(request: VideoGenerationRequest, providerId: string): Promise<VideoQuote> {
    validateRequest(request);
    return this.provider(providerId).quote(request);
  }

  async quoteAll(request: VideoGenerationRequest): Promise<VideoQuote[]> {
    validateRequest(request);
    const results = await Promise.allSettled(
      [...this.providers.values()].map((provider) => provider.quote(request)),
    );
    return results
      .filter((result): result is PromiseFulfilledResult<VideoQuote> => result.status === "fulfilled")
      .map((result) => result.value)
      .sort((a, b) => a.estimatedCostUsd - b.estimatedCostUsd);
  }

  /**
   * Call only after the UI has shown the quote and the user has approved a
   * maximum USD amount. The quote is recalculated immediately before submit.
   */
  async generate(
    request: VideoGenerationRequest,
    providerId: string,
    approvedMaxSpendUsd: number,
  ): Promise<{ quote: VideoQuote; task: VideoTask }> {
    if (!Number.isFinite(approvedMaxSpendUsd) || approvedMaxSpendUsd < 0) {
      throw new VideoEngineError("A valid user-approved USD spending ceiling is required.", "INVALID_SPEND_APPROVAL");
    }

    const provider = this.provider(providerId);
    const quote = await this.quote(request, providerId);

    if (quote.estimatedCostUsd > approvedMaxSpendUsd) {
      throw new SpendApprovalRequiredError(quote, approvedMaxSpendUsd);
    }

    const task = await provider.generate(request);
    return { quote, task };
  }

  async getTask(providerId: string, taskId: string): Promise<VideoTask> {
    if (!taskId.trim()) {
      throw new VideoEngineError("A task id is required.", "INVALID_TASK_ID");
    }
    return this.provider(providerId).getTask(taskId);
  }
}

export function validateRequest(request: VideoGenerationRequest): void {
  if (!request.prompt?.trim()) {
    throw new VideoEngineError("A video prompt is required.", "INVALID_PROMPT");
  }
  if (request.prompt.length > 1000) {
    throw new VideoEngineError("The selected Runway image-to-video endpoint accepts prompts up to 1,000 characters.", "PROMPT_TOO_LONG");
  }
  if (!Number.isInteger(request.durationSeconds) || request.durationSeconds < 2 || request.durationSeconds > 10) {
    throw new VideoEngineError("Duration must be a whole number between 2 and 10 seconds for this first adapter.", "INVALID_DURATION");
  }
  try {
    const url = new URL(request.startImageUrl);
    if (url.protocol !== "https:") throw new Error("HTTPS required");
  } catch {
    throw new VideoEngineError("The starting-frame image must be a valid HTTPS URL.", "INVALID_START_IMAGE");
  }
}
