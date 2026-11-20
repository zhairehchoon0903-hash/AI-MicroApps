# OpenMontage Film Studio

A mobile-first director workspace with a local API bridge to the repository's real OpenMontage pipeline catalog and project library.

## Run the connected Film Studio

From the repository root:

```bash
python film-studio/server.py
```

Open **http://127.0.0.1:4173** on the same computer. To access it from a phone on the same Wi-Fi, run with a LAN host binding by changing the host in `server.py` to `0.0.0.0`, then use the computer's LAN IP and port 4173. Do not expose this development server directly to the public internet.

## Working features

- Create and manage local browser projects while offline.
- Connect to the local OpenMontage API to read the actual validated pipeline manifests and production library.
- Create real `projects/<slug>/` folders with `project.json`, `meta.json`, artifact storage, asset folders, and render folders. These are visible to Backlot.
- Choose from actual pipeline definitions; view each pipeline's declared stages and human-approval gates.
- Set a planning budget cap in the project brief.
- Script notes, scene planning, character continuity bible, and shot planning.
- Export one film or the complete local library as JSON; import backups without overwriting existing projects.
- Responsive phone and desktop layouts.

## Safety boundary

Creating a production project only scaffolds its folder and initial metadata. It does **not** launch an agent, call an AI provider, generate images/video/audio, download media, or render. The budget cap is planning metadata, not a price quote. Generation and rendering require separate implementation, provider configuration, explicit director approval, and cost controls.

Project data entered in the browser's existing planning workspace is stored in local storage on that device. The API exposes a separate `PUT /api/projects/{project_id}/studio` endpoint for validated server-side project notes; browser-to-API synchronization is the next integration step. Backlot remains the read-only production monitor.
