"""Process-local write-only credentials; persisted configuration contains references only."""

from __future__ import annotations

import os
import re
from threading import RLock
from uuid import uuid4

SESSION_PREFIX = "BENCH_AGENTS_SESSION_"
_SESSION_REFERENCE = re.compile(r"BENCH_AGENTS_SESSION_[0-9a-f]{32}\Z")
_keys: dict[str, str] = {}
# A process may still be draining output from a request that used a rotated or
# deleted credential. Keep its masking value for the rest of this process only.
_redaction_history: set[str] = set()
_lock = RLock()


def is_session_reference(reference: str | None) -> bool:
    return bool(reference and _SESSION_REFERENCE.fullmatch(reference))


def remember_key(value: str, reference: str | None = None) -> str:
    """Remember a secret without writing the environment or any file."""
    if not isinstance(value, str) or not 1 <= len(value) <= 8192:
        raise ValueError("API key must contain between 1 and 8192 characters")
    if reference is not None and not is_session_reference(reference):
        raise ValueError("Only a generated session credential reference may be updated")
    reference = reference or SESSION_PREFIX + uuid4().hex
    with _lock:
        _keys[reference] = value
        _redaction_history.add(value)
    return reference


def get_key(reference: str | None) -> str | None:
    if not reference:
        return None
    # Session references never fall back to an environment variable after restart.
    if reference.startswith(SESSION_PREFIX):
        with _lock:
            return _keys.get(reference)
    return os.environ.get(reference)


def forget_key(reference: str | None) -> None:
    if reference is None:
        return
    with _lock:
        _keys.pop(reference, None)


def secret_values() -> tuple[str, ...]:
    """All values seen by this process, including retired keys, for masking only."""
    with _lock:
        return tuple(_redaction_history)


def missing_key_message(reference: str) -> str:
    if reference.startswith(SESSION_PREFIX):
        return "Session credential is unavailable; re-enter the API key after a backend restart"
    return f"Credential environment variable {reference} is unset"
