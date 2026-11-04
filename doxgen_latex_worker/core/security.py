"""Request authentication and input checks for the worker."""

import hmac
import os

STORAGE_ROOT = os.path.realpath("/storage")

# The API sends this token in "Authorization: Bearer <token>". The worker does not start without it.
WORKER_TOKEN = os.getenv("WORKER_TOKEN", "").strip()
if not WORKER_TOKEN:
    raise RuntimeError("Set WORKER_TOKEN. The worker refuses requests without a shared token.")


class InvalidRequest(Exception):
    """The request payload is not acceptable."""


def is_authorized(scope) -> bool:
    for name, value in scope.get("headers", []):
        if name.lower() == b"authorization":
            expected = f"Bearer {WORKER_TOKEN}".encode()
            return hmac.compare_digest(value, expected)
    return False


def storage_path(relative_path: str) -> str:
    """Return the absolute path of a file in /storage. Refuse a path that goes out of /storage."""
    if not isinstance(relative_path, str) or not relative_path:
        raise InvalidRequest("A storage path is required.")
    path = os.path.realpath(os.path.join(STORAGE_ROOT, relative_path.lstrip("/")))
    if os.path.commonpath([path, STORAGE_ROOT]) != STORAGE_ROOT or path == STORAGE_ROOT:
        raise InvalidRequest("The path is outside the storage folder.")
    return path

