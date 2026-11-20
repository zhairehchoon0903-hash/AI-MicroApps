"""Local Film Studio API for OpenMontage.

This service exposes validated pipeline metadata and safe project scaffolding.
It deliberately does not invoke agents, generation providers, or render jobs.
"""
from __future__ import annotations

import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from backlot.state import PROJECTS_DIR, list_projects, load_board_state
from lib.pipeline_loader import list_pipelines, load_pipeline

app = FastAPI(title="OpenMontage Film Studio API", version="0.1.0")
PROJECT_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=90)
    genre: str = Field(default="Fantasy", max_length=40)
    logline: str = Field(default="", max_length=2000)
    pipeline_type: str = Field(default="cinematic", min_length=1, max_length=64)
    budget_cap_usd: float = Field(default=2.0, ge=0, le=5000)


class StudioSave(BaseModel):
    data: dict[str, Any]


def _project_dir(project_id: str) -> Path:
    if not PROJECT_ID.fullmatch(project_id):
        raise HTTPException(status_code=400, detail="Invalid project id.")
    root = PROJECTS_DIR.resolve()
    target = (root / project_id).resolve()
    if target.parent != root:
        raise HTTPException(status_code=400, detail="Invalid project path.")
    if not target.is_dir():
        raise HTTPException(status_code=404, detail="Project not found.")
    return target


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


@app.get("/api/health")
def health() -> dict:
    return {
        "ok": True,
        "service": "OpenMontage Film Studio",
        "version": app.version,
        "projects_dir": str(PROJECTS_DIR),
        "generation_enabled": False,
        "note": "Planning and project scaffolding only. No provider calls or render jobs are started.",
    }


@app.get("/api/pipelines")
def pipelines() -> dict:
    result = []
    for name in sorted(list_pipelines()):
        try:
            manifest = load_pipeline(name)
        except Exception:
            continue
        orchestration = manifest.get("orchestration") or {}
        stages = []
        for stage in manifest.get("stages", []):
            if not isinstance(stage, dict) or not stage.get("name"):
                continue
            stages.append({
                "name": stage["name"],
                "approval_required": bool(stage.get("human_approval_default", False)),
                "checkpoint_required": bool(stage.get("checkpoint_required", False)),
                "produces": stage.get("produces", []),
            })
        result.append({
            "id": name,
            "name": manifest.get("name", name),
            "description": manifest.get("description", ""),
            "category": manifest.get("category", "general"),
            "stability": manifest.get("stability", "unknown"),
            "default_checkpoint_policy": manifest.get("default_checkpoint_policy", "guided"),
            "budget_default_usd": float(orchestration.get("budget_default_usd", 0) or 0),
            "stages": stages,
        })
    return {"pipelines": result}


@app.get("/api/projects")
def projects() -> dict:
    return {"projects": list_projects()}


@app.post("/api/projects", status_code=201)
def create_project(payload: ProjectCreate) -> dict:
    try:
        load_pipeline(payload.pipeline_type)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Unknown or invalid pipeline: {payload.pipeline_type}") from exc

    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="Project title cannot be blank.")
    base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:48] or "film"

    # Claim a unique directory atomically. Never clean up a directory unless
    # this request successfully created it; a collision must preserve its owner.
    project_dir: Path | None = None
    project_id = ""
    for attempt in range(6):
        suffix = "" if attempt == 0 else f"-{uuid.uuid4().hex[:6]}"
        candidate_id = f"{base}{suffix}"
        candidate_dir = PROJECTS_DIR / candidate_id
        try:
            candidate_dir.mkdir(parents=True, exist_ok=False)
            project_id, project_dir = candidate_id, candidate_dir
            break
        except FileExistsError:
            continue
    if project_dir is None:
        raise HTTPException(status_code=409, detail="Could not reserve a unique project folder. Please try again.")

    try:
        for folder in ("artifacts", "assets/images", "assets/video", "assets/audio", "renders", "history"):
            (project_dir / folder).mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc).isoformat()
        marker = {
            "project_id": project_id,
            "title": title,
            "pipeline_type": payload.pipeline_type,
            "created_at": now,
            "style_playbook": None,
            "series": None,
            "film_studio": {
                "genre": payload.genre,
                "logline": payload.logline.strip(),
                "budget_cap_usd": payload.budget_cap_usd,
                "production_status": "planning",
                "generation_authorized": False,
            },
        }
        _atomic_json(project_dir / "project.json", marker)
        _atomic_json(project_dir / "meta.json", {"name": title, "created_at": now})
        _atomic_json(project_dir / "artifacts" / "film_studio.json", {
            "version": 1,
            "project_id": project_id,
            "title": title,
            "genre": payload.genre,
            "logline": payload.logline.strip(),
            "pipeline_type": payload.pipeline_type,
            "budget_cap_usd": payload.budget_cap_usd,
            "script_title": "",
            "script": "",
            "scenes": [],
            "characters": [],
            "shots": [],
            "created_at": now,
            "updated_at": now,
        })
    except Exception:
        import shutil
        shutil.rmtree(project_dir, ignore_errors=True)
        raise

    selected = next((p for p in pipelines()["pipelines"] if p["id"] == payload.pipeline_type), None)
    return {
        "project": {
            "project_id": project_id,
            "title": title,
            "pipeline_type": payload.pipeline_type,
            "genre": payload.genre,
            "logline": payload.logline.strip(),
            "budget_cap_usd": payload.budget_cap_usd,
            "production_status": "planning",
            "generation_authorized": False,
            "stages": [
                {"name": stage["name"], "status": "pending", "approval_required": stage["approval_required"]}
                for stage in (selected or {}).get("stages", [])
            ],
        },
        "message": "Project folder created. No AI generation or rendering was started.",
    }


@app.get("/api/projects/{project_id}/preflight")
def project_preflight(project_id: str) -> dict:
    """Inspect real pipeline prerequisites without executing any production work."""
    folder = _project_dir(project_id)
    project_path = folder / "project.json"
    if not project_path.is_file():
        raise HTTPException(status_code=409, detail="Project metadata is missing.")
    project = json.loads(project_path.read_text(encoding="utf-8"))
    pipeline_type = project.get("pipeline_type")
    try:
        manifest = load_pipeline(pipeline_type)
    except Exception as exc:
        raise HTTPException(status_code=409, detail="The project's pipeline manifest is unavailable or invalid.") from exc

    artifacts_dir = folder / "artifacts"
    stages = manifest.get("stages", [])
    producer_by_artifact = {
        artifact: stage.get("name")
        for stage in stages
        for artifact in (stage.get("produces", []) or [])
    }
    # The canonical OpenMontage record is checkpoint_<stage>.json at the
    # project root. Artifact payloads live inside checkpoint["artifacts"],
    # not as artifacts/<name>.json files. Use the repository reader so the
    # same schema and identity validation used by the pipeline is applied.
    from lib.checkpoint import read_checkpoint

    checkpoint_by_stage: dict[str, dict[str, Any] | None] = {}
    for stage in stages:
        stage_name = stage.get("name")
        try:
            checkpoint = read_checkpoint(PROJECTS_DIR, project_id, stage_name)
        except Exception:
            checkpoint = None
        if checkpoint and (
            checkpoint.get("project_id") != project_id
            or checkpoint.get("pipeline_type") != pipeline_type
            or checkpoint.get("stage") != stage_name
        ):
            checkpoint = None
        checkpoint_by_stage[stage_name] = checkpoint

    stage_results = []
    for index, stage in enumerate(stages, start=1):
        stage_name = stage.get("name", f"stage-{index}")
        required = stage.get("required_artifacts_in", []) or []
        optional = stage.get("optional_artifacts_in", []) or []
        present: list[str] = []
        missing: list[str] = []
        optional_present: list[str] = []
        optional_missing: list[str] = []
        for artifact_name in required:
            producer = producer_by_artifact.get(artifact_name)
            producer_checkpoint = checkpoint_by_stage.get(producer) if producer else None
            payload = (producer_checkpoint or {}).get("artifacts", {})
            artifact_ready = bool(
                producer_checkpoint
                and producer_checkpoint.get("status") == "completed"
                and isinstance(payload, dict)
                and artifact_name in payload
            )
            if artifact_ready and producer and bool(next((s.get("human_approval_default", False) for s in stages if s.get("name") == producer), False)):
                artifact_ready = bool(producer_checkpoint.get("human_approved"))
            # Some inputs (for example source_media_review) can be supplied
            # directly as standalone project artifacts instead of stage output.
            if not artifact_ready and (artifacts_dir / f"{artifact_name}.json").is_file():
                artifact_ready = True
            (present if artifact_ready else missing).append(artifact_name)
        for artifact_name in optional:
            producer = producer_by_artifact.get(artifact_name)
            producer_checkpoint = checkpoint_by_stage.get(producer) if producer else None
            payload = (producer_checkpoint or {}).get("artifacts", {})
            artifact_ready = bool(
                producer_checkpoint
                and producer_checkpoint.get("status") == "completed"
                and isinstance(payload, dict)
                and artifact_name in payload
            )
            if not artifact_ready and (artifacts_dir / f"{artifact_name}.json").is_file():
                artifact_ready = True
            (optional_present if artifact_ready else optional_missing).append(artifact_name)

        tools = sorted(
            set(stage.get("required_tools", []))
            | set(stage.get("optional_tools", []))
            | set(stage.get("preferred_tools", []))
            | set(stage.get("fallback_tools", []))
            | set(stage.get("tools_available", []))
        )
        approval = bool(stage.get("human_approval_default", False))
        checkpoint = checkpoint_by_stage.get(stage_name)
        checkpoint_status = checkpoint.get("status") if checkpoint else "not_started"
        if checkpoint_status == "awaiting_human":
            status = "awaiting_director_approval"
        elif checkpoint_status == "completed" and approval and not bool(checkpoint.get("human_approved")):
            # Surface legacy or manually-authored checkpoints that predate
            # strict gate enforcement; never silently treat them as approved.
            status = "awaiting_director_approval"
        elif checkpoint_status == "completed":
            status = "completed"
        elif checkpoint_status in {"in_progress", "failed"}:
            status = checkpoint_status
        elif missing:
            status = "missing_prerequisites"
        else:
            status = "ready_for_stage"
        stage_results.append({
            "order": index,
            "name": stage_name,
            "checkpoint_required": bool(stage.get("checkpoint_required", False)),
            "approval_required": approval,
            "human_approved": bool(checkpoint.get("human_approved")) if checkpoint else False,
            "checkpoint_status": checkpoint_status,
            "status": status,
            "required_artifacts": required,
            "present_artifacts": present,
            "missing_artifacts": missing,
            "optional_artifacts": optional,
            "optional_artifacts_present": optional_present,
            "optional_artifacts_missing": optional_missing,
            "produces": stage.get("produces", []),
            "tools": tools,
            "review_focus": stage.get("review_focus", []),
        })

    orchestration = manifest.get("orchestration") or {}
    studio_path = artifacts_dir / "film_studio.json"
    studio = json.loads(studio_path.read_text(encoding="utf-8")) if studio_path.is_file() else {}
    budget_cap = float((project.get("film_studio") or {}).get("budget_cap_usd", orchestration.get("budget_default_usd", 0)) or 0)
    cost_path = folder / "cost_log.json"
    cost = {"recorded": cost_path.is_file(), "spent_usd": 0.0, "reserved_usd": 0.0}
    if cost_path.is_file():
        try:
            raw_cost = json.loads(cost_path.read_text(encoding="utf-8"))
            entries = raw_cost.get("entries", []) if isinstance(raw_cost, dict) else []
            cost["spent_usd"] = round(sum(float(e.get("actual_usd", 0) or 0) for e in entries if e.get("status") in ("completed", "failed")), 4)
            cost["reserved_usd"] = round(sum(float(e.get("reserved_usd", 0) or 0) for e in entries if e.get("status") == "reserved"), 4)
        except (ValueError, TypeError, AttributeError):
            cost["recorded"] = False
            cost["note"] = "Cost log exists but could not be read safely."
    missing_count = sum(len(item["missing_artifacts"]) for item in stage_results)
    approval_count = sum(1 for item in stage_results if item["approval_required"])
    pending_approvals = sum(1 for item in stage_results if item["status"] == "awaiting_director_approval")
    completed_stages = [item["name"] for item in stage_results if item["status"] == "completed"]
    next_stage = next((item["name"] for item in stage_results if item["status"] != "completed"), None)
    return {
        "project_id": project_id,
        "title": project.get("title", project_id),
        "pipeline": {"id": pipeline_type, "name": manifest.get("name", pipeline_type), "version": manifest.get("version"), "stability": manifest.get("stability", "unknown")},
        "production": {"mode": orchestration.get("mode", "manifest-driven"), "max_revisions_per_stage": orchestration.get("max_revisions_per_stage"), "max_send_backs": orchestration.get("max_send_backs"), "max_wall_time_minutes": orchestration.get("max_wall_time_minutes")},
        "budget": {"cap_usd": budget_cap, **cost, "remaining_estimate_usd": round(budget_cap - cost["spent_usd"] - cost["reserved_usd"], 4)},
        "summary": {"stage_count": len(stage_results), "stages_with_missing_artifacts": sum(1 for item in stage_results if item["missing_artifacts"]), "missing_required_artifacts": missing_count, "director_approval_gates": approval_count, "pending_director_approvals": pending_approvals, "completed_stages": len(completed_stages)},
        "next_stage": next_stage,
        "stages": stage_results,
        "saved_studio_data": {"script_present": bool(studio.get("script", "").strip()), "scene_count": len(studio.get("scenes", [])), "character_count": len(studio.get("characters", [])), "shot_count": len(studio.get("shots", []))},
        "generation_enabled": False,
        "execution_authorized": False,
        "message": "Preflight only. No agents, paid tools, downloads, media generation, or renders were started."
    }


@app.get("/api/projects/{project_id}")
def project_detail(project_id: str) -> dict:
    folder = _project_dir(project_id)
    state = load_board_state(folder)
    studio_path = folder / "artifacts" / "film_studio.json"
    studio = json.loads(studio_path.read_text(encoding="utf-8")) if studio_path.is_file() else None
    return {"backlot": state, "studio": studio}


@app.put("/api/projects/{project_id}/studio")
def save_studio(project_id: str, payload: StudioSave) -> dict:
    folder = _project_dir(project_id)
    data = payload.data
    allowed = {"script_title", "script", "scenes", "characters", "shots", "genre", "logline"}
    if set(data) - allowed:
        raise HTTPException(status_code=400, detail="Unsupported project fields.")
    try:
        if len(json.dumps(data, ensure_ascii=False)) > 2_000_000:
            raise HTTPException(status_code=413, detail="Project notes exceed the 2 MB limit.")
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Project data must be JSON serializable.") from exc
    for key in ("scenes", "characters", "shots"):
        if key in data and (not isinstance(data[key], list) or len(data[key]) > 2000):
            raise HTTPException(status_code=422, detail=f"{key} must be a list with at most 2000 entries.")
    for key in ("script", "script_title", "logline"):
        if key in data and (not isinstance(data[key], str) or len(data[key]) > 1_000_000):
            raise HTTPException(status_code=422, detail=f"{key} must be text within the size limit.")
    path = folder / "artifacts" / "film_studio.json"
    current = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"project_id": project_id}
    current.update(data)
    current["updated_at"] = datetime.now(timezone.utc).isoformat()
    _atomic_json(path, current)
    return {"saved": True, "updated_at": current["updated_at"]}


# API routes are registered before this catch-all static app.
app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="film-studio")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.environ.get("FILM_STUDIO_HOST", "127.0.0.1"), port=int(os.environ.get("FILM_STUDIO_PORT", "4173")))
