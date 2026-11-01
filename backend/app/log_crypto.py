"""Encryption for personal data in the question log.

Customer questions are encrypted with Fernet (AES-128-CBC with an HMAC-SHA256 check)
before they reach SQLite, and client IPs are replaced by a keyed one-way hash. A copy of
app.db, or a backup of it, then shows neither what customers asked nor who asked it.

The key comes from LOG_ENCRYPTION_KEY. Several comma-separated keys allow rotation: the
first one encrypts, all of them decrypt. Without the variable, a key is generated in the
data directory. That protects copies of the database file, but not a copy of the whole
data folder, so set the variable for any real deployment."""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from .config import config

log = logging.getLogger("log_crypto")

PREFIX = "enc:v1:"   # marks an encrypted value; rows from before encryption have no prefix
HASH_PREFIX = "h:"   # marks a hashed client id
UNREADABLE = "[unreadable: encrypted with a different key]"
_KEY_FILE = config.data_dir / "log_encryption.key"
_GENERATE_HINT = ('Generate one with: python -c "from cryptography.fernet import Fernet; '
                  'print(Fernet.generate_key().decode())"')


def _load_or_create_key_file() -> bytes:
    try:
        with open(_KEY_FILE, "xb") as f:  # "x" never overwrites an existing key
            f.write(Fernet.generate_key())
        try:
            os.chmod(_KEY_FILE, 0o600)
        except OSError:
            pass
        log.warning("LOG_ENCRYPTION_KEY is not set, so a key was generated at %s. "
                    "Set the variable to keep the key away from the data.", _KEY_FILE)
    except FileExistsError:
        pass
    return _KEY_FILE.read_bytes().strip()


@lru_cache(maxsize=1)
def _keys() -> tuple[tuple[bytes, ...], str]:
    if config.log_encryption_key.strip():
        keys = tuple(k.strip().encode() for k in config.log_encryption_key.split(",") if k.strip())
        return keys, "env"
    return (_load_or_create_key_file(),), "file"


@lru_cache(maxsize=1)
def _fernet() -> MultiFernet:
    keys, _ = _keys()
    try:
        return MultiFernet([Fernet(k) for k in keys])
    except (ValueError, TypeError) as e:
        raise RuntimeError("LOG_ENCRYPTION_KEY must be one or more Fernet keys separated by commas. "
                           + _GENERATE_HINT) from e


def check() -> None:
    """Fail at startup, not on the first chat message, if the key is unusable."""
    _fernet()


def key_source() -> str:
    """'env' when the key comes from LOG_ENCRYPTION_KEY, 'file' when it was generated."""
    return _keys()[1]


def encrypt(text: str) -> str:
    return PREFIX + _fernet().encrypt(text.encode("utf-8")).decode("ascii")


def decrypt(value: str | None) -> str | None:
    if value is None or not value.startswith(PREFIX):
        return value  # plaintext row from before encryption was added
    try:
        return _fernet().decrypt(value[len(PREFIX):].encode("ascii")).decode("utf-8")
    except InvalidToken:
        return UNREADABLE


def pseudonymize(client: str | None) -> str | None:
    """Keyed one-way hash of the client IP. The log can still tell repeat visitors
    apart, but the IP itself can't be read back, not even by an admin."""
    if not client or client.startswith(HASH_PREFIX):
        return client
    subkey = hashlib.sha256(b"scopeguard-client-id:" + _keys()[0][0]).digest()
    return HASH_PREFIX + hmac.new(subkey, client.encode("utf-8"), hashlib.sha256).hexdigest()[:16]
