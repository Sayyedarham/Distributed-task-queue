from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Optional
from celery.result import AsyncResult
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from tasks import app as celery_app, process_job, send_email, resize_image

app = FastAPI(
    title="Distributed Task Queue API",
    description="FastAPI + Celery + Redis async task system",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request schemas ──────────────────────────────────────────────────────────

class JobRequest(BaseModel):
    type: str = "generic"          # generic | email | image
    steps: Optional[int] = 3
    # email fields
    to: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    # image fields
    filename: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/jobs", status_code=202)
def submit_job(req: JobRequest):
    """Submit a new async job. Returns task_id immediately."""
    if req.type == "email":
        if not req.to or not req.subject:
            raise HTTPException(400, "email jobs need 'to' and 'subject'")
        task = send_email.delay(req.to, req.subject or "", req.body or "")

    elif req.type == "image":
        if not req.filename:
            raise HTTPException(400, "image jobs need 'filename'")
        task = resize_image.delay(
            req.filename,
            req.width or 800,
            req.height or 600,
        )

    else:
        task = process_job.delay(req.dict())

    return {"task_id": task.id, "status": "PENDING", "type": req.type}


@app.get("/jobs/{task_id}")
def get_job_status(task_id: str):
    """Poll task status and result."""
    result = AsyncResult(task_id, app=celery_app)

    response: dict[str, Any] = {
        "task_id": task_id,
        "status": result.status,
    }

    if result.status == "PROGRESS":
        response["progress"] = result.info

    elif result.status == "SUCCESS":
        response["result"] = result.result

    elif result.status == "FAILURE":
        response["error"] = str(result.info)

    return response


@app.delete("/jobs/{task_id}")
def revoke_job(task_id: str):
    """Revoke (cancel) a pending or running task."""
    celery_app.control.revoke(task_id, terminate=True)
    return {"task_id": task_id, "revoked": True}


@app.get("/jobs")
def list_active_jobs():
    """Return active, reserved, and scheduled tasks via Celery inspect."""
    inspect = celery_app.control.inspect(timeout=2.0)
    active = inspect.active() or {}
    reserved = inspect.reserved() or {}
    return {
        "active": active,
        "reserved": reserved,
    }
    
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("api.main:app", host="0.0.0.0", port=port)