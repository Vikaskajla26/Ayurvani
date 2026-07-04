import os
import time
import json
import hmac
import hashlib
import base64


def _secret():
    return os.environ.get("ADMIN_TOKEN_SECRET", "").encode("utf-8")


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _b64d(s: str) -> bytes:
    padded = s + "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(padded)


def create_token(role="ADMIN", ttl_seconds=6 * 3600):
    """Creates a signed, time-limited session token. Raises if no secret is configured."""
    secret = _secret()
    if not secret:
        raise RuntimeError("ADMIN_TOKEN_SECRET not configured")

    payload = {"role": role, "exp": int(time.time()) + ttl_seconds}
    payload_b64 = _b64e(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    sig = hmac.new(secret, payload_b64.encode("utf-8"), hashlib.sha256).digest()
    return f"{payload_b64}.{_b64e(sig)}"


def verify_token(token: str) -> bool:
    """Verifies signature + expiry. Returns False on any problem (never raises)."""
    secret = _secret()
    if not secret or not token or "." not in token:
        return False

    payload_b64, sig_b64 = token.split(".", 1)
    expected_sig = hmac.new(secret, payload_b64.encode("utf-8"), hashlib.sha256).digest()

    if not hmac.compare_digest(sig_b64, _b64e(expected_sig)):
        return False

    try:
        payload = json.loads(_b64d(payload_b64))
    except Exception:
        return False

    return payload.get("exp", 0) >= time.time()
