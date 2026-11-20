from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SERVER_PATH = ROOT / "film-studio" / "server.py"


@pytest.fixture
def film_server(monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location("film_studio_server_test", SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    project_id = "preflight-test"
    project_dir = tmp_path / project_id
    artifacts_dir = project_dir / "artifacts"
    artifacts_dir.mkdir(parents=True)
    (project_dir / "project.json").write_text(json.dumps({
        "project_id": project_id,
        "title": "Preflight Test",
        "pipeline_type": "cinematic",
        "film_studio": {"budget_cap_usd": 4.0},
    }), encoding="utf-8")
    (artifacts_dir / "film_studio.json").write_text(json.dumps({
        "script": "A saved screenplay", "scenes": [{}], "characters": [], "shots": []
    }), encoding="utf-8")

    manifest = {
        "name": "cinematic", "version": "2.0", "stability": "production",
        "orchestration": {"budget_default_usd": 2.0},
        "stages": [
            {"name": "research", "produces": ["research_brief"], "checkpoint_required": True},
            {"name": "proposal", "required_artifacts_in": ["research_brief"],
             "produces": ["proposal_packet"], "checkpoint_required": True,
             "human_approval_default": True, "review_focus": ["Approve the creative direction"]},
            {"name": "script", "required_artifacts_in": ["proposal_packet"],
             "produces": ["script"], "checkpoint_required": True,
             "human_approval_default": True},
        ],
    }
    checkpoints = {
        "research": {"project_id": project_id, "pipeline_type": "cinematic", "stage": "research",
                     "status": "completed", "human_approved": False,
                     "artifacts": {"research_brief": {"summary": "Research"}}},
        "proposal": {"project_id": project_id, "pipeline_type": "cinematic", "stage": "proposal",
                     "status": "awaiting_human", "human_approved": False,
                     "artifacts": {"proposal_packet": {"title": "Film direction"}}},
    }
    monkeypatch.setattr(module, "PROJECTS_DIR", tmp_path)
    monkeypatch.setattr(module, "_project_dir", lambda _project_id: project_dir)
    monkeypatch.setattr(module, "load_pipeline", lambda _name: manifest)
    from lib import checkpoint as checkpoint_module
    monkeypatch.setattr(checkpoint_module, "read_checkpoint", lambda _root, _id, stage: checkpoints.get(stage))
    return module, checkpoints


def test_preflight_reads_checkpoint_artifacts_and_halts_at_approval(film_server):
    module, _checkpoints = film_server
    result = module.project_preflight("preflight-test")

    assert result["summary"]["completed_stages"] == 1
    assert result["summary"]["pending_director_approvals"] == 1
    assert result["next_stage"] == "proposal"
    assert result["stages"][1]["status"] == "awaiting_director_approval"
    assert result["stages"][2]["missing_artifacts"] == ["proposal_packet"]
    assert result["execution_authorized"] is False
    assert result["generation_enabled"] is False


def test_preflight_unlocks_next_stage_only_after_approval_evidence(film_server):
    module, checkpoints = film_server
    checkpoints["proposal"]["status"] = "completed"
    checkpoints["proposal"]["human_approved"] = True

    result = module.project_preflight("preflight-test")

    assert result["next_stage"] == "script"
    assert result["stages"][1]["status"] == "completed"
    assert result["stages"][2]["present_artifacts"] == ["proposal_packet"]
    assert result["stages"][2]["status"] == "ready_for_stage"
    assert result["execution_authorized"] is False


def test_capability_report_is_registry_summary_only(monkeypatch, film_server):
    module, _checkpoints = film_server
    from tools import tool_registry
    monkeypatch.setattr(tool_registry.registry, "provider_menu_summary", lambda: {
        "capabilities": [{"capability": "image_generation", "configured": 1, "total": 3,
                          "available_providers": ["local-test"], "unavailable_providers": ["remote-a", "remote-b"]}],
        "composition_runtimes": {"remotion": True},
        "setup_offers": [],
        "runtime_warnings": [],
    })

    result = module.capabilities()

    assert result["capabilities"][0]["configured"] == 1
    assert result["composition_runtimes"]["remotion"] is True
    assert result["paid_calls_started"] is False
    assert result["generation_enabled"] is False


def test_api_requires_bearer_token_when_configured(monkeypatch, film_server):
    from fastapi.testclient import TestClient
    module, _checkpoints = film_server
    monkeypatch.setattr(module, "API_TOKEN", "test-director-token")
    monkeypatch.setattr(module, "list_pipelines", lambda: [])
    client = TestClient(module.app)

    assert client.get("/api/pipelines").status_code == 401
    response = client.get("/api/pipelines", headers={"Authorization": "Bearer test-director-token"})
    assert response.status_code == 200



def test_director_handoff_packages_planning_without_authorizing_execution(film_server, tmp_path):
    module, _checkpoints = film_server
    result = module.create_director_handoff("preflight-test")
    handoff = result["handoff"]

    assert result["saved"] is True
    assert result["artifact_path"] == "artifacts/director_handoff.json"
    assert handoff["artifact_type"] == "director_handoff"
    assert handoff["canonical_pipeline_artifact"] is False
    assert handoff["director_intent"]["script"] == "A saved screenplay"
    assert handoff["production_contract"]["stages"][1]["human_approval_required"] is True
    assert all(value is False for key, value in handoff["authorization"].items() if key.endswith("_authorized"))
    saved = json.loads((tmp_path / "preflight-test" / "artifacts" / "director_handoff.json").read_text())
    assert saved["project"]["pipeline_id"] == "cinematic"



def test_director_handoff_creates_agent_session_prompt_with_real_skill_paths(film_server, tmp_path):
    module, _checkpoints = film_server
    result = module.create_director_handoff("preflight-test")
    handoff = result["handoff"]
    prompt = result["agent_prompt"]

    assert result["agent_prompt_path"] == "artifacts/agent_session.md"
    assert "skills/pipelines/cinematic/proposal-director.md" in prompt
    assert "AGENT_GUIDE.md" in prompt
    assert "Paid operations: NOT authorized" in prompt
    assert handoff["production_contract"]["stages"][1]["director_skill"] == "skills/pipelines/cinematic/proposal-director.md"
    saved_prompt = (tmp_path / "preflight-test" / "artifacts" / "agent_session.md").read_text()
    assert saved_prompt == prompt + "\n"



def test_cloud_agent_task_requires_explicit_director_confirmation(film_server, tmp_path):
    from fastapi.testclient import TestClient

    module, _checkpoints = film_server
    client = TestClient(module.app)
    response = client.post("/api/projects/preflight-test/agent-task", json={})

    assert response.status_code == 400
    assert "Explicit director confirmation" in response.json()["detail"]


def test_cloud_agent_connection_check_never_starts_a_task(film_server, monkeypatch):
    from fastapi.testclient import TestClient

    module, _checkpoints = film_server
    monkeypatch.setattr(module, "_agent_connection", lambda: ({
        "connected": True, "can_start": True, "repository": "owner/repo",
        "base_ref": "feature/test", "note": "Connection check only."
    }, "test-user-token"))
    client = TestClient(module.app)
    response = client.get("/api/agent/connection")

    assert response.status_code == 200
    assert response.json()["connected"] is True
    assert "token" not in json.dumps(response.json()).lower()


def test_cloud_agent_start_embeds_handoff_and_never_authorizes_paid_media(film_server, monkeypatch, tmp_path):
    from fastapi.testclient import TestClient

    module, _checkpoints = film_server
    module.create_director_handoff("preflight-test")
    monkeypatch.setattr(module, "_agent_connection", lambda: ({
        "connected": True, "can_start": True, "repository": "owner/repo",
        "base_ref": "feature/test", "default_branch": "main"
    }, "test-user-token"))
    captured = {}

    def fake_github_request(method, path, token, payload=None):
        captured.update({"method": method, "path": path, "token": token, "payload": payload})
        return {"id": "task-123", "state": "queued"}

    monkeypatch.setattr(module, "_github_api_request", fake_github_request)
    monkeypatch.setattr(module, "_agent_repository_context", lambda: {
        "owner": "owner", "repo": "repo", "base_ref": "feature/test"
    })
    client = TestClient(module.app)
    response = client.post("/api/projects/preflight-test/agent-task", json={"confirm_start": True})

    assert response.status_code == 200
    assert response.json()["started"] is True
    assert captured["method"] == "POST"
    assert captured["path"] == "/agents/repos/owner/repo/tasks"
    assert captured["payload"]["base_ref"] == "feature/test"
    assert captured["payload"]["create_pull_request"] is False
    assert "A saved screenplay" in captured["payload"]["prompt"]
    assert "Local Film Studio preflight report" in captured["payload"]["prompt"]
    assert "Canonical checkpoint snapshot" in captured["payload"]["prompt"]
    assert "Film direction" in captured["payload"]["prompt"]
    assert "Do not call paid AI providers" in captured["payload"]["prompt"]
    assert response.json()["task"]["paid_media_operations_authorized"] is False
    assert response.json()["task"]["generation_authorized"] is False
    saved = json.loads((tmp_path / "preflight-test" / "artifacts" / "cloud_agent_task.json").read_text())
    assert saved["task_id"] == "task-123"
    assert "test-user-token" not in json.dumps(saved)



def test_local_copilot_connection_check_does_not_start_a_task(film_server, monkeypatch):
    from fastapi.testclient import TestClient

    module, _checkpoints = film_server
    monkeypatch.setattr(module, "_local_copilot_status", lambda: ({
        "installed": True, "can_start": True, "provider": "GitHub Copilot CLI",
        "version": "copilot 1.0", "note": "Connection check only."
    }, "/usr/bin/copilot"))
    client = TestClient(module.app)
    response = client.get("/api/agent/local-connection")

    assert response.status_code == 200
    assert response.json()["installed"] is True
    assert response.json()["note"] == "Connection check only."


def test_local_agent_start_requires_explicit_director_confirmation(film_server):
    from fastapi.testclient import TestClient

    module, _checkpoints = film_server
    client = TestClient(module.app)
    response = client.post("/api/projects/preflight-test/local-agent-task", json={})

    assert response.status_code == 400
    assert "Explicit director confirmation" in response.json()["detail"]


def test_local_agent_uses_read_only_copilot_tools_and_records_output(film_server, monkeypatch, tmp_path):
    from fastapi.testclient import TestClient

    module, _checkpoints = film_server
    module.create_director_handoff("preflight-test")
    monkeypatch.setattr(module, "_local_copilot_status", lambda: ({
        "installed": True, "can_start": True, "provider": "GitHub Copilot CLI"
    }, "/usr/bin/copilot"))
    monkeypatch.setattr(module, "_build_agent_prompt", lambda _id, _handoff, _session, host: "read-only planning prompt" if host == "local" else "wrong host")
    monkeypatch.setenv("COPILOT_ALLOW_ALL", "true")
    captured = {}

    class FakeInput:
        def __init__(self):
            self.value = ""
            self.closed = False
        def write(self, value):
            self.value += value
        def close(self):
            self.closed = True

    class FakeProcess:
        pid = 45678
        def __init__(self):
            self.stdin = FakeInput()
        def poll(self):
            return 0

    fake_process = FakeProcess()

    def fake_popen(command, **kwargs):
        captured["command"] = command
        captured["environment"] = kwargs["env"]
        captured["stdin"] = kwargs["stdin"]
        kwargs["stdout"].write("Checkpoint audit complete. No files changed.\n")
        kwargs["stdout"].flush()
        return fake_process

    monkeypatch.setattr(module.subprocess, "Popen", fake_popen)
    client = TestClient(module.app)
    response = client.post("/api/projects/preflight-test/local-agent-task", json={"confirm_start": True})

    assert response.status_code == 200
    assert response.json()["started"] is True
    assert "--available-tools=read" in captured["command"]
    assert "--deny-tool=shell,write,url,memory" in captured["command"]
    assert "-p" not in captured["command"]
    assert fake_process.stdin.value == "read-only planning prompt"
    assert fake_process.stdin.closed is True
    assert captured["stdin"] == module.subprocess.PIPE
    assert "--no-ask-user" in captured["command"]
    assert "--allow-all" not in captured["command"]
    assert "COPILOT_ALLOW_ALL" not in captured["environment"]
    assert captured["environment"]["GITHUB_COPILOT_PROMPT_MODE_REPO_HOOKS"] == "false"
    assert captured["environment"]["GITHUB_COPILOT_PROMPT_MODE_WORKSPACE_MCP"] == "false"
    assert response.json()["task"]["render_authorized"] is False

    status = client.get("/api/projects/preflight-test/local-agent-task")
    assert status.status_code == 200
    assert status.json()["task"]["state"] == "completed"
    assert "Checkpoint audit complete" in status.json()["output"]
