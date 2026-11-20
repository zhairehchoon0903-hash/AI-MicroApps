# Film Studio development

The first director-facing app lives in `film-studio/` as a standalone, mobile-first PWA.

## Milestone 1 — director workspace

- [x] Create a safe feature branch separate from `main`.
- [x] Add responsive dashboard and navigation.
- [x] Add local film project creation.
- [x] Add script/story notes editor with local persistence.
- [x] Add scene board with add/remove and notes.
- [x] Add installable/offline app shell.
- [ ] Run browser and mobile QA in the user's Codespace.
- [ ] Add project export/import and server-side persistence.

## Milestone 2 — OpenMontage integration

- [ ] Define authenticated project CRUD endpoints.
- [ ] Connect the UI to Backlot project state without bypassing existing safeguards.
- [ ] Add explicit approval gates for provider calls, generation, and rendering.
- [ ] Add provider configuration and cost estimates before any paid operation.
- [ ] Connect script, storyboard, asset generation, and Remotion render workflows.

## Safety

Do not alter the user's existing Codespace or uncommitted work. Keep development isolated on `feature/film-studio-director-app` until reviewed. Never trigger paid AI provider requests without the director's explicit approval.
