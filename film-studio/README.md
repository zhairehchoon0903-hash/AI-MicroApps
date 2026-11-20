# OpenMontage Film Studio

A mobile-first director workspace with a local API bridge to the repository's real OpenMontage pipeline catalog and project library.

## Run the connected Film Studio

From the repository root:

```bash
python film-studio/server.py
```

Open **http://127.0.0.1:4173** on the same computer. To access it from a phone on the same trusted Wi-Fi network, start it with:

```bash
FILM_STUDIO_HOST=0.0.0.0 python film-studio/server.py
```

Then open `http://YOUR-COMPUTER-LAN-IP:4173` on the phone. This is a development server with no user authentication; use it only on a trusted private network and never expose it directly to the public internet.

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

Open the Production Engine, choose a project in **Production preflight**, and select **Inspect readiness**. The API reads the project's validated pipeline manifest and checks the actual `artifacts/<name>.json` prerequisites for every stage. It reports missing inputs, declared tool requirements, director-approval gates, review focus, and any recorded `cost_log.json` totals. This is an inspection only: it does not invoke agents, reserve budget, call providers, download assets, generate media, or render. The response always reports `execution_authorized: false`.

The endpoint is `GET /api/projects/{project_id}/preflight`.

## Safety boundary

Creating a production project only scaffolds its folder and initial metadata. It does **not** launch an agent, call an AI provider, generate images/video/audio, download media, or render. The budget cap planning metadata, not a price quote. Generation and rendering require separate implementation, provider configuration, explicit director approval, and cost controls.

The browser workspace currently stores its creative notes in local storage on that device. The API also exposes a validated `PUT` endpoint for server-side script, scene, character, and shot data; full browser-to-project synchronization is still in progress. Backlot remains the read-only production monitor.

