# OpenMontage Film Studio

A mobile-first director workspace and installable progressive web app.

## Current capabilities

- Create and manage film projects.
- Store a logline, genre, script title, and script/story notes.
- Add, describe, and remove scenes.
- See project and scene counts on the overview.
- Save planning data in browser local storage.
- Responsive phone and desktop layouts; offline app shell after first load.

## Open locally

From the repository root, serve this directory over HTTP, for example:

```bash
python -m http.server 4173 --directory film-studio
```

Then open `http://localhost:4173`.

## Important integration status

This is the first working director-facing workspace, not yet an AI generation service. Script assistance, image/video/audio generation, automated production execution, rendering, provider credentials, and cost controls are not wired to production APIs in this version. The existing Backlot dashboard remains the read-only production monitor. The next integration phase must connect these controls through explicit, validated backend endpoints and approval gates. No provider calls or charges are made by this app.

Project data currently stays in the browser on the device where it was created. Export/import and server-side project persistence are follow-up work.
