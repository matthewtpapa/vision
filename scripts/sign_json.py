#!/usr/bin/env python3
"""Sign JSON payloads with an HMAC-SHA256 development key."""

from __future__ import annotations

import datetime as _dt
import hashlib
import hmac
import json
import os
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: sign_json.py <path>")

    path = sys.argv[1]
    kid = os.getenv("SOT_KID", "dev")
    key = os.getenv("SOT_DEV_SIGNING_KEY")
    if not key:
        raise SystemExit("SOT_DEV_SIGNING_KEY missing")

    payload = Path(path).read_bytes()
    payload_sha256 = hashlib.sha256(payload).hexdigest()
    signature = hmac.new(key.encode(), payload, hashlib.sha256).hexdigest()
    created_at = _dt.datetime.now(_dt.UTC).isoformat().replace("+00:00", "Z")
    document = {
        "alg": "HMAC-SHA256",
        "kid": kid,
        "created_at": created_at,
        "payload_sha256": payload_sha256,
        "sig": signature,
    }
    Path(path + ".sig").write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print("ok")


if __name__ == "__main__":
    main()
