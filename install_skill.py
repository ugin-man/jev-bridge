"""Install a portable Agent Skill. Never modifies host settings or credentials."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def linked(path: Path) -> bool:
    return path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction())


def inventory(folder: Path) -> dict[str, str]:
    result = {}
    if linked(folder):
        raise ValueError("Linked skill directories are not copied or overwritten.")
    for path in sorted(folder.rglob("*")):
        if linked(path):
            raise ValueError("Links inside a skill folder are not copied or overwritten.")
        if (path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
                and not any(part.endswith((".egg-info", ".dist-info")) for part in path.parts)):
            result[path.relative_to(folder).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def target_root(target: str, scope: str, project: Path | None = None) -> Path:
    base = (project or Path.cwd()) if scope == "project" else Path.home()
    # Other Agent Skills hosts can supply their own --skills-root.
    folder = ".claude" if target == "claude" else ".agents"
    return base / folder / "skills"


def install(source: Path, skills_root: Path, *, update: bool = False) -> dict:
    if not (source / "SKILL.md").is_file():
        raise ValueError("SKILL.md is missing. Extract the whole archive first.")
    manifest = inventory(source)
    destination = skills_root / "jev"
    for path in (skills_root, destination):
        if linked(path):
            raise ValueError("The install destination is a link; review it locally first.")
    skills_root.mkdir(parents=True, exist_ok=True)
    lock = skills_root / ".jev-install.lock"
    fd = os.open(str(lock), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    staged = backup = None
    try:
        os.close(fd)
        if destination.exists():
            if destination.is_dir() and inventory(destination) == manifest:
                return {"ok": True, "already_installed": True, "path": str(destination), "network_called": False}
            if not update or not destination.is_dir():
                raise ValueError("A different jev skill exists. Compare it, then explicitly use --update to keep a backup and replace it.")
        staged = Path(tempfile.mkdtemp(prefix=".jev-stage-", dir=skills_root))
        for rel in manifest:
            target = staged / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / rel, target)
        if inventory(staged) != manifest:
            raise ValueError("Copied files do not match the source.")
        if destination.exists():
            if not update or linked(destination):
                raise ValueError("The destination changed during installation.")
            backups = skills_root.parent / "jev-skill-backups"
            if linked(backups):
                raise ValueError("The backup directory is a link.")
            backups.mkdir(exist_ok=True)
            backup = backups / uuid.uuid4().hex
            destination.rename(backup)
        try:
            staged.rename(destination)
            staged = None
        except OSError:
            if backup is not None and not destination.exists():
                backup.rename(destination)
                backup = None
            raise
        return {"ok": True, "installed": True, "path": str(destination),
                "backup": str(backup) if backup else None, "network_called": False,
                "host_config_changed": False, "codex_config_changed": False}
    finally:
        if staged is not None:
            shutil.rmtree(staged)
        lock.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=("generic", "codex", "claude"), default="generic")
    parser.add_argument("--scope", choices=("user", "project"), default="user")
    parser.add_argument("--skills-root", type=Path)
    parser.add_argument("--update", action="store_true")
    args = parser.parse_args(argv)
    try:
        root = args.skills_root if args.skills_root is not None else target_root(args.target, args.scope)
        result = install(ROOT / "jev", root.expanduser(), update=args.update)
    except FileExistsError:
        result = {"ok": False, "message": "An installation lock exists. Check it before retrying."}
    except (ValueError, RuntimeError) as exc:
        result = {"ok": False, "message": str(exc)}
    except OSError:
        result = {"ok": False, "message": "Local installation failed. Check permissions and any recorded backup."}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
