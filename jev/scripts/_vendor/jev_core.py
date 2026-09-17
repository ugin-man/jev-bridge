"""Small, dependency-free client for the documented TypeSafe System One API.

Only explicitly supplied state/questions are sent. No files, browsers, shell
commands, alternate providers, or implicit retries are exposed to the model.
"""
from __future__ import annotations

import copy
import ctypes
import json
import math
import os
import re
import socket
import sqlite3
import ssl
import tempfile
import threading
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any, Callable

VERSION = "2.0.0"
API_URL = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-latest"


class JevError(Exception):
    """An intentionally sanitized error that can be returned to the MCP client."""

    def __init__(self, code: str, message: str, *, status: int | None = None,
                 ambiguous_charge: bool = False):
        super().__init__(message)
        self.code, self.message = code, message
        self.status, self.ambiguous_charge = status, ambiguous_charge

    def as_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.status is not None:
            value["http_status"] = self.status
        if self.ambiguous_charge:
            value["billing_may_have_occurred"] = True
        value["automatic_retry"] = False
        return value


def strict_json(text: str | bytes) -> Any:
    def reject_constant(_: str) -> None:
        raise ValueError("Non-finite JSON number")
    def unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for k, v in pairs:
            if k in result:
                raise ValueError("Duplicate JSON key")
            result[k] = v
        return result
    return json.loads(text, parse_constant=reject_constant, object_pairs_hook=unique_pairs)


def encode_json(value: Any) -> bytes:
    try:
        return json.dumps(value, ensure_ascii=False, allow_nan=False,
                          separators=(",", ":")).encode("utf-8")
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        raise JevError("invalid_json", "Input must be finite, UTF-8 encodable JSON.") from exc


def home_dir() -> Path:
    from bridge_support import storage_home
    try:
        return storage_home()[0]
    except (RuntimeError, OSError, ValueError) as exc:
        raise JevError("home_directory_unavailable", "Configure JEV_BRIDGE_HOME locally.") from exc


def atomic_write(path: Path, content: bytes, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(name, mode)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


@dataclass(frozen=True)
class Settings:
    # These are local safety limits, NOT claims about the service's maximums.
    model: str = MODEL
    request_timeout_seconds: int = 25
    max_request_bytes: int = 262_144
    max_response_bytes: int = 1_048_576
    max_questions: int = 100
    max_batch_items: int = 20
    max_daily_requests: int = 200
    max_daily_payload_bytes: int = 10_485_760
    max_input_file_bytes: int = 4_194_304
    max_batch_seconds: int = 90
    trust_environment: bool = False

    @classmethod
    def load(cls, home: Path) -> "Settings":
        path = home / "settings.json"
        if not path.exists():
            return cls()
        try:
            raw = strict_json(path.read_bytes())
            if not isinstance(raw, dict):
                raise ValueError()
            if set(raw) - {f.name for f in fields(cls)}:
                raise ValueError()
            obj = cls(**raw)
            if not isinstance(obj.model, str) or not obj.model.strip():
                raise ValueError()
            if type(obj.trust_environment) is not bool:
                raise ValueError()
            optional_caps = {"max_daily_requests", "max_daily_payload_bytes", "max_batch_seconds"}
            for field in fields(cls):
                if field.name in {"model", "trust_environment"}:
                    continue
                value = getattr(obj, field.name)
                if type(value) is not int or value < (0 if field.name in optional_caps else 1):
                    raise ValueError()
            return obj
        except (OSError, TypeError, ValueError, RecursionError) as exc:
            raise JevError("invalid_settings", "Invalid settings.json; no request was sent.") from exc


def _dpapi(data: bytes, *, decrypt: bool) -> bytes:
    """Windows current-user DPAPI. Does not fall back to plaintext storage."""
    if os.name != "nt":
        raise JevError("windows_required", "This saved DPAPI credential requires the original Windows user. Configure a native vault or TYPESAFE_API_KEY on other platforms.")
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]

    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    byte_array = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
    incoming = DATA_BLOB(len(data), byte_array)
    outgoing = DATA_BLOB()
    common = [ctypes.POINTER(DATA_BLOB), ctypes.c_void_p, ctypes.c_void_p,
              ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(DATA_BLOB)]
    func = crypt32.CryptUnprotectData if decrypt else crypt32.CryptProtectData
    func.argtypes = common
    func.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    if not func(ctypes.byref(incoming), None, None, None, None, 1, ctypes.byref(outgoing)):
        raise JevError("credential_error", "Windows could not protect/unprotect the API key for this user.")
    try:
        return ctypes.string_at(outgoing.pbData, outgoing.cbData)
    finally:
        kernel32.LocalFree(outgoing.pbData)


def validate_key(key: str) -> str:
    key = key.strip()
    if not key or len(key) > 4_096 or any(ord(c) < 33 or ord(c) > 126 for c in key):
        raise JevError("invalid_key", "API key must be a nonempty ASCII token without spaces or line breaks.")
    return key


def secure_keyring():
    try:
        import keyring
        backend = keyring.get_keyring()
        # Only native OS credential vaults; never accept a plaintext fallback.
        module = type(backend).__module__
        if module not in {"keyring.backends.macOS", "keyring.backends.Windows",
                          "keyring.backends.SecretService", "keyring.backends.kwallet"}:
            raise RuntimeError()
        return keyring
    except Exception as exc:
        raise JevError("secure_store_unavailable", "Install the keyring extra and configure an OS credential vault, or use TYPESAFE_API_KEY in the process environment. No plaintext fallback.") from exc


def keyring_account(home: Path) -> str:
    import hashlib
    return hashlib.sha256(str(home.resolve()).encode("utf-8")).hexdigest()


def save_key(home: Path, key: str) -> None:
    key = validate_key(key)
    if os.name == "nt":
        encrypted = _dpapi(key.encode("ascii"), decrypt=False)
        atomic_write(home / "secrets" / "api-key.dpapi", encrypted)
        return
    vault = secure_keyring()
    try:
        vault.set_password("jev-bridge", keyring_account(home), key)
        atomic_write(home / "secrets" / "keyring.json", b'{"backend":"os-keyring"}\n')
    except Exception as exc:
        raise JevError("credential_error", "Could not complete OS credential storage. No key is printed.") from exc


def load_key(home: Path) -> tuple[str, str]:
    path = home / "secrets" / "api-key.dpapi"
    # A newly entered key wins over a potentially stale inherited environment.
    if path.exists():
        try:
            if path.stat().st_size > 65_536:
                raise ValueError()
            key = _dpapi(path.read_bytes(), decrypt=True).decode("ascii")
            return validate_key(key), "windows_dpapi"
        except JevError:
            raise
        except (OSError, ValueError, UnicodeError) as exc:
            raise JevError("credential_error", "Cannot read the saved key. Run SET-KEY.cmd as the same Windows user.") from exc
    if (home / "secrets" / "keyring.json").exists():
        try:
            key = secure_keyring().get_password("jev-bridge", keyring_account(home))
            return validate_key(key or ""), "os_keyring"
        except JevError:
            raise
        except Exception as exc:
            raise JevError("credential_error", "Cannot read the configured OS credential vault.") from exc
    env_key = os.environ.get("TYPESAFE_API_KEY", "")
    if env_key:
        return validate_key(env_key), "process_environment"
    raise JevError("missing_api_key", "No TypeSafe API key is configured. Run set-key locally or configure TYPESAFE_API_KEY; never paste a key into chat.")


def validate_description(value: Any, label: str, *, nullable: bool = False) -> None:
    if nullable and value is None:
        return
    if not isinstance(value, (str, dict, list)):
        raise JevError("invalid_argument", f"{label} must be a string, object or array.")
    encode_json(value)


def validate_questions(questions: Any, settings: Settings) -> dict[str, Any]:
    if not isinstance(questions, dict) or not 1 <= len(questions) <= settings.max_questions:
        raise JevError("invalid_questions", f"Supply 1..{settings.max_questions} questions as an object.")
    for qid, q in questions.items():
        if not isinstance(qid, str) or not qid.strip():
            raise JevError("invalid_questions", "Question IDs must be nonblank strings.")
        if not isinstance(q, dict) or set(q) - {"type", "instructions", "criteria"}:
            raise JevError("invalid_questions", "Each question accepts only type, instructions and criteria.")
        kind = q.get("type")
        if kind not in ("choice", "score", "noul"):
            raise JevError("invalid_questions", "Question type must be choice, score or noul.")
        if "instructions" not in q:
            raise JevError("invalid_questions", "Question instructions are required.")
        validate_description(q["instructions"], "instructions", nullable=True)
        criteria = q.get("criteria")
        if kind == "choice":
            if not isinstance(criteria, dict) or not 2 <= len(criteria) <= 255:
                raise JevError("invalid_questions", "Choice requires 2..255 labeled options (documented TypeSafe limit).")
            for label, desc in criteria.items():
                if not isinstance(label, str) or not label.strip():
                    raise JevError("invalid_questions", "Choice option labels must be nonblank strings.")
                validate_description(desc, "Choice description", nullable=True)
        elif kind == "score":
            if not isinstance(criteria, list) or not 2 <= len(criteria) <= 10:
                raise JevError("invalid_questions", "Score requires 2..10 ordered level descriptions.")
            for desc in criteria:
                validate_description(desc, "Score level", nullable=True)
        elif "criteria" in q:
            if not isinstance(criteria, dict) or set(criteria) - {"true", "false"}:
                raise JevError("invalid_questions", "Optional Noul criteria accepts true and false descriptions.")
            for desc in criteria.values():
                validate_description(desc, "Noul description", nullable=True)
    return copy.deepcopy(questions)


def build_payload(state: Any, questions: Any, settings: Settings) -> tuple[dict[str, Any], bytes]:
    validate_description(state, "state")
    payload = {"state": copy.deepcopy(state), "model": settings.model,
               "questions": validate_questions(questions, settings)}
    data = encode_json(payload)
    if len(data) > settings.max_request_bytes:
        raise JevError("request_too_large", f"Encoded request exceeds {settings.max_request_bytes} bytes; split it explicitly.")
    return payload, data


def _number(value: Any, low: float, high: float) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and low <= value <= high


def validate_response(raw: Any, questions: dict[str, Any]) -> dict[str, Any]:
    """Reject malformed decisions, while preserving the model's probabilities."""
    def bad() -> None:
        raise JevError("invalid_api_response", "TypeSafe returned an unexpected response shape. No result was fabricated.", ambiguous_charge=True)
    if not isinstance(raw, dict) or not isinstance(raw.get("model"), str) or not raw["model"]:
        bad()
    answers = raw.get("answers")
    if not isinstance(answers, dict) or set(answers) != set(questions):
        bad()
    for qid, q in questions.items():
        a = answers[qid]
        if not isinstance(a, dict) or a.get("type") != q["type"]:
            bad()
        kind = q["type"]
        if kind == "noul":
            if not _number(a.get("noul"), 0, 1):
                bad()
            continue
        if not _number(a.get("confidence"), 0, 1):
            bad()
        probs = a.get("probabilities")
        keys = set(q["criteria"]) if kind == "choice" else {str(i) for i in range(len(q["criteria"]))}
        if not isinstance(probs, dict) or set(probs) != keys:
            bad()
        if not all(_number(p, 0, 1) for p in probs.values()) or abs(sum(probs.values()) - 1) > 0.02:
            bad()
        if kind == "choice":
            if not isinstance(a.get("choice"), str) or a["choice"] not in keys:
                bad()
            if probs[a["choice"]] + 0.02 < max(probs.values()):
                bad()
        else:
            if not _number(a.get("score"), 0, len(keys) - 1):
                bad()
            if not isinstance(a.get("legend"), dict) or set(a["legend"]) != keys:
                bad()
            expected = sum(int(k) * p for k, p in probs.items())
            if abs(a["score"] - expected) > 0.02 * len(keys):
                bad()
    usage = raw.get("usage")
    if not isinstance(usage, dict) or any(type(usage.get(k)) is not int or usage[k] < 0
                                           for k in ("input_tokens", "output_tokens")):
        bad()
    # Avoid propagating arbitrary unrecognized metadata/instructions from upstream.
    allowed = {"noul": ("type", "noul"),
               "choice": ("type", "choice", "probabilities", "confidence"),
               "score": ("type", "score", "legend", "probabilities", "confidence")}
    clean_answers = {qid: {k: answers[qid][k] for k in allowed[q["type"]]}
                     for qid, q in questions.items()}
    clean_usage = {k: usage[k] for k in ("input_tokens", "output_tokens")}
    return {"model": raw["model"], "answers": clean_answers, "usage": clean_usage}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Never forward credentials to a redirected destination."""
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str,
                         headers: Any, newurl: str) -> None:
        return None


def post_http(data: bytes, key: str, settings: Settings) -> Any:
    # Explicit empty proxies avoids sending this secret through an unexpected
    # inherited proxy. Corporate users must review the transport before adapting.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler(None if settings.trust_environment else {}), NoRedirect(),
                                         urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    req = urllib.request.Request(API_URL, data=data, method="POST", headers={
        "Authorization": "Bearer " + key,
        "Content-Type": "application/json; charset=utf-8",
        "Accept": "application/json",
        "User-Agent": "jev-bridge/" + VERSION,
    })
    try:
        with opener.open(req, timeout=settings.request_timeout_seconds) as response:
            if response.status != 200:
                raise JevError("http_error", "Unexpected TypeSafe HTTP status.", status=response.status,
                               ambiguous_charge=True)
            if response.headers.get_content_type() != "application/json":
                raise JevError("invalid_api_response", "TypeSafe did not return JSON.", ambiguous_charge=True)
            content = response.read(settings.max_response_bytes + 1)
            if len(content) > settings.max_response_bytes:
                raise JevError("response_too_large", "TypeSafe response exceeded the local size limit.", ambiguous_charge=True)
            try:
                return strict_json(content)
            except (ValueError, UnicodeError, RecursionError) as exc:
                raise JevError("invalid_api_response", "TypeSafe response was not valid JSON.", ambiguous_charge=True) from exc
    except urllib.error.HTTPError as exc:
        code = exc.code
        exc.close()  # Do not log/return the body; it may echo submitted data.
        messages = {
            401: "TypeSafe rejected the API key. Update it using SET-KEY.cmd.",
            402: "TypeSafe requires account credit/payment. No automatic purchase or top-up was attempted.",
            403: "TypeSafe denied access for this account or key.",
            404: "TypeSafe endpoint/model was not found. Check official API availability.",
            422: "TypeSafe rejected the request shape. Check the official schema and supplied questions.",
            429: "TypeSafe rate limit reached. Stop; wait before explicitly retrying.",
            529: "TypeSafe is overloaded. Stop; wait before explicitly retrying.",
        }
        raise JevError("http_error", messages.get(code, "TypeSafe returned an HTTP error; response body omitted."),
                       status=code, ambiguous_charge=code >= 500) from exc
    except (TimeoutError, socket.timeout) as exc:
        raise JevError("timeout", "TypeSafe request timed out. It may already have been processed; no automatic retry.", ambiguous_charge=True) from exc
    except (urllib.error.URLError, OSError) as exc:
        raise JevError("network_error", "Could not complete the verified HTTPS request to TypeSafe. No automatic retry.", ambiguous_charge=True) from exc


class UsageLedger:
    """Cross-process daily request/byte caps. Stores counters only, never payloads.

    Reservations count even failed calls. This is conservative and is NOT a dollar
    budget or an account-wide limit. It covers processes sharing this local home.
    """
    def __init__(self, home: Path, settings: Settings):
        self.home, self.settings = home, settings

    @contextmanager
    def db(self):
        self.home.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.home / "usage.sqlite3", timeout=5)
        try:
            conn.execute("CREATE TABLE IF NOT EXISTS daily (day TEXT PRIMARY KEY, requests INTEGER NOT NULL, payload_bytes INTEGER NOT NULL, input_tokens INTEGER NOT NULL, output_tokens INTEGER NOT NULL)")
            conn.commit()
            yield conn
        except sqlite3.Error as exc:
            conn.rollback()
            raise JevError("usage_ledger_error", "Could not safely update local usage counters; no additional request will be sent.") from exc
        finally:
            conn.close()

    @staticmethod
    def day() -> str:
        return time.strftime("%Y-%m-%d", time.localtime())

    def reserve(self, count: int, payload_bytes: int) -> str:
        day = self.day()
        with self.db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("INSERT OR IGNORE INTO daily VALUES (?,0,0,0,0)", (day,))
            row = conn.execute("SELECT requests,payload_bytes FROM daily WHERE day=?", (day,)).fetchone()
            if ((self.settings.max_daily_requests and row[0] + count > self.settings.max_daily_requests) or
                    (self.settings.max_daily_payload_bytes and row[1] + payload_bytes > self.settings.max_daily_payload_bytes)):
                raise JevError("daily_limit", "Local daily request/byte cap reached. Review usage and settings.json locally; the MCP tool cannot increase limits.")
            conn.execute("UPDATE daily SET requests=requests+?,payload_bytes=payload_bytes+? WHERE day=?", (count, payload_bytes, day))
            conn.commit()
        return day

    def record_tokens(self, day: str, usage: dict[str, int]) -> bool:
        try:
            with self.db() as conn:
                conn.execute("UPDATE daily SET input_tokens=input_tokens+?,output_tokens=output_tokens+? WHERE day=?",
                             (usage["input_tokens"], usage["output_tokens"], day))
                conn.commit()
            return True
        except (JevError, OSError, sqlite3.Error):
            return False  # Do not discard a paid answer or invite a repeat call.

    def snapshot(self) -> dict[str, Any]:
        path = self.home / "usage.sqlite3"
        if not path.exists():
            row = (0, 0, 0, 0)
        else:
            with self.db() as conn:
                row = conn.execute("SELECT requests,payload_bytes,input_tokens,output_tokens FROM daily WHERE day=?", (self.day(),)).fetchone() or (0, 0, 0, 0)
        return dict(zip(("reserved_requests", "reserved_payload_bytes", "observed_input_tokens", "observed_output_tokens"), row),
                    local_date=self.day(), note="Local caps only; reservations include failures/unused batch slots. Not an account balance or dollar cap.")


class JevClient:
    def __init__(self, home: Path | None = None, *,
                 transport: Callable[[bytes, str, Settings], Any] = post_http,
                 key_loader: Callable[[Path], tuple[str, str]] = load_key):
        self.home = home or home_dir()
        self.transport, self.key_loader = transport, key_loader
        self.gate = threading.Lock()

    def status(self) -> dict[str, Any]:
        settings = Settings.load(self.home)
        try:
            _, source = self.key_loader(self.home)
            ready, error = True, None
        except JevError as exc:
            ready, source, error = False, "none", exc.as_dict()
        result = {"ok": True, "version": VERSION, "network_called": False,
                  "api_key_ready_locally": ready, "api_key_source": source,
                  "credential_validated_with_service": False,
                  "model": settings.model, "endpoint": API_URL,
                  "settings": asdict(settings),
                  "daily_usage": UsageLedger(self.home, settings).snapshot(),
                  "note": "Tool registration/local key readiness does not prove an API call succeeds. External use may consume TypeSafe credits, separately from ChatGPT."}
        if error:
            result["credential_error"] = error
        return result

    def evaluate(self, state: Any, questions: Any, *, dry_run: bool = False,
                 cancel: threading.Event | None = None) -> dict[str, Any]:
        settings = Settings.load(self.home)
        payload, data = build_payload(state, questions, settings)
        if type(dry_run) is not bool:
            raise JevError("invalid_argument", "dry_run must be boolean.")
        if dry_run:
            return {"ok": True, "dry_run": True, "network_called": False,
                    "model": settings.model, "question_count": len(payload["questions"]),
                    "request_bytes": len(data), "estimated_cost": None,
                    "note": "Validated locally only; bytes are not billable tokens. No key or API access required."}
        with self.gate:
            self._check_cancel(cancel)
            key, _ = self.key_loader(self.home)
            ledger = UsageLedger(self.home, settings)
            day = ledger.reserve(1, len(data))
            return self._send(payload, data, key, settings, ledger, day)

    @staticmethod
    def _check_cancel(cancel: threading.Event | None) -> None:
        if cancel and cancel.is_set():
            raise JevError("cancelled", "Call cancelled; no further request will be started.")

    def _send(self, payload: dict[str, Any], data: bytes, key: str, settings: Settings,
              ledger: UsageLedger, day: str) -> dict[str, Any]:
        start = time.perf_counter()
        result = validate_response(self.transport(data, key, settings), payload["questions"])
        tracked = ledger.record_tokens(day, result["usage"])
        return {"ok": True, "dry_run": False, "network_called": True, **result,
                "elapsed_ms": round((time.perf_counter() - start) * 1000, 1),
                "local_token_accounting_updated": tracked,
                "note": "Probabilities/confidence are model judgments, not guaranteed correctness. No automatic action was taken."}

    def batch(self, items: Any, questions: Any, *, dry_run: bool = False,
              cancel: threading.Event | None = None) -> dict[str, Any]:
        settings = Settings.load(self.home)
        if type(dry_run) is not bool:
            raise JevError("invalid_argument", "dry_run must be boolean.")
        if not isinstance(items, list) or not 1 <= len(items) <= settings.max_batch_items:
            raise JevError("invalid_argument", f"items must contain 1..{settings.max_batch_items} records.")
        prepared, seen = [], set()
        for item in items:
            if not isinstance(item, dict) or set(item) != {"id", "state"}:
                raise JevError("invalid_argument", "Each batch item must contain only id and state.")
            identifier = item["id"]
            if not isinstance(identifier, str) or not identifier.strip() or identifier in seen:
                raise JevError("invalid_argument", "Batch ids must be unique nonblank strings.")
            seen.add(identifier)
            payload, data = build_payload(item["state"], questions, settings)
            prepared.append((identifier, payload, data))
        # Full validation happens before the first paid request.
        if dry_run:
            return {"ok": True, "dry_run": True, "network_called": False,
                    "api_requests": len(prepared),
                    "total_request_bytes": sum(len(d) for _, _, d in prepared),
                    "items": [{"id": i, "request_bytes": len(d)} for i, _, d in prepared],
                    "note": "Separate state per request. Shared questions do not imply a discounted batch API."}
        with self.gate:
            self._check_cancel(cancel)
            key, _ = self.key_loader(self.home)
            ledger = UsageLedger(self.home, settings)
            day = ledger.reserve(len(prepared), sum(len(d) for _, _, d in prepared))
            results, attempted = [], 0
            deadline = time.monotonic() + settings.max_batch_seconds if settings.max_batch_seconds else float("inf")
            for identifier, payload, data in prepared:
                if (cancel and cancel.is_set()) or time.monotonic() >= deadline:
                    break
                attempted += 1
                try:
                    result = self._send(payload, data, key, settings, ledger, day)
                    results.append({"id": identifier, **result})
                except JevError as exc:
                    results.append({"id": identifier, "ok": False, "error": exc.as_dict()})
                    break  # Stop on any error, especially auth, quota and overload.
            not_started = [i for i, _, _ in prepared[attempted:]]
            return {"ok": not not_started and all(r["ok"] for r in results), "dry_run": False,
                    "network_called": attempted > 0, "requests_attempted": attempted,
                    "results": results, "not_started_ids": not_started,
                    "note": "Sequential, bounded requests; stops on first error/cancel/deadline. Earlier successful requests may have been charged. Unused reservations remain in the conservative local counter."}
