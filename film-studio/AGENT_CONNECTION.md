# Film Studio agent connection

Film Studio now supports the official GitHub Copilot Cloud Agent tasks API, in addition to the manual Codespaces Copilot Chat prompt.

## Hosted agent connection

1. Open the repository in a **new Codespace** on `feature/film-studio-director-app`. Keep the existing backup Codespace untouched.
2. In the Codespace terminal, check GitHub CLI authentication with `gh auth status`. If needed, sign in using `gh auth login`.
3. Start Film Studio from the repository root:

   ```bash
   python film-studio/server.py
   ```

4. Open the Production Engine, select the film project, and choose **Prepare director handoff**.
5. Check the **GitHub Copilot Cloud Agent** connection. This is a read-only capability check; it does not start a task.
6. Choose **Start cloud agent task** and review the confirmation. The task is submitted only after you confirm.
7. Use **Refresh task status** to check progress.

The server reads a user-authenticated token from `gh auth token` in memory. Alternatively, `GH_TOKEN` may be configured with a user-to-server token. The token is never returned to the browser or saved in project artifacts. GitHub's agent tasks API does not accept server-to-server installation tokens.

## Eligibility and usage

- Requires GitHub Copilot Business or Enterprise and Copilot Cloud Agent enabled for the repository. For fine-grained personal access tokens, grant repository **Agent tasks: read and write** to start tasks; read permission is sufficient for status checks.
- The Cloud Agent tasks API is in public preview and may change.
- Starting a task may consume Copilot AI credits or other metered usage under your organization's billing configuration.
- Tasks are based on the current Git branch. The app blocks the repository's default branch and `backup/*` branches; use the dedicated feature-branch Codespace.
- Task creation disables pull-request creation.

## Current safety scope

The task receives the saved `agent_session.md` instructions and the director handoff JSON. It is explicitly limited to read-only repository inspection and non-paid planning. It must not edit or delete files, commit, open a pull request, run production stages, call paid providers, generate or download media, reserve budget, or render. If local project checkpoints are not present in the GitHub repository, it must report that limitation rather than inventing state.

The Film Studio records the returned task ID in `projects/<project_id>/artifacts/cloud_agent_task.json`. Task status can be refreshed through the app. Connection checks do not start tasks, and the start endpoint requires explicit director confirmation.

## Manual fallback

If Cloud Agent is not enabled for the account or repository, prepare the director handoff, copy the agent-session prompt, open Copilot Chat in the Codespace, and invoke `/film-studio-agent` if repository prompt files are supported. Otherwise paste the saved `projects/<project_id>/artifacts/agent_session.md` into a compatible coding-agent session.

## Official API documentation

https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/use-cloud-agent-via-the-api
