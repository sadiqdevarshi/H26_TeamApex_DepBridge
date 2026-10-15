from dataclasses import dataclass, field
import os
from pathlib import Path


@dataclass
class Settings:
    data_dir: Path = field(default_factory=lambda: Path(os.getenv("DEPBRIDGE_DATA_DIR", ".depbridge")).resolve())
    frontend_dir: Path = field(default_factory=lambda: Path(os.getenv("DEPBRIDGE_FRONTEND_DIR", "frontend")).resolve())
    public_base_url: str = field(default_factory=lambda: os.getenv("DEPBRIDGE_PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip("/"))
    allowed_repositories: tuple[str, ...] = field(default_factory=lambda: tuple(
        value.strip().lower() for value in os.getenv("DEPBRIDGE_ALLOWED_REPOSITORIES", "rishrek/LinkWatch").split(",") if value.strip()
    ))
    max_pending_jobs: int = field(default_factory=lambda: int(os.getenv("DEPBRIDGE_MAX_PENDING_JOBS", "8")))
    engine_mode: str = field(default_factory=lambda: os.getenv("DEPBRIDGE_ENGINE_MODE", "auto"))

    def __post_init__(self):
        self.data_dir = Path(self.data_dir).resolve()
        self.frontend_dir = Path(self.frontend_dir).resolve()
        if self.max_pending_jobs < 1:
            raise ValueError("DEPBRIDGE_MAX_PENDING_JOBS must be positive")
        if self.engine_mode not in {"auto", "preview"}:
            raise ValueError("DEPBRIDGE_ENGINE_MODE must be auto or preview")
        from urllib.parse import urlsplit
        url = urlsplit(self.public_base_url)
        if url.scheme not in {"http", "https"} or not url.netloc or url.username or url.password or url.query or url.fragment or url.path not in {"", "/"}:
            raise ValueError("DEPBRIDGE_PUBLIC_BASE_URL must be an HTTP(S) origin without credentials")
