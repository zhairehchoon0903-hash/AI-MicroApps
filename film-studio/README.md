¶∑©j∑ù# OpenMontage Film Studio

A mobile-first director workspace with a local API bridge to the repository's real OpenMontage pipeline catalog and project library.

## Run the connected Film Studio

From the repository root:

```bash
python film-studio/server.py
```

Open **http://127.0.0.1:4173** on the same computer. For phone or Codespaces access on a trusted private network, configure a bearer token and bind the server to the network interface:

```bash
export FILM_STUDIO_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
echo "$FILM_STUDIO_TOKEN"  # keep this private; enter it in the app
export FILM_STUDIO_HOST=0.0.0.0
python film-studio/server.py
```

Then open `http://YOUR-COMPUTER-LAN-IP:4173` on the phone and paste the same token into the Film Studio access field. The token is kept in the current browser tab's session storage. The server is loopback-only by default and refuses remote binding without a token. Keep it on a trusted private network; do not expose this development server directly to the public internet.

## Working features

- Create and manage film projects in the browser while offline.
- Connect to the local OpenMontage API to read the actual validated pipeline manifests and production library.
- Create real `projects/<slug>/` folders with `project.json`, `meta.json`, artifact storage, asset folders, and render folders. These are visible to Backlot.
- Choose from actual pipeline definitions; view each pipeline's declared stages and human-approval gates.
- Set a planning budget cap within the project brief.
- Script notes, scene planning, character continuity bible, and shot planning.
- Export one film or the complete local library as JSON: import backups without overwriting existing projects.
- Responsive phone and desktop layouts.

## Production preflight

Open the Production Engine, choose a project in **Production preflight**, and select **Inspect readiness**. The API reads the project's validated pipeline manifest and the canonical `checkpoint_<stage>.json` records through OpenMontage's checkpoint reader. It checks required artifacts inside completed predecessor checkpoints, respects predecessor approval gates, surfaces legacy checkpoints that lack approval evidence, and reports each stage's checkpoint state, review focus, declared tools, and any recorded `cost_log.json` totals. It also identifies the next stage that is not yet complete. This is an inspection only: it does not invoke agents, reserve budget, call providers, download assets, generate media, or render. The response always reports `execution_authorized: false`.

The endpoint is `GET /api/projects/{project_id}/preflight`.

The Production Engine also exposes `GET /api/capabilities`, backed by OpenMontage's `registry.provider_menu_summary()`. It reports locally discovered provider availability, composition runtimes, setup offers, and runtime warnings. This is dependency/configuration discovery only; it does not call a provider's `.execute()` method or make paid API requests.

## Director handoff

Select a project in Production preflight and choose **Prepare director handoff**. The API packages the saved screenplay, scene plan, character continuity notes, shot plan, project brief, budget cap, and pipeline stage contracts/director-skill paths into `projects/<project_id>/artifacts/director_handoff.json`. This is a non-canonical planning artifact. The OpenMontage agent remains the orchestrator and must read `AGENT_GUIDE.md`, the selected manifest, checkpoint protocol, and each stage director skill before stage work.

Endpoint: `POST /api/projects/{project_id}/director-handoff`. It only writes the local JSON package; it does not start an agent, reserve budget, call providers, generate media, download assets, or render. Execution and spending authorization remain false.

## Agent-session handoff

Preparing a director handoff also writes `projects/<project_id>/artifacts/agent_session.md`. The prompt names the exact repository guide, selected pipeline manifest, executive-producer skill (when declared), stage-director skills, checkpoint protocol, and project artifact paths. The **Copy agent session prompt** action copies these instructions for pasting into the OpenMontage coding-agent session in the Codespace. This is an explicit handoff to the agent host, not a claim that the Film Studio starts an agent process; the repository currently provides agent instructions and tools, not a callable agent-session server.

The prompt authorizes read-only inspection and non-paid planning only. It expressly prohibits paid provider calls, generation, downloads, and rendering until separately approved. The selected pipeline manifest remains the authority for stage order and human-approval gates.

## Safety boundary

Creating a production project only scaffolds its folder and initial metadata. It does **not** launch an agent, call an AI provider, generate images/video/audio, download media, or render. The budget cap planning metadata, not a price quote. Generation and rendering require separate implementation, provider configuration, explicit director approval, and cost controls.

The browser workspace currently stores its creative notes in local storage on that device. The API also exposes a validated `PUT` endpoint for server-side script, scene, character, and shot data; full browser-to-project synchronization is still in progress. Backlot remains the read-only production monitor.


For GitHub Copilot Chat in Codespaces, the repository also provides the `/film-studio-agent` prompt in `.github/prompts/film-studio-agent.prompt.md`. After preparing a handoff, invoke that prompt and provide the project ID if it is not already clear. It reads the saved local project handoff and follows the repository's agent contract; it does not bypass approval gates.
