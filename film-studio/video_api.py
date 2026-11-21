"""Server-side multi-provider video generation for OpenMontage Film Studio.

Provider credentials never leave the server. Every paid generation requires a
fresh quote and an explicit user-approved maximum spend.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from backlot.state import PROJECTS_DIR

router = APIRouter(prefix="/api", tags=["video-generation"])
PROJECT_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")

class VideoRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=1000)
    start_image_url: str = Field(min_length=13, max_length=5_242_880)
    duration_seconds: int = Field(default=5, ge=2, le=10)
    aspect_ratio: str = Field(default="9:16")
    resolution: str = Field(default="720p")
    audio: bool = False

class VideoGenerateRequest(VideoRequest):
    provider_id: str = Field(min_length=1, max_length=40)
    approved_max_spend_usd: float = Field(ge=0, le=5000)
    confirm_generation: bool = False


def _project_folder(project_id: str) -> Path:
    if not PROJECT_ID.fullmatch(project_id):
        raise HTTPException(status_code=400, detail="Invalid project id.")
    root = PROJECTS_DIR.resolve()
    folder = (root / project_id).resolve()
    if folder.parent != root or not folder.is_dir():
        raise HTTPException(status_code=404, detail="Film production project not found on the server. Create or connect the production project first.")
    return folder


def _rate(name: str) -> float | None:
    try:
        value = float(os.environ.get(name, ""))
        return value if value > 0 else None
    except (TypeError, ValueError):
        return None


def _providers() -> dict[str, dict[str, Any]]:
    runway_key = os.environ.get("RUNWAYML_API_SECRET", "").strip()
    runway_rate = _rate("RUNWAY_DEV_PRICE_USD_PER_SECOND")
    fal_key = os.environ.get("FAL_KEY", "").strip()
    fal_rates = {tier: _rate(f"FAL_WAN3_PRICE_{tier.upper()}") for tier in ("480p", "720p", "1080p")}
    return {
        "runway-dev": {"id": "runway-dev", "name": "Runway Dev API", "model": os.environ.get("RUNWAY_DEV_MODEL", "gen4.5"), "configured": bool(runway_key and runway_rate), "key_configured": bool(runway_key), "pricing_configured": bool(runway_rate), "rate": runway_rate, "note": "Pay-as-you-go developer API; separate from the Runway consumer subscription."},
        "fal-wan3": {"id": "fal-wan3", "name": "fal.ai · Wan 3.0", "model": "alibaba/wan-3.0/image-to-video", "configured": bool(fal_key and all(fal_rates.values())), "key_configured": bool(fal_key), "pricing_configured": all(fal_rates.values()), "rates": fal_rates, "note": "Queue-based pay-per-generation API. Rates are configured by the server operator."},
    }


def _http_json(url: str, method: str = "GET", headers: dict[str, str] | None = None, body: dict | None = None, timeout: int = 45) -> dict:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = "Provider request failed."
        try:
            payload = json.loads(exc.read().decode("utf-8"))
            detail = str(payload.get("message") or payload.get("detail") or payload.get("error") or detail)[:400]
        except Exception:
            pass
        raise HTTPException(status_code=502, detail=f"Video provider returned HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise HTTPException(status_code=502, detail="Could not reach the selected video provider. Check the server network and provider status.") from exc
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=502, detail="Video provider returned an invalid JSON response.") from exc
    if not isinstance(result, dict):
        raise HTTPException(status_code=502, detail="Video provider returned an unexpected response.")
    return result


def _validate_request(payload: VideoRequest) -> None:
    if payload.aspect_ratio not in {"9:16", "16:9", "1:1"}:
        raise HTTPException(status_code=422, detail="Choose 9:16, 16:9, or 1:1 aspect ratio.")
    if payload.resolution not in {"480p", "720p", "1080p"}:
        raise HTTPException(status_code=422, detail="Choose 480p, 720p, or 1080p resolution.")
    image = payload.start_image_url.strip()
    if not (image.startswith("https://") or image.startswith("data:image/")):
        raise HTTPException(status_code=422, detail="Starting frame must be a public HTTPS image URL or an image data URI. Local filesystem paths are not accepted.")
    if len(image) > 5_242_880:
        raise HTTPException(status_code=413, detail="Starting frame data URI exceeds 5 MB.")


def _quote(payload: VideoRequest, provider_id: str) -> dict:
    providers = _providers()
    provider = providers.get(provider_id)
    if not provider or not provider["configured"]:
        raise HTTPException(status_code=503, detail=f"{provider_id} is not fully configured. Add its server-side API key and current model pricing before requesting a quote.")
    if provider_id == "runway-dev":
        if payload.resolution != "720p":
            raise HTTPException(status_code=422, detail="The initial Runway Dev adapter is configured for its 720p vertical/horizontal output tier. Select 720p or use fal.ai for other tiers.")
        ratio = {"9:16": "720:1280", "16:9": "1280:720", "1:1": "960:960"}[payload.aspect_ratio]
        model = provider["model"]
        rate = provider["rate"]
    else:
        model = provider["model"]
        rate = provider["rates"].get(payload.resolution)
        if not rate:
            raise HTTPException(status_code=503, detail=f"fal.ai pricing for {payload.resolution} is not configured on the server.")
        ratio = payload.aspect_ratio
    return {"provider_id": provider_id, "provider_name": provider["name"], "model": model, "duration_seconds": payload.duration_seconds, "aspect_ratio": payload.aspect_ratio, "resolution": payload.resolution, "estimated_cost_usd": round(rate * payload.duration_seconds, 4), "currency": "USD", "pricing_basis": f"Server-configured rate ${rate:.4f} per output second × {payload.duration_seconds} seconds.", "warning": "Estimate only. Confirm the provider's current pricing before generation; provider rates and model settings can change."}


def _task_file(folder: Path) -> Path:
    path = folder / "artifacts" / "video_generation.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _load_tasks(folder: Path) -> list[dict]:
    path = _task_file(folder)
    if not path.is_file():
        return []
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, list) else []
    except (OSError, json.JSONDecodeError):
        raise HTTPException(status_code=500, detail="Saved video generation history could not be read.")


def _save_tasks(folder: Path, tasks: list[dict]) -> None:
    path = _task_file(folder)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(tasks[-200:], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _submit_runway(payload: VideoGenerateRequest) -> tuple[str, dict]:
    key = os.environ["RUNWAYML_API_SECRET"].strip()
    ratio = {"9:16": "720:1280", "16:9": "1280:720", "1:1": "960:960"}[payload.aspect_ratio]
    result = _http_json("https://api.dev.runwayml.com/v1/image_to_video", "POST", {"Authorization": f"Bearer {key}", "X-Runway-Version": "2024-11-06"}, {"model": os.environ.get("RUNWAY_DEV_MODEL", "gen4.5"), "promptImage": payload.start_image_url, "promptText": payload.prompt, "position": "first", "ratio": ratio, "duration": payload.duration_seconds})
    provider_task_id = str(result.get("id") or "")
    if not provider_task_id:
        raise HTTPException(status_code=502, detail="Runway accepted no recognizable task ID. No automatic retry was attempted.")
    return provider_task_id, result


def _submit_fal(payload: VideoGenerateRequest) -> tuple[str, dict]:
    key = os.environ["FAL_KEY"].strip()
    endpoint = "alibaba/wan-3.0/image-to-video"
    result = _http_json(f"https://queue.fal.run/{endpoint}", "POST", {"Authorization": f"Key {key}"}, {"prompt": payload.prompt, "start_image_url": payload.start_image_url, "duration": payload.duration_seconds, "resolution": payload.resolution, "aspect_ratio": payload.aspect_ratio, "audio": payload.audio})
    provider_task_id = str(result.get("request_id") or "")
    if not provider_task_id:
        raise HTTPException(status_code=502, detail="fal.ai accepted no recognizable request ID. No automatic retry was attempted.")
    return provider_task_id, result


def _poll_task(record: dict) -> dict:
    provider_id = record["provider_id"]
    provider_task_id = record["provider_task_id"]
    if provider_id == "runway-dev":
        key = os.environ.get("RUNWAYML_API_SECRET", "").strip()
        if not key:
            raise HTTPException(status_code=503, detail="Runway API key is no longer configured on the server.")
        result = _http_json(f"https://api.dev.runwayml.com/v1/tasks/{urllib.parse.quote(provider_task_id, safe='')}", headers={"Authorization": f"Bearer {key}", "X-Runway-Version": "2024-11-06"})
        status = str(result.get("status", "UNKNOWN")).upper()
        output = result.get("output")
        output_url = output[0] if isinstance(output, list) and output and isinstance(output[0], str) else output if isinstance(output, str) else None
        record.update({"status": status, "output_url": output_url, "provider_result": result})
    elif provider_id == "fal-wan3":
        key = os.environ.get("FAL_KEY", "").strip()
        if not key:
            raise HTTPException(status_code=503, detail="fal.ai API key is no longer configured on the server.")
        endpoint = "alibaba/wan-3.0/image-to-video"
        encoded = urllib.parse.quote(provider_task_id, safe="")
        status_result = _http_json(f"https://queue.fal.run/{endpoint}/requests/{encoded}/status", headers={"Authorization": f"Key {key}"})
        status = str(status_result.get("status", "UNKNOWN")).upper()
        record["status"] = {"IN_QUEUE": "PENDING", "IN_PROGRESS": "RUNNING", "COMPLETED": "SUCCEEDED"}.get(status, status)
        if status == "COMPLETED":
            result = _http_json(f"https://queue.fal.run/{endpoint}/requests/{encoded}", headers={"Authorization": f"Key {key}"})
            video = result.get("video") if isinstance(result.get("video"), dict) else {}
            record.update({"output_url": video.get("url"), "provider_result": result})
        elif status_result.get("error"):
            record["error"] = str(status_result.get("error"))[:400]
    else:
        raise HTTPException(status_code=400, detail="Unknown video provider in saved task.")
    record["updated_at"] = datetime.now(timezone.utc).isoformat()
    return record


@router.get("/video/providers")
def video_providers() -> dict:
    return {"providers": list(_providers().values()), "generation_started": False, "note": "Only server-configured providers are listed as ready. API keys are never returned."}


@router.post("/projects/{project_id}/video/quote")
def quote_video(project_id: str, payload: VideoRequest) -> dict:
    _project_folder(project_id)
    _validate_request(payload)
    quotes = []
    unavailable = []
    for provider_id in ("runway-dev", "fal-wan3"):
        try:
            quotes.append(_quote(payload, provider_id))
        except HTTPException as exc:
            unavailable.append({"provider_id": provider_id, "reason": str(exc.detail)})
    return {"quotes": sorted(quotes, key=lambda item: item["estimated_cost_usd"]), "unavailable": unavailable, "generation_started": False}


@router.post("/projects/{project_id}/video/generate")
def generate_video(project_id: str, payload: VideoGenerateRequest) -> dict:
    folder = _project_folder(project_id)
    _validate_request(payload)
    if payload.confirm_generation is not True:
        raise HTTPException(status_code=400, detail="Explicit generation confirmation is required.")
    quote = _quote(payload, payload.provider_id)
    if quote["estimated_cost_usd"] > payload.approved_max_spend_usd:
        raise HTTPException(status_code=409, detail={"code": "SPEND_APPROVAL_REQUIRED", "quote": quote, "approved_max_spend_usd": payload.approved_max_spend_usd})
    # One submission only. Never retry or silently switch providers after a paid request.
    if payload.provider_id == "runway-dev":
        provider_task_id, raw = _submit_runway(payload)
    elif payload.provider_id == "fal-wan3":
        provider_task_id, raw = _submit_fal(payload)
    else:
        raise HTTPException(status_code=400, detail="Unsupported provider.")
    record = {"task_id": str(uuid.uuid4()), "provider_id": payload.provider_id, "provider_name": quote["provider_name"], "model": quote["model"], "provider_task_id": provider_task_id, "status": str(raw.get("status") or "PENDING").upper(), "prompt": payload.prompt, "start_image_url": payload.start_image_url, "duration_seconds": payload.duration_seconds, "aspect_ratio": payload.aspect_ratio, "resolution": payload.resolution, "audio": payload.audio, "quote": quote, "approved_max_spend_usd": payload.approved_max_spend_usd, "created_at": datetime.now(timezone.utc).isoformat(), "updated_at": datetime.now(timezone.utc).isoformat(), "output_url": None}
    tasks = _load_tasks(folder)
    # Enforce the project's recorded production budget as well as the per-shot approval.
    project_path = folder / "project.json"
    try:
        project_meta = json.loads(project_path.read_text(encoding="utf-8"))
        project_budget = float((project_meta.get("film_studio") or {}).get("budget_cap_usd", 0))
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=500, detail="The production budget could not be verified. No generation was submitted.") from exc
    committed_estimate = sum(float(item.get("quote", {}).get("estimated_cost_usd", 0) or 0) for item in tasks)
    remaining = max(0.0, project_budget - committed_estimate)
    if quote["estimated_cost_usd"] > remaining:
        raise HTTPException(status_code=409, detail={"code": "PROJECT_BUDGET_EXCEEDED", "project_budget_usd": project_budget, "committed_estimate_usd": round(committed_estimate, 4), "remaining_budget_usd": round(remaining, 4), "quote": quote})
    tasks.append(record)
    _save_tasks(folder, tasks)
    return {"task": {k: v for k, v in record.items() if k not in {"provider_task_id", "start_image_url"}}, "message": "Generation submitted once. Refresh task status to retrieve the result; retries require a new quote and approval."}


@router.get("/projects/{project_id}/video/tasks")
def list_video_tasks(project_id: str) -> dict:
    folder = _project_folder(project_id)
    tasks = _load_tasks(folder)
    return {"tasks": [{k: v for k, v in task.items() if k not in {"provider_task_id", "start_image_url", "provider_result"}} for task in reversed(tasks)]}


@router.get("/projects/{project_id}/video/tasks/{task_id}")
def refresh_video_task(project_id: str, task_id: str) -> dict:
    folder = _project_folder(project_id)
    tasks = _load_tasks(folder)
    record = next((item for item in tasks if item.get("task_id") == task_id), None)
    if not record:
        raise HTTPException(status_code=404, detail="Video task not found.")
    if record.get("status") not in {"SUCCEEDED", "FAILED", "CANCELLED"}:
        record = _poll_task(record)
        tasks = [record if item.get("task_id") == task_id else item for item in tasks]
        _save_tasks(folder, tasks)
    safe = {k: v for k, v in record.items() if k not in {"provider_task_id", "start_image_url", "provider_result"}}
    return {"task": safe}
