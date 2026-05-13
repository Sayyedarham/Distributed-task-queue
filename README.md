# TaskQueue — Distributed Async Job Processing System

> **Live Demo:** [taskqueue-dashboard](https://sayyedarham.github.io/taskqueue-dashboard/) &nbsp;|&nbsp; **API:** [api-production-f1021.up.railway.app](https://api-production-f1021.up.railway.app/health)

A production-deployed distributed task queue system built with **FastAPI**, **Celery**, and **Redis** — featuring real-time job tracking, a terminal-style dashboard, and full cloud deployment on Railway. Designed to demonstrate scalable async architecture patterns used in modern full-stack engineering.

---

## Architecture

```
Browser (GitHub Pages)
    │
    ▼
FastAPI REST API  ──── Redis (broker + backend) ──── Celery Worker(s)
    │                        │                              │
    └── POST /jobs           └── task queue                └── executes jobs
    └── GET  /jobs/{id}          result store                   reports progress
```

All three services (API, Worker, Redis) are independently deployed and horizontally scalable.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend API** | FastAPI (Python 3.11), Pydantic v2 |
| **Task Queue** | Celery 5.3, Redis broker + result backend |
| **Frontend** | Vanilla JS, SSE polling, IBM Plex Mono |
| **Containerization** | Docker (separate images for API and Worker) |
| **Orchestration** | Kubernetes (local via Minikube), Railway (cloud) |
| **Cloud Deploy** | Railway (API + Worker + managed Redis) |
| **Static Hosting** | GitHub Pages |

---

## Features

- **3 job types** — Generic multi-step, Email simulation, Image resize simulation
- **Real-time progress tracking** — live status polling with visual progress bars
- **Concurrent job limits** — 3 active / 10 session (frontend) + concurrency=2 (worker)
- **Job lifecycle management** — submit, track, revoke running jobs
- **Terminal-style dashboard** — live stats, job cards, constraint bars
- **Production-ready** — separate Docker images, health checks, Railway managed infra

---

## Local Development

**Prerequisites:** Python 3.11+, Docker Desktop

```bash
# 1. Start Redis
docker run -d -p 6379:6379 --name redis redis:alpine

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start API (Terminal 1)
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# 4. Start Worker (Terminal 2)
python -m celery -A tasks worker --loglevel=info --concurrency=2 --pool=solo

# 5. Open frontend
# Open frontend/index.html in browser
# Set API URL to http://localhost:8000
```

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/jobs` | Submit async job |
| `GET` | `/jobs/{task_id}` | Poll job status + result |
| `DELETE` | `/jobs/{task_id}` | Revoke running job |
| `GET` | `/jobs` | List active + reserved tasks |

**Submit job example:**
```bash
curl -X POST https://api-production-f1021.up.railway.app/jobs \
  -H "Content-Type: application/json" \
  -d '{"type": "generic", "steps": 4}'
```

**Response:**
```json
{
  "task_id": "abc123-...",
  "status": "PENDING",
  "type": "generic"
}
```

---

## Project Structure

```
dis-task/
├── api/
│   └── main.py          # FastAPI app — routes, job submission, status polling
├── tasks.py             # Celery app — broker config, task definitions
├── frontend/
│   └── index.html       # Dashboard — real-time UI, SSE polling, job management
├── k8s/                 # Kubernetes manifests (Minikube local deploy)
│   ├── api-deploy.yaml
│   ├── worker-deploy.yaml
│   ├── flower-deploy.yaml
│   └── redis-secret.yaml
├── Dockerfile.api       # API container image
├── Dockerfile.worker    # Worker container image
├── Dockerfile.flower    # Flower monitor image
├── railway.toml         # Railway service configuration
└── requirements.txt
```

---

## Deployment (Railway)

Services deployed:

| Service | Description |
|---|---|
| `api` | FastAPI server, public HTTPS endpoint |
| `worker` | Celery worker, 2 concurrent prefork processes |
| `Redis` | Railway managed Redis plugin (broker + result backend) |

Worker connects to Redis via `REDIS_PUBLIC_URL` environment variable injected at runtime.

---

## Key Engineering Decisions

**Why separate Docker images for API and Worker?**
API and Worker have different scaling profiles — API scales with HTTP traffic, Worker scales with queue depth. Separate images allow independent horizontal scaling.

**Why Redis as both broker and backend?**
Simplifies infra for a portfolio/demo context. In production, you'd separate broker (Redis/RabbitMQ) from result backend (Redis/PostgreSQL) for durability guarantees.

**Why `--pool=solo` on Windows locally?**
Celery's default prefork pool uses `billiard` which has known issues with Windows + Python 3.12. Solo pool runs tasks in the main process — fine for local dev, not for production.

---

## What I'd Add Next

- Auth middleware (API key or JWT) on job submission
- Dead letter queue for failed tasks with retry policy
- Prometheus metrics endpoint + Grafana dashboard
- WebSocket-based push instead of polling
- Persistent job history (PostgreSQL)

---

## Author

**Arham Sayyad** — [GitHub](https://github.com/Sayyedarham) · [LinkedIn](https://linkedin.com/in/arham-sayyad)

Built as a full-stack engineering portfolio project demonstrating distributed systems, async processing, containerization, and cloud deployment.
