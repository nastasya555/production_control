from __future__ import annotations

import hashlib
import hmac


def sign_payload(secret_key: str, body: bytes) -> str:
    signature = hmac.new(secret_key.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={signature}"



