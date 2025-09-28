#!/usr/bin/env python3
"""Sign JSON payloads with an HMAC-SHA256 development key."""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import hmac
import json
import os
from datetime import timezone
from pathlib import Path

if hasattr(_dt, "UTC"):
    UTC = _dt.UTC  # type: ignore[attr-defined]
else:  # Python 3.10 fallback
    UTC = timezone.utc  # noqa: UP017


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Sign JSON payload with dev key")
    parser.add_argument("path", help="JSON file to sign")
    parser.add_argument("--key", dest="key", help="Signing key override")
    args = parser.parse_args(argv)

    path = args.path
    kid = os.getenv("SOT_KID", "dev")
    key = args.key or os.getenv("SOT_DEV_SIGNING_KEY")
    if not key:
        raise SystemExit("SOT_DEV_SIGNING_KEY missing")

    payload = Path(path).read_bytes()
    payload_sha256 = hashlib.sha256(payload).hexdigest()
    signature = hmac.new(key.encode(), payload, hashlib.sha256).hexdigest()
    created_at = _dt.datetime.now(UTC).isoformat().replace("+00:00", "Z")
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
