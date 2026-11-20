# Film Studio development

The first director-facing app lives in `film-studio/` as a standalone, mobile-first PWA.

## Milestone 1 — director workspace

- [x] Create a safe feature branch separate from `main`.
- [x] Add responsive dashboard and navigation.
- [x] Add local film project creation.
- [x] Add script/story notes editor with local persistence.
- [x] Add scene board, character continuity notes, and shot planning.
- [x] Add installable/offline app shell.
- [x] Add project export/import backups.
- [x] Add a local API for real project scaffolding and Film Studio planning-data persistence.
- [ ] Run browser and mobile QA in the user's Codespace.

## Milestone 2 — OpenMontage integration

- [x] Read the real Backlot project library and create canonical OpenMontage project folders.
- [x] Persist Film Studio script, scene, character, and shot planning data in the project's `artifacts/film_studio.json`.
- [x] Inspect actual pipeline manifests, checkpoint artifacts, stage order, and approval evidence in Production Preflight.
- [x] Discover locally configured providers and composition runtimes through the existing tool registry without executing providers.
- [x] Display recorded project costs and the project's planning budget cap.
- [x] Require a bearer token before remote API access; keep the default server loopback-only.
- [ ] Add itemized cost estimates and explicit approval UI before any paid operation.
- [ ] Map Film Studio screenplay/storyboard data into schema-valid OpenMontage stage artifacts.
- [ ] Connect the director workspace to the agent-driven stage workflow and Remotion rendering.

## Milestone 3 — agent-driven production

OpenMontage is instruction-driven: the AI agent is the orchestrator. Python owns tools, validated persistence, checkpoints, and budget governance; it must not become a second creative/orchestration engine. The next integration must hand an approved director brief to that agent workflow, follow the pipeline manifest and stage-director skills, and preserve checkpoint and cost controls. Do not create a generic Python runner that bypasses `AGENT_GUIDE.md`.

## Safety

Do not alter the user's existing Codespace or uncommitted work. Keep development isolated on `feature/film-studio-director-app` until reviewed. Never trigger paid AI provider requests without the director's explicit approval.
