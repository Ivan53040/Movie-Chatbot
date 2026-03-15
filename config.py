import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent
ENV_PATH = PROJECT_ROOT / ".env"


def load_env_file(env_path=ENV_PATH):
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def get_env(name, default=None):
    load_env_file()
    return os.getenv(name, default)
