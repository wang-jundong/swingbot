"""CLI entry point to generate a Fernet key file and encrypted sig."""

from __future__ import annotations

import sys

from src.config.bindings.keys import SIG_KEYS
from src.utils.encrypt_util import encrypt_sig, generate_secret_key, secret_key_path


KEY_ID = "solana"


def main() -> int:
    plain = SIG_KEYS.get(KEY_ID, {}).get("plain", "").strip()
    if not plain:
        print(f"Set SIG_KEYS[{KEY_ID!r}]['plain'] in keys.py", file=sys.stderr)
        return 1

    key_path = secret_key_path(KEY_ID)
    if not key_path.is_file():
        generate_secret_key(KEY_ID, path=key_path)
        print(f"Wrote {key_path}")

    encrypted = encrypt_sig(plain, KEY_ID, key_path=key_path).decode()
    print(f"SIG_KEYS[{KEY_ID!r}]['encrypted'] = {encrypted!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
