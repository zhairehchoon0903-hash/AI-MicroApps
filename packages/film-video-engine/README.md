# Film Video Engine

A server-side, provider-neutral video generation layer for the Film Studio.

## Why this package exists

The editor, screenplay, character bible, shot list, continuity records, and Remotion renderer must not depend on one generation vendor. This package defines one contract for video providers and includes a first working adapter for the Runway Dev API. Additional adapters can be registered without changing the editor or renderer.

This is a server-side package. Never expose provider API keys in browser code.

## First provider: Runway Dev

Runway Dev is separate from the consumer Runway subscription and the connected ChatGPT Runway workspace. It uses a developer API key and pay-as-you-go credits. A connected consumer Free plan does not grant Dev API credits.

Configure these environment variables on the server:

- `RUNWAYML_API_SECRET` — API secret from Runway Dev.
- `RUNWAY_DEV_PRICE_USD_PER_SECOND` — current per-second rate for the selected model and settings. Keep this value current with the official pricing page; do not assume a permanent price.
- `RUNWAY_DEV_MODEL` — optional model id; defaults to `gen4.5`.

The adapter calls `POST https://api.dev.runwayml.com/v1/image_to_video` and polls `GET /v1/tasks/{id}`. It sends the required `X-Runway-Version: 2024-11-06` header.

The vertical Reels ratio maps to Runway's `720:1280` ratio. The direct image-to-video endpoint currently accepts integer durations from 2 to 10 seconds.

## Safe generation flow

1. The UI calls `engine.quote(request, providerId)` and displays the estimated cost.
2. The user explicitly approves a maximum spend for that generation.
3. The server calls `engine.generate(request, providerId, approvedMaxSpendUsd)`.
4. The engine recalculates the quote immediately before submission and refuses if the estimate exceeds the approved ceiling.
5. The editor stores the provider task id and polls `getTask`; it does not block a web request while a video renders.

There is no automatic provider fallback after a generation is submitted. A retry or a different provider is a new generation and must be quoted and approved separately.

## Adding another provider

Implement the `VideoProvider` interface in `src/types.ts`, then register it with `VideoEngine.register()`. Each adapter owns its authentication, model-specific payload mapping, task polling, and pricing quote. Keep provider-specific request fields out of the editor and screenplay schema.

## Current scope

- Provider interface and registry
- Per-provider quote and cost ceiling
- Explicit approval ceiling before a paid generation
- Runway Dev image-to-video adapter
- Task status normalization
- No API key, purchase, or generation is performed by this package until the server is configured and the user approves a quoted generation

Official references:
- https://docs.dev.runwayml.com/api/
- https://docs.dev.runwayml.com/guides/pricing/
- https://docs.dev.runwayml.com/model-routers/
