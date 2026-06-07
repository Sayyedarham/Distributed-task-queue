import time
import sys
import os
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from celery.result import AsyncResult

# Ensure root is on path so we can import tasks, config, rate_limiter
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from tasks import app as celery_app, process_job, send_email, resize_image
from config import settings
from rate_limiter import (
    rate_limit_post_jobs,
    rate_limit_get_job,
    rate_limit_list_jobs,
    rate_limit_revoke_job,
)

app = FastAPI(
    title="Distributed Task Queue API",
    description="FastAPI + Celery + Redis async task system",
    version="1.1.0",
)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request Logging Middleware ───────────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    client_ip = (
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or (request.client.host if request.client else "unknown")
    )

    response = await call_next(request)

    duration = (time.time() - start) * 1000
    print(
        f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
        f"{client_ip} | {request.method} {request.url.path} | "
        f"HTTP {response.status_code} | {duration:.1f}ms",
        flush=True,
    )
    return response

# ── Request schemas ──────────────────────────────────────────────────────────

class JobRequest(BaseModel):
    type: str = "generic"
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
    return {"status": "ok", "environment": settings.ENVIRONMENT}


@app.get("/health/worker")
def health_worker():
    """Check if at least one Celery worker is alive."""
    try:
        inspect = celery_app.control.inspect(timeout=3.0)
        active = inspect.active() or {}
        stats = inspect.stats() or {}
        worker_count = len(stats)
        return {
            "status": "ok",
            "workers_online": worker_count,
            "active_tasks": sum(len(tasks) for tasks in active.values()),
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@app.post("/jobs", status_code=202, dependencies=[Depends(rate_limit_post_jobs)])
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
        task = process_job.delay(req.model_dump())

    return {"task_id": task.id, "status": "PENDING", "type": req.type}


@app.get("/jobs/{task_id}", dependencies=[Depends(rate_limit_get_job)])
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


@app.delete("/jobs/{task_id}", dependencies=[Depends(rate_limit_revoke_job)])
def revoke_job(task_id: str):
    """Revoke (cancel) a pending or running task."""
    celery_app.control.revoke(task_id, terminate=True)
    return {"task_id": task_id, "revoked": True}


@app.get("/jobs", dependencies=[Depends(rate_limit_list_jobs)])
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