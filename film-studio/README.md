# OpenMontage Film Studio

A mobile-first director workspace and installable progressive web app.

## Working in v0.2

- Create and manage film projects.
- Store a logline, genre, script title, and script/story notes.
- Add and describe scenes.
- Build a character bible with role, visual identity, personality, and continuity rules.
- Plan shots with scene reference, framing, camera movement, and visual intent.
- Export one film or the complete library as JSON; import backups without overwriting existing projects.
- Save planning data in browser local storage.
- Responsive phone and desktop layouts; offline app shell after first load.

## Run locally

From the repository root:

```bash
python -m http.server 4173 --directory film-studio
```

Open `http://localhost:4173`.

## Integration status

This is a director-facing planning app, not yet an AI generation service. Script assistance, image/video/audio generation, automated production execution, rendering, provider credentials, and cost controls are not wired to production APIs in this version. The existing Backlot dashboard remains a read-only production monitor. The next integration phase must connect through explicit, validated backend endpoints and approval gates. No provider calls or charges are made by this app.

Project data stays in browser local storage on the device where it was created until exported. Use the backup tools before clearing browser data or changing devices.
