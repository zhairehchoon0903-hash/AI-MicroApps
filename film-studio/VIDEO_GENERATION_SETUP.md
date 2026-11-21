# Video generation setup

The Video Lab is integrated with the existing FastAPI server. It does not need a separate web service.

## Providers supported in this first integration

- **Runway Dev API** — image-to-video via `POST /v1/image_to_video`; task status via `GET /v1/tasks/{id}`.
- **fal.ai Wan 3.0** — queue-based image-to-video; task status and result are polled from fal's queue API.

These are developer APIs and are separate from the Runway consumer subscription and from ChatGPT's connected Runway workspace. A consumer plan or its credits do not automatically fund the Dev API.

## Server environment variables

Set these in the environment used to start `film-studio/server.py`. Never put provider keys in `app.js`, HTML, browser storage, or a committed `.env` file.

### Runway Dev

- `RUNWAYML_API_SECRET` — Runway Dev API key.
- `RUNWAY_DEV_MODEL` — optional; defaults to `gen4.5`.
- `RUNWAY_DEV_PRICE_USD_PER_SECOND` — current USD per output second for that exact model and output tier. Verify the current Runway Dev pricing page before setting it.

The initial adapter supports 2–10 second clips at the configured 720p tier. 9:16 is mapped to 720:1280.

### fal.ai Wan 3.0

- `FAL_KEY` — fal.ai API key.
- `FAL_WAN3_PRICE_480P` — current USD per output second at 480p.
- `FAL_WAN3_PRICE_720P` — current USD per output second at 720p.
- `FAL_WAN3_PRICE_1080P` — current USD per output second at 1080p.

The price variables are intentionally not hard-coded. Keep them aligned with the live model pricing.

## How to use it

1. Create or connect a production project in **Production Engine**. The Video Lab only generates against a server-side production project.
2. Open **Video Lab**, choose the project, enter a specific motion prompt, and provide a public HTTPS starting-frame image URL or an image data URI no larger than 5 MB.
3. Compare the estimates. The cheapest configured provider is preselected, but you can choose another.
4. Enter a per-shot maximum and confirm the paid generation in the approval dialog.
5. Refresh the task to retrieve its status and, when complete, its output video URL.

The API re-quotes immediately before submission, checks the per-shot approval ceiling, and checks the remaining project budget. Each submitted task is recorded in `artifacts/video_generation.json`. A failed task remains in the ledger because a provider may still charge for processing; do not assume failed generations are refunded.

No retries or provider fallbacks happen automatically. Every retry is a new paid generation and requires a fresh quote and approval.

## Routes

- `GET /api/video/providers`
- `POST /api/projects/{project_id}/video/quote`
- `POST /api/projects/{project_id}/video/generate`
- `GET /api/projects/{project_id}/video/tasks`
- `GET /api/projects/{project_id}/video/tasks/{task_id}`

The existing Film Studio API authentication middleware protects these routes. API keys remain server-side.

## Important limitations

- The starting frame must currently be a public HTTPS URL or a data URI. Local asset upload/hosting is the next integration step.
- The first adapter is image-to-video, not text-to-video.
- Provider price estimates depend on operator-configured rates and are not a live provider quote. Always verify current provider pricing.
- No generation runs until API credentials, current rates, a production project, a valid image, and explicit user approval are all present.

Official API references:
- Runway Dev API: https://docs.dev.runwayml.com/api/
- Runway Dev pricing: https://docs.dev.runwayml.com/guides/pricing/
- fal.ai Wan 3.0 image-to-video: https://fal.ai/models/alibaba/wan-3.0/image-to-video/api
