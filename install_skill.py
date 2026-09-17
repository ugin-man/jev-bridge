"""Install only this local skill. No API, key access, or Codex config changes."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def inventory(folder: Path) -> dict[str, str]:
    result = {}
    for path in sorted(folder.rglob("*")):
        if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
            raise ValueError("Links inside a skill folder are not copied or overwritten.")
        if path.is_file():
            if "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            result[path.relative_to(folder).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def install(source: Path, skills_root: Path) -> dict:
    if not (source / "SKILL.md").is_file():
        raise ValueError("SKILL.md is missing. Extract the whole ZIP first.")
    manifest = inventory(source)
    destination = skills_root / "jev"
    # Refuse redirected managed destinations, rather than overwrite a shared tree.
    for path in (skills_root, destination):
        if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
            raise ValueError("The install destination is a link. Ask the local agent to review it.")
    skills_root.mkdir(parents=True, exist_ok=True)
    lock = skills_root / ".jev-install.lock"
    fd = os.open(str(lock), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    staged = None
    try:
        os.close(fd)
        if destination.exists():
            if destination.is_dir() and inventory(destination) == manifest:
                return {"ok": True, "already_installed": True, "path": str(destination), "network_called": False}
            raise ValueError("A different jev skill already exists. It was left unchanged; ask Codex to compare it first.")
        staged = Path(tempfile.mkdtemp(prefix=".jev-stage-", dir=skills_root))
        for rel in manifest:
            target = staged / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / rel, target)
        if inventory(staged) != manifest:
            raise ValueError("Copied files did not match the source. Installation stopped.")
        if destination.exists():
            raise ValueError("The destination appeared during installation. Nothing was overwritten.")
        staged.rename(destination)
        staged = None
        return {"ok": True, "installed": True, "path": str(destination),
                "network_called": False, "codex_config_changed": False}
    finally:
        if staged is not None:
            shutil.rmtree(staged)
        lock.unlink(missing_ok=True)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills-root", type=Path, default=Path.home() / ".agents" / "skills")
    args = parser.parse_args()
    try:
        result = install(ROOT / "jev", args.skills_root.expanduser())
    except FileExistsError:
        result = {"ok": False, "message": "Another installation or a prior lock exists. Do not remove it without checking."}
    except ValueError as exc:
        result = {"ok": False, "message": str(exc)}
    except OSError:
        result = {"ok": False, "message": "Cannot copy into the skill directory. Check local permissions; existing data was not deliberately replaced."}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
