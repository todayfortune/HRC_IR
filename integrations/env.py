from __future__ import annotations
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load_env(path: Path | None = None) -> None:
    """Load missing values from .env without logging or overwriting process env."""
    env_path = path or ROOT / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)

def require_env(*names: str) -> list[str]:
    missing = [name for name in names if not os.getenv(name)]
    if missing:
        raise RuntimeError("필수 환경 변수가 없습니다: " + ", ".join(missing))
    return [os.environ[name] for name in names]
