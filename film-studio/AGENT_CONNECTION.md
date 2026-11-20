# Connecting the Film Studio to an AI Agent

## Current connection status

The Film Studio can create a director handoff and an agent-session prompt, but it does not currently host or launch an agent process. The repository's agent instructions and tools are designed to be run by a compatible coding-agent host.

## Use GitHub Copilot Chat in Codespaces

1. Open this repository on the `feature/film-studio-director-app` branch in a **new Codespace**. Keep any existing backup Codespace on its backup branch untouched.
2. Start the Film Studio service from the repository root:

   ```bash
   python film-studio/server.py
   ```

3. Open the Film Studio in that Codespace and connect to its local engine.
4. In **Production Engine → Production preflight**, select the film project and choose **Prepare director handoff**.
5. Choose **Copy agent session prompt**.
6. Open GitHub Copilot Chat in the same Codespace. If your Copilot Chat version supports repository prompt files, invoke:

   ```text
   /film-studio-agent
   ```

7. Paste the copied project-specific agent-session prompt when needed. The agent should read the project's handoff files, inspect the real pipeline and checkpoints, and report the next safe step.

## Important limitations and safeguards

- The slash command depends on GitHub Copilot Chat supporting repository prompt files. If it is unavailable, paste the saved `projects/<project_id>/artifacts/agent_session.md` instructions into a compatible coding-agent session.
- The Film Studio handoff endpoint only writes planning artifacts. It does not start Copilot, create a remote agent session, or execute a production stage.
- The initial agent work is read-only inspection and non-paid planning.
- Paid provider calls, media generation, downloads, budget reservations, and rendering require separate explicit director approval and a real implementation of those operations.
- Follow the selected pipeline manifest, stage-director skills, checkpoint protocol, and human approval gates. Never bypass them.
- Do not expose the development server to the public internet. For remote access, use a trusted private network and the documented bearer-token protection.
