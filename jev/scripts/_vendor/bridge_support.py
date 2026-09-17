"""Application-neutral storage with explicit legacy compatibility, no writes."""
from __future__ import annotations
import os
import sys
from pathlib import Path


def storage_home() -> tuple[Path, str]:
    for name in ("JEV_BRIDGE_HOME", "JEV_SKILL_HOME", "JEV_WORKER_HOME", "JEV_HELPER_HOME"):
        if value := os.environ.get(name):
            return Path(value).expanduser().resolve(), name
    configured = os.environ.get("CODEX_HOME")
    user = None if configured else Path.home()
    legacy = Path(configured).expanduser() if configured else user / ".codex"
    known = [legacy / "tools" / n for n in ("jev-worker", "jev-helper", "jev-skill")]
    if configured:
        # Explicit legacy environment keeps the old storage and usage ledger.
        for path in known:
            if (path / "secrets" / "api-key.dpapi").is_file():
                return path.resolve(), "existing_encrypted_key"
        for path in known:
            if path.is_dir():
                return path.resolve(), "existing_tool_storage"
        return known[-1].resolve(), "skill_storage"
    if os.name == "nt":
        root = Path(os.environ.get("LOCALAPPDATA") or user / "AppData" / "Local")
        neutral = root / "jev-bridge"
    elif sys.platform == "darwin":
        neutral = user / "Library" / "Application Support" / "jev-bridge"
    else:
        configured_state = os.environ.get("XDG_STATE_HOME")
        root = Path(configured_state) if configured_state else user / ".local" / "state"
        if not root.is_absolute():
            raise ValueError("XDG_STATE_HOME must be absolute")
        neutral = root / "jev-bridge"
    if neutral.exists():
        return neutral.resolve(), "platform_storage"
    for path in known:
        if path.is_dir():
            return path.resolve(), "legacy_storage"
    return neutral.resolve(), "platform_storage"
