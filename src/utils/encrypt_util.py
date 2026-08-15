"""Fernet encrypt/decrypt for sigs."""

from __future__ import annotations

import base64
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from src.config.bindings.keys import SIG_KEYS

_XOR_KEY = b"Djajsl09!2"


def secret_key_path(key_id: str) -> Path:
    """Filesystem path for the Fernet key file belonging to ``key_id``."""
    entry = SIG_KEYS.get(key_id, {})
    key_file = entry.get("key_file", "").strip()
    if not key_file:
        raise ValueError("No key_file configured.")
    return Path(key_file)


def encrypted_value(key_id: str) -> str:
    """Encrypted sig blob for ``key_id``, or empty string."""
    return SIG_KEYS.get(key_id, {}).get("encrypted", "").strip()


def _resolve_key_path(key_id: str) -> Path:
    path = secret_key_path(key_id)
    if path.is_file():
        return path
    raise FileNotFoundError(f"Missing key file")


def generate_secret_key(key_id: str, path: Path | None = None) -> bytes:
    """Create and write a Fernet key file for ``key_id``."""
    path = path or secret_key_path(key_id)
    key = Fernet.generate_key()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(key)
    except PermissionError as e:
        raise PermissionError(
            f"Cannot write {path}. Create the key file with appropriate permissions."
        ) from e
    return key


def encrypt_sig(
    plain: str,
    key_id: str,
    *,
    key_path: Path | None = None,
) -> bytes:
    """Fernet encrypt plain sig."""
    path = key_path or _resolve_key_path(key_id)
    cipher = Fernet(path.read_bytes())
    return cipher.encrypt(plain.strip().encode())


def decrypt_sig(key_id: str, encrypted: str | None = None) -> str:
    """Decrypt sig."""
    blob = (encrypted if encrypted is not None else encrypted_value(key_id)).strip()
    if not blob:
        raise ValueError(f"No encrypted sig")
    cipher = Fernet(_resolve_key_path(key_id).read_bytes())
    try:
        plain = cipher.decrypt(blob.encode()).decode()
        return xor_decrypt(plain)
    except InvalidToken as e:
        raise ValueError(
            f"Failed to decrypt sig (wrong key file?)"
        ) from e


def _xor_bytes(data: bytes, key: bytes) -> bytes:
    if not key:
        raise ValueError("key is empty")
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def xor_encrypt(private_key: str) -> str:
    """XOR encrypt private key; returns base64 string."""
    encrypted = _xor_bytes(private_key.strip().encode(), _XOR_KEY)
    return base64.b64encode(encrypted).decode()


def xor_decrypt(encrypted: str) -> str:
    """XOR decrypt base64 string back to private key."""
    data = base64.b64decode(encrypted.strip())
    return _xor_bytes(data, _XOR_KEY).decode()
