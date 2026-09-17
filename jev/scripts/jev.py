"""Bounded TypeSafe calls for the jev skill; the host LLM writes the request.

No secondary LLM, background server, model registry edits, or secret arguments.
Validation is offline; a real call additionally requires --execute.
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
import warnings
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent / "_vendor"))
from jev_core import (JevClient, JevError, Settings, build_payload,
                      encode_json, save_key, strict_json)

VERSION = "1.0.1"
MAX_FILE_BYTES = 4 * 1024 * 1024


def selected_home() -> tuple[Path, str]:
    """Reuse only known storage locations, not code imported from a project."""
    for key in ("JEV_SKILL_HOME", "JEV_WORKER_HOME", "JEV_HELPER_HOME"):
        value = os.environ.get(key)
        if value:
            return Path(value).expanduser().resolve(), key
    # Do not eagerly look up the OS home when CODEX_HOME is explicit.
    # Windows may lack USERPROFILE in a deliberately minimal environment.
    configured_base = os.environ.get("CODEX_HOME")
    try:
        base = (Path(configured_base) if configured_base else Path.home() / ".codex").expanduser()
    except RuntimeError as exc:
        raise JevError("home_directory_unavailable", "Cannot determine local storage. Configure CODEX_HOME or JEV_SKILL_HOME locally.") from exc
    known = [base / "tools" / "jev-worker", base / "tools" / "jev-helper"]
    # If a chosen credential/config is broken, report it; never change accounts
    # or homes merely because a request failed or a cap was reached.
    for home in known:
        if (home / "secrets" / "api-key.dpapi").is_file():
            return home.resolve(), "existing_encrypted_key"
    for home in known:
        if home.is_dir():
            return home.resolve(), "existing_tool_storage"
    return (base / "tools" / "jev-skill").resolve(), "skill_storage"


def read_json_file(filename: str) -> Any:
    path = Path(filename).expanduser()
    if not path.is_file():
        raise JevError("input_file_missing", "The agent must create the requested input file first.")
    with path.open("rb") as f:
        content = f.read(MAX_FILE_BYTES + 1)
    if len(content) > MAX_FILE_BYTES:
        raise JevError("file_too_large", "Input exceeds 4 MiB. Split into explicitly bounded groups.")
    try:
        return strict_json(content.decode("utf-8-sig"))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise JevError("invalid_input_json", "The agent must repair the input JSON locally; no request was sent.") from exc


def request_from_files(filename: str | None, recipe: str | None, data: str | None) -> dict:
    if filename:
        if recipe or data:
            raise JevError("conflicting_inputs", "Use --file OR --recipe with --data, not both.")
        request = read_json_file(filename)
    else:
        if not recipe or not data:
            raise JevError("missing_inputs", "Supply --file or both --recipe and --data.")
        definition, records = read_json_file(recipe), read_json_file(data)
        if not isinstance(definition, dict) or "questions" not in definition or set(definition) - {"name", "questions"}:
            raise JevError("invalid_recipe", "Recipe accepts questions and an optional name only.")
        if not isinstance(records, dict) or set(records) not in ({"state"}, {"items"}):
            raise JevError("invalid_data", "Data must contain exactly state or items.")
        request = {**records, "questions": definition["questions"]}
    if not isinstance(request, dict) or set(request) not in ({"state", "questions"}, {"items", "questions"}):
        raise JevError("invalid_request", "Request must contain state/questions or items/questions only.")
    return request


def validate_request(client: JevClient, request: dict) -> dict:
    # No key lookup or transport call in this path.
    if "items" in request:
        return client.batch(request["items"], request["questions"], dry_run=True)
    result = client.evaluate(request["state"], request["questions"], dry_run=True)
    return {**result, "api_requests": 1}


def execute_request(client: JevClient, request: dict, *, execute: bool = False) -> dict:
    checked = validate_request(client, request)
    if not execute:
        return {**checked, "execution_authorized": False,
                "note": "OFFLINE ONLY. The host must obtain scoped user authorization before adding --execute."}
    if "items" in request:
        return client.batch(request["items"], request["questions"])
    return client.evaluate(request["state"], request["questions"])


def reserve_output(filename: str | None):
    """Refuse to overwrite even a partial result, before a paid call starts."""
    if filename is None:
        return None
    path = Path(filename).expanduser()
    try:
        # Deliberately do not create arbitrary parent directories automatically.
        f = path.open("x", encoding="utf-8", newline="\n")
    except FileExistsError as exc:
        raise JevError("output_exists", "Result file already exists. Read it; do not repeat the API call blindly.") from exc
    try:
        f.write('{"status":"execution_not_finished","do_not_retry_blindly":true}\n')
        f.flush()
        os.fsync(f.fileno())
    except Exception:
        f.close()
        raise
    return f


def finish_output(f, result: dict) -> None:
    if f is not None:
        # Keep the reserved file on error/interruption as a no-blind-retry marker.
        f.seek(0)
        f.write(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2) + "\n")
        f.truncate()
        f.flush()
        os.fsync(f.fileno())


def print_json(result: dict) -> None:
    print(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2))


def set_local_key(home: Path) -> dict:
    if os.name != "nt":
        raise JevError("windows_required", "Use the process environment outside Windows. Never put a key in chat or command arguments.")
    if not sys.stdin.isatty():
        raise JevError("interactive_required", "Open SET-KEY.cmd in a local interactive Windows terminal.")
    print("TypeSafe key storage only. NO API request. Input is hidden.")
    print("Storage: " + str(home))
    if (home / "secrets" / "api-key.dpapi").exists():
        if input("An encrypted key already exists. Replace it? [y/N]: ").strip().lower() != "y":
            return {"ok": True, "cancelled": True, "network_called": False}
    # Do not accept a getpass fallback that would echo the credential.
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        try:
            key = getpass.getpass("TypeSafe API key (Enter cancels): ")
        except getpass.GetPassWarning as exc:
            raise JevError("hidden_input_unavailable", "No key was accepted. Use a local interactive terminal with hidden input.") from exc
    if not key.strip():
        return {"ok": True, "cancelled": True, "network_called": False}
    save_key(home, key)
    key = ""
    return {"ok": True, "network_called": False, "key_saved_locally": True,
            "credential_validated_with_service": False}


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    sub.add_parser("set-key")
    for command in ("validate", "run"):
        p = sub.add_parser(command)
        p.add_argument("--file")
        p.add_argument("--recipe")
        p.add_argument("--data")
        if command == "run":
            p.add_argument("--execute", action="store_true", help="Requires user authorization; may consume TypeSafe credits.")
            p.add_argument("--out", help="New result file, reserved before any paid request. No overwrite.")
    args = parser.parse_args(argv)
    output = None
    execute_started = False
    try:
        home, source = selected_home()
        client = JevClient(home)
        if args.command == "status":
            result = {**client.status(), "skill_version": VERSION, "storage_home": str(home), "home_source": source}
        elif args.command == "set-key":
            result = set_local_key(home)
        else:
            request = request_from_files(args.file, args.recipe, args.data)
            if args.command == "validate":
                result = validate_request(client, request)
            else:
                # Validate everything, then reserve output, then contact service.
                validate_request(client, request)
                output = reserve_output(args.out)
                execute_started = bool(args.execute)
                result = execute_request(client, request, execute=args.execute)
                finish_output(output, result)
        print_json(result)
        return 0 if result.get("ok") else 1
    except JevError as exc:
        result = {"ok": False, "error": exc.as_dict(), "execution_requested": execute_started,
                  "note": "No automatic retry. Read any partial results before deciding what to retry."}
        try:
            finish_output(output, result)
        except OSError:
            result["result_save_failed"] = True
        print_json(result)
        return 1
    except KeyboardInterrupt:
        print_json({"ok": False, "interrupted": True, "execution_requested": execute_started,
                    "note": "An in-flight request may already have been processed. Do not repeat blindly."})
        return 130
    except (OSError, ValueError, TypeError, RecursionError):
        print_json({"ok": False, "error": {"code": "local_io_error", "message": "Local input/output failed. No raw exception or credentials are displayed."},
                    "execution_requested": execute_started, "automatic_retry": False})
        return 1
    finally:
        if output is not None:
            output.close()


if __name__ == "__main__":
    raise SystemExit(main())
