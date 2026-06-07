import os
import time
import random
from celery import Celery
from config import settings


# Build Celery config with conditional TLS for Upstash rediss:// URLs
celery_config = {
    "broker_url": settings.REDIS_URL,
    "result_backend": settings.REDIS_URL,
    "task_serializer": "json",
    "result_serializer": "json",
    "accept_content": ["json"],
    "timezone": "UTC",
    "enable_utc": True,
    "task_track_started": True,
    "result_expires": 3600,
}

# Upstash uses rediss:// (TLS). Celery needs explicit SSL config for that.
if settings.REDIS_URL.startswith("rediss://"):
    ssl_cfg = {
        "ssl_cert_reqs": os.environ.get("REDIS_SSL_CERT_REQS", "CERT_NONE"),
        "ssl_ca_certs": None,
        "ssl_certfile": None,
        "ssl_keyfile": None,
    }
    celery_config["broker_use_ssl"] = ssl_cfg
    celery_config["redis_backend_use_ssl"] = ssl_cfg

app = Celery("tasks", **celery_config)


@app.task(bind=True, name="tasks.process_job")
def process_job(self, payload: dict) -> dict:
    """Simulate a real async workload with progress updates."""
    steps = payload.get("steps", 3)
    job_type = payload.get("type", "generic")

    for i in range(1, steps + 1):
        self.update_state(
            state="PROGRESS",
            meta={"current": i, "total": steps, "step": f"Processing step {i}/{steps}"},
        )
        time.sleep(random.uniform(0.5, 1.5))

    return {
        "status": "completed",
        "job_type": job_type,
        "steps_completed": steps,
        "input": payload,
    }


@app.task(bind=True, name="tasks.send_email")
def send_email(self, to: str, subject: str, body: str) -> dict:
    """Simulate email sending task."""
    self.update_state(state="PROGRESS", meta={"step": "Connecting to SMTP"})
    time.sleep(1)
    self.update_state(state="PROGRESS", meta={"step": "Sending email"})
    time.sleep(1)
    return {"sent": True, "to": to, "subject": subject}


@app.task(bind=True, name="tasks.resize_image")
def resize_image(self, filename: str, width: int, height: int) -> dict:
    """Simulate image processing task."""
    self.update_state(state="PROGRESS", meta={"step": "Loading image"})
    time.sleep(0.8)
    self.update_state(state="PROGRESS", meta={"step": f"Resizing to {width}x{height}"})
    time.sleep(1.2)
    self.update_state(state="PROGRESS", meta={"step": "Saving output"})
    time.sleep(0.5)
    return {"resized": True, "filename": filename, "width": width, "height": height}