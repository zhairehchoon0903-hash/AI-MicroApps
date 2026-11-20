¦·©j·# OpenMontage Film Studio

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

## Local GitHub Copilot CLI agent (recommended)

Film Studio can run the official GitHub Copilot CLI inside the Codespace. This is available on all Copilot plans, subject to organization policy. Install Node.js 22 or later, then run `npm install -g @github/copilot`. Start `copilot` once, enter `/login`, complete sign-in, and approve workspace trust if prompted. Exit the interactive CLI after setup.

In **Production Engine → Production preflight**, prepare the director handoff, check **Local Copilot CLI**, then choose **Start local read-only agent** and confirm. The server launches Copilot CLI in piped-prompt mode as a local process in the repository, records its log and task status, and lets you refresh the result. The command uses `--available-tools=read` so the CLI exposes only its read tool; shell, write, URL, memory, and all other tools are unavailable. It also disables repository hooks, workspace MCP, and extensions for the prompt run, strips automatic-approval environment switches, and never uses `--allow-all`. The local task receives the director handoff plus a fresh preflight and canonical checkpoint snapshot, and can also inspect local project files. Authentication and workspace trust are not tested by the connection check; complete the one-time interactive setup first.

Starting a task may consume Copilot AI credits or other metered usage under your plan. No media generation, paid production providers, downloads, budget reservations, file edits, or rendering are authorized by this read-only task.

GitHub CLI references: https://docs.github.com/en/copilot/how-tos/copilot-cli/set-up-copilot-cli/install-copilot-cli and https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-programmatic-reference

## GitHub Copilot Cloud Agent connection

Film Studio can connect to GitHub's official Copilot Cloud Agent tasks API. In the Codespace, make sure GitHub CLI is authenticated as your user (`gh auth status`; if needed, run `gh auth login`). The server reads the user token with `gh auth token` in memory; it never sends the token to the browser or writes it into project files. Alternatively, configure `GH_TOKEN` with a user-to-server token. Do not use a server-to-server installation token: GitHub's agent tasks API requires a user-to-server token.

The account needs GitHub Copilot Business or Enterprise, and Copilot Cloud Agent must be enabled for the repository. For a fine-grained personal access token, grant the repository **Agent tasks: read and write** permission to start tasks (read permission is sufficient to list/check them). Open **Production Engine → Production preflight**, select a project, prepare the director handoff, check the connection, then choose **Start cloud agent task** and confirm. The API task is submitted against the current non-default, non-backup branch, with pull-request creation disabled. Starting a task may consume Copilot AI credits or other metered usage under your organization’s billing configuration. GitHub documents the tasks API as public preview and subject to change.

Each task receives the saved agent-session instructions, director handoff data, and a live local preflight/checkpoint snapshot captured when the task is submitted. The current integration is intentionally limited to read-only repository inspection and non-paid planning: no file edits, commits, pull requests, paid provider calls, media generation, downloads, budget reservations, or rendering are authorized. It records the task ID locally and lets you refresh the task state. Missing local project checkpoints are reported as missing rather than invented. The existing **Copy agent session prompt** action remains available as a manual fallback in Copilot Chat.

GitHub API reference: https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/use-cloud-agent-via-the-api

## Safety boundary

Creating a production project only scaffolds its folder and initial metadata. Checking the Copilot connection does not launch an agent. Starting a confirmed local or cloud agent task uses GitHub Copilot and may consume plan usage, but the task is explicitly limited to read-only inspection and non-paid planning. It does **not** authorize media generation, paid provider calls, downloads, budget reservations, or rendering. The budget cap is planning metadata, not a price quote.

The browser workspace currently stores its creative notes in local storage on that device. The API also exposes a validated `PUT` endpoint for server-side script, scene, character, and shot data; full browser-to-project synchronization is still in progress. Backlot remains the read-only production monitor.


For GitHub Copilot Chat in Codespaces, the repository also provides the `/film-studio-agent` prompt in `.github/prompts/film-studio-agent.prompt.md`. After preparing a handoff, invoke that prompt and provide the project ID if it is not already clear. It reads the saved local project handoff and follows the repository's agent contract; it does not bypass approval gates.
