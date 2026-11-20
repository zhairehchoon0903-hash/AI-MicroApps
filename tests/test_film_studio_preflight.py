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
