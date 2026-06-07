import os
from typing import Optional


class Settings:
    """App settings loaded from environment variables with sensible defaults."""

    # ── Redis ──────────────────────────────────────────────────────────────
    REDIS_URL: str = (
        os.environ.get("REDIS_URL")
        or os.environ.get("REDIS_PUBLIC_URL")
        or "redis://localhost:6379/0"
    )

    # ── App ────────────────────────────────────────────────────────────────
    ENVIRONMENT: str = os.environ.get("ENVIRONMENT", "development")
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev-secret-change-me-in-production")

    # ── Frontend (CORS) ────────────────────────────────────────────────────
    FRONTEND_URL: str = os.environ.get(
        "FRONTEND_URL",
        "https://sayyedarham.github.io/Distributed-task-queue/",
    )

    # ── Rate limits ────────────────────────────────────────────────────────
    RATE_LIMIT_PER_MIN: int = int(os.environ.get("RATE_LIMIT_PER_MIN", "10"))
    RATE_LIMIT_POLL_PER_MIN: int = int(os.environ.get("RATE_LIMIT_POLL_PER_MIN", "60"))
    RATE_LIMIT_LIST_PER_MIN: int = int(os.environ.get("RATE_LIMIT_LIST_PER_MIN", "30"))

    # ── Job limits ─────────────────────────────────────────────────────────
    MAX_ACTIVE_JOBS: int = int(os.environ.get("MAX_ACTIVE_JOBS", "3"))
    MAX_SESSION_JOBS: int = int(os.environ.get("MAX_SESSION_JOBS", "10"))

    # ── External services ──────────────────────────────────────────────────
    RESEND_API_KEY: Optional[str] = os.environ.get("RESEND_API_KEY")

    # ── Derived ──────────────────────────────────────────────────────────────
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def cors_origins(self) -> list:
        """Allowed CORS origins. Locked down — no wildcard even in dev."""
        return [
            self.FRONTEND_URL,
            "http://localhost:3000",
            "http://localhost:8000",
            "http://localhost:8080",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8000",
            "http://127.0.0.1:8080",
            "null",  # file:// origins when opening HTML directly
        ]


settings = Settings()