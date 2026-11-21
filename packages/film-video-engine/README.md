# Film Video Engine

A server-side, provider-neutral video generation layer for the Film Studio.

## Why this package exists

The editor, screenplay, character bible, shot list, continuity records, and Remotion renderer must not depend on one generation vendor. This package defines one contract for video providers and includes adapters for Runway Dev and fal.ai's Wan 3.0 image-to-video endpoint. Additional adapters can be registered without changing the editor or renderer.

This is a server-side package. Never expose provider API keys in browser code.

## Providers

### Runway Dev

Runway Dev is separate from the consumer Runway subscription and the connected ChatGPT Runway workspace. It uses a developer API key and pay-as-you-go credits. A connected consumer Free plan does not grant Dev API credits.

Configure on the server:

- `RUNWAYML_API_SECRET`
- `RUNWAY_DEV_MODEL` (defaults to `gen4.5`)
- `RUNWAY_DEV_RESOLUTION` (defaults to `720p`)
- `RUNWAY_DEV_PRICE_USD_PER_SECOND` — current rate for that exact model/settings combination

The adapter calls `POST https://api.dev.runwayml.com/v1/image_to_video` and polls `GET /v1/tasks/{id}`. It sends `X-Runway-Version: 2024-11-06`. The 9:16 Reels ratio maps to `720:1280`.

### fal.ai — Wan 3.0

Configure on the server:

- `FAL_KEY`
- `FAL_WAN3_PRICE_480P`
- `FAL_WAN3_PRICE_720P`
- `FAL_WAN3_PRICE_1080P`

The price variables are USD per generated second and must be kept aligned with the live endpoint pricing. The adapter uses fal's queue API at `https://queue.fal.run/alibaba/wan-3.0/image-to-video`, then retrieves the result after the task completes. It supports vertical 9:16 output and selectable 480p, 720p, and 1080p.

## Safe generation flow

1. The UI calls `engine.quoteAll(request)` and displays available provider quotes.
2. The user selects a provider and explicitly approves a maximum spend for that generation.
3. The server calls `engine.generate(request, providerId, approvedMaxSpendUsd)`.
4. The engine recalculates the quote immediately before submission and refuses if the estimate exceeds the approved ceiling.
5. The editor stores the provider task id and polls `getTask`; it does not block a web request while a video renders.

There is no automatic provider fallback after a generation is submitted. A retry or a different provider is a new generation and must be quoted and approved separately.

## Adding another provider

Implement the `VideoProvider` interface in `src/types.ts`, then register it with `VideoEngine.register()`. Each adapter owns its authentication, model-specific payload mapping, task polling, and pricing quote. Keep provider-specific request fields out of the editor and screenplay schema.

## Current scope

- Provider interface and registry
- Quote comparison across configured providers
- Per-provider cost estimates and explicit approval ceiling
- Runway Dev image-to-video adapter
- fal.ai Wan 3.0 image-to-video adapter
- Task status normalization
- No API key, purchase, or generation is performed until the server is configured and the user approves a quoted generation

Official references:
- https://docs.dev.runwayml.com/api/
- https://docs.dev.runwayml.com/guides/pricing/
- https://fal.ai/models/alibaba/wan-3.0/image-to-video/api
- https://fal.ai/docs/api-reference/inference-api/queue/submit-path
