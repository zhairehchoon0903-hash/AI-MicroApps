"""Local Film Studio API for OpenMontage.

This service exposes validated pipeline metadata and safe project scaffolding.
It deliberately does not invoke agents, generation providers, or render jobs.
"""
from __future__ import annotations

import json
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
        manifest = load_pipeline(payload.pipeline_type)
    except (FileNotFoundError, ValueError, Exception) as exc:
        raise HTTPException(status_code=400, detail=f"Unknown or invalid pipeline: {payload.pipeline_type}") from exc

    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="Project title cannot be blank.")
    base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:48] or "film"
    project_id = base
    if (PROJECTS_DIR / project_id).exists():
        project_id = f"{base}-{uuid.uuid4().hex[:6]}"

    project_dir = PROJECTS_DIR / project_id
    try:
        project_dir.mkdir(parents=True, exist_ok=False)
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
        # Do not leave a half-created directory behind after a failed scaffold.
        import shutil
        shutil.rmtree(project_dir, ignore_errors=True)
        raise

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
                {"name": s["name"], "status": "pending", "approval_required": s["approval_required"]}
                for s in pipelines()["pipelines"] if s["id"] == payload.pipeline_type
                for s in s["stages"]
            ],
        },
        "message": "Project folder created. No AI generation or rendering was started.",
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


# Serve the mobile-first web app from the same origin as its API.
app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="film-studio")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=4173)
