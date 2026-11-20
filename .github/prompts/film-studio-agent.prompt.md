# /film-studio-agent — continue a prepared OpenMontage production

Use this prompt when the director has prepared a Film Studio handoff in a local Codespace.

1. Read `AGENTS.md` and `AGENT_GUIDE.md` first. Their instructions are mandatory.
2. Identify the active project ID from the user's request or current conversation. If it is not unambiguous, ask for the project ID; do not guess.
3. Read:
   - `projects/<project_id>/artifacts/agent_session.md`
   - `projects/<project_id>/artifacts/director_handoff.json`
   - `projects/<project_id>/artifacts/film_studio.json`
4. Follow the exact pipeline manifest and skill paths named by the handoff. Before work in a stage, read that stage's director skill. Use the existing checkpoint utilities and reviewer skill. The AI agent is the orchestrator; Python remains tools and persistence only.
5. Begin with read-only inspection of project metadata, current checkpoints, provider readiness, and budget. Report the next valid stage and any missing prerequisites.
6. The handoff permits read-only inspection and non-paid planning only. Do not call paid providers, generate images/video/audio, download media, reserve spend, or render unless the director separately approves the specific plan.
7. Stop at every manifest-required human approval gate and wait for the director's response. Never silently change provider, model, renderer, or creative direction.

If the local project files are unavailable, explain that the project lives in the Codespace filesystem and ask the director to open the correct Codespace/branch. Do not fabricate project state or claim that the Film Studio launched an agent process.
