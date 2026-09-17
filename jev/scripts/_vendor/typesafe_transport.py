"""Thin adapter to the upstream TypeSafe SDK; no alternate HTTP implementation."""
from __future__ import annotations
import importlib.metadata
from typing import Any


def sdk_status() -> dict[str, Any]:
    try:
        version = importlib.metadata.version("typesafe-sdk")
    except importlib.metadata.PackageNotFoundError:
        version = None
    return {"distribution": "typesafe-sdk", "installed_version": version,
            "installed": version is not None, "import_verified": False}


def require_sdk():
    from jev_core import JevError
    try:
        import httpx2
        import typesafe_sdk
    except ImportError:
        raise JevError("missing_typesafe_sdk",
                       "Install this project's declared TypeSafe SDK dependency in the executing Python environment. No API request was sent.") from None
    return typesafe_sdk, httpx2


def send(data: bytes, key: str, settings, *, http_transport=None) -> Any:
    """Use only public SDK APIs. http_transport is a Python test injection, not an MCP input."""
    from jev_core import JevError, strict_json
    sdk, http = require_sdk()
    payload = strict_json(data)

    class LimitedStream(http.SyncByteStream):
        def __init__(self, inner):
            self.inner = inner
        def __iter__(self):
            size = 0
            for chunk in self.inner:
                size += len(chunk)
                if size > settings.max_response_bytes:
                    raise JevError("response_too_large", "TypeSafe response exceeded the local size limit.", ambiguous_charge=True)
                yield chunk
        def close(self):
            self.inner.close()

    def cap_response(response):
        # The hook runs before SDK buffering/parsing. Count streamed bytes and
        # also check decoded content below (servers may still compress responses).
        response.stream = LimitedStream(response.stream)

    try:
        with http.Client(timeout=settings.request_timeout_seconds, verify=True,
                         follow_redirects=False, trust_env=settings.trust_environment,
                         transport=http_transport, event_hooks={"response": [cap_response]}) as http_client:
            with sdk.TypeSafeClient(api_key=key, model=settings.model,
                                    base_url="https://api.typesafe.ai",
                                    retry=sdk.RetryPolicy(max_retries=0),
                                    http_client=http_client,
                                    headers={"Accept-Encoding": "identity"}) as client:
                result = client.system_one(state=payload["state"], questions=payload["questions"])
                content = result.raw_http_response.content
                if len(content) > settings.max_response_bytes:
                    raise JevError("response_too_large", "TypeSafe response exceeded the local size limit.", ambiguous_charge=True)
                return strict_json(content)
    except JevError:
        raise
    except sdk.TypeSafeAPITimeoutError:
        raise JevError("timeout", "TypeSafe timed out; it may already have processed the request. No automatic retry.", ambiguous_charge=True) from None
    except sdk.TypeSafeAPIResponseValidationError:
        raise JevError("invalid_api_response", "The official SDK could not parse the TypeSafe response. No result was fabricated.", ambiguous_charge=True) from None
    except sdk.TypeSafeAPIConnectionError:
        raise JevError("network_error", "The TypeSafe SDK could not complete the request. No automatic retry.", ambiguous_charge=True) from None
    except sdk.TypeSafeAPIError as exc:
        code = exc.status
        raise JevError("http_error", "TypeSafe returned an HTTP error; private response content is omitted. Check account access, request format or service status.",
                       status=code, ambiguous_charge=code >= 500) from None
    except sdk.TypeSafeError:
        raise JevError("typesafe_sdk_error", "The TypeSafe SDK rejected the operation. Inspect the supported SDK contract without exposing private payloads.", ambiguous_charge=True) from None
    except (ValueError, TypeError, UnicodeError, OSError):
        raise JevError("sdk_operation_failed", "The SDK operation did not finish. No raw payload or secret is displayed; do not retry blindly.", ambiguous_charge=True) from None
