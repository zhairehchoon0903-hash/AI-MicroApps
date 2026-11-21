# Episode Director — local screenplay breakdown

The Episode Director turns a screenplay or episode story beats into a structured JSON production plan using the existing local Ollama text adapter. It does not generate media or run a render.

## Workflow

1. Create or select a film in Film Studio.
2. Open **Episode Director** and confirm the selected project.
3. Paste the episode screenplay or story beats. Add director instructions and select an installed Ollama model. `qwen2.5:3b` is the lightweight starting suggestion for a constrained Codespace; use a larger model only if the server has enough memory and the model is already installed.
4. Check local model readiness. Generation requires an explicit browser confirmation and calls `POST /api/ai/director` with role `episode_director`.
5. Review and edit the returned JSON. The UI validates required scene and shot fields and displays counts and canon checks.
6. Only **Approve & save** replaces the project's Scene Board and Shot Planner entries. The screenplay and character profiles are preserved. The existing project save endpoint persists the approved data.

## Output contract

Top-level fields: `episode_title`, `logline`, `canon_checks`, `scenes`. Each scene contains `scene_number`, `slugline`, `purpose`, `location`, `time`, `objective`, `conflict`, `turning_point`, `emotional_change`, `transition`, and `shots`. Each shot contains `shot_number`, `title`, `framing`, `lens`, `camera_movement`, `action`, `performance`, `dialogue`, `sound`, `lighting`, `continuity`, and `generation_prompt`.

The server asks for strict JSON, 3–8 scenes and 2–5 shots per scene when the source supports that scope, and a maximum 6,000-token response budget. The UI enforces a maximum of 100 scenes and 500 shots. Unknown creative facts should remain blank or be identified in `canon_checks`; the model must not silently invent canon. For projects whose title includes `THE LAST BLOODLINE`, the prompt includes the currently confirmed premise and sword-plus-magic combat identity as guardrails.

## Safety and limitations

- Ollama text generation only; no cloud model or media provider is called.
- The feature never downloads a model. The requested model must already be installed and reachable by the server's loopback Ollama URL.
- Generation is not automatic on page load. A user confirmation is required.
- The generated plan is not saved until the director validates and approves it.
- Saving replaces the current scene and shot arrays for that project; the confirmation dialog states this explicitly.
- Existing video generation still requires its separate quote, spend limit, and per-shot approval.
- The generated `generation_prompt` fields are planning text only; they do not trigger image/video generation.
