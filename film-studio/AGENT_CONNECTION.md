# Film Studio agent connection

Film Studio supports two GitHub Copilot agent hosts. The **local Copilot CLI** is recommended because it is available on all Copilot plans and runs inside the Codespace beside the real project files. The optional **Copilot Cloud Agent API** requires Business or Enterprise.

## Recommended: local Copilot CLI (all plans)

1. Open the repository in a **new Codespace** on `feature/film-studio-director-app`. Keep the existing backup Codespace untouched.
2. Ensure Node.js 22 or later is installed, then install the official CLI:

   ```bash
   npm install -g @github/copilot
   ```

3. Start `copilot` in the repository root. On first use, enter `/login`, complete GitHub sign-in, and approve workspace trust if prompted. Then exit the interactive CLI.
4. Start Film Studio from the repository root:

   ```bash
   python film-studio/server.py
   ```

5. In **Production Engine → Production preflight**, select a project and choose **Prepare director handoff**.
6. Check **Local Copilot CLI**, then choose **Start local read-only agent** and review the confirmation.
7. Use **Refresh local task** to view the result.

The server checks the CLI executable/version without signing in or consuming usage. Authentication and workspace trust are not verified by that check; complete the interactive setup above first. The local process receives the saved agent-session prompt, director handoff, live local preflight report, and canonical checkpoint snapshot. It can also inspect the real Codespace project files.

### Local task safety

The server invokes Copilot CLI in non-interactive prompt mode with `--available-tools=read`, `--deny-tool=shell,write,url,memory`, and `--no-ask-user`. It also disables repository hooks, workspace MCP, and extensions for the prompt run. It removes inherited `COPILOT_ALLOW_ALL` and `COPILOT_ASSISTED_APPROVAL` environment switches and does not use `--allow-all`. The task can read files but cannot run shell commands, modify files, fetch URLs, or write agent memory. Paid provider calls, media generation, downloads, budget reservations, and rendering are not authorized. Starting a task may consume Copilot AI credits or other metered usage under your plan.

Official references: [Install Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/set-up-copilot-cli/install-copilot-cli) and [CLI programmatic reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-programmatic-reference).

## Optional: hosted Copilot Cloud Agent (Business/Enterprise)

1. Ensure the account has GitHub Copilot Business or Enterprise and Cloud Agent is enabled for the repository.
2. Authenticate GitHub CLI (`gh auth status`; if needed, `gh auth login`) or configure `GH_TOKEN` with an eligible user-to-server token. Fine-grained personal access tokens need repository **Agent tasks: read and write** permission to start tasks; read permission is sufficient for status checks. Server-to-server installation tokens are not supported.
3. In Film Studio, check **GitHub Copilot Cloud Agent**, then choose **Start cloud agent task** and confirm.

The API is in public preview. Tasks use the current branch, block the default and `backup/*` branches, and disable pull-request creation. The cloud task receives the embedded director handoff and local preflight/checkpoint snapshot because it cannot access the Codespace filesystem. It is restricted by its prompt to read-only repository inspection and non-paid planning.

Official API reference: https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/use-cloud-agent-via-the-api

## Manual fallback

If neither agent host is available, prepare the director handoff, copy the agent-session prompt, open Copilot Chat in the Codespace, and invoke `/film-studio-agent` if repository prompt files are supported. Otherwise paste the saved `projects/<project_id>/artifacts/agent_session.md` into a compatible coding-agent session.
