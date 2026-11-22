"""Configuration module - password hashing, reversible secret encryption, paths."""

import os
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.fernet import Fernet

password_hasher = PasswordHasher()

APP_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_data")
KEY_FILE = os.path.join(APP_DATA_DIR, ".secret.key")


def _load_or_create_key():
    os.makedirs(APP_DATA_DIR, exist_ok=True)
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as f:
            return f.read()
    key = Fernet.generate_key()
    with open(KEY_FILE, "wb") as f:
        f.write(key)
    # restrict perms best-effort
    try:
        os.chmod(KEY_FILE, 0o600)
    except Exception:
        pass
    return key


_FERNET = Fernet(_load_or_create_key())


def hash_password(plain_password: str) -> str:
    """Hash a password using Argon2. Returns the hash string (one-way, for app login)."""
    return password_hasher.hash(plain_password)


def verify_password(plain_password: str, stored_hash: str) -> bool:
    try:
        password_hasher.verify(stored_hash, plain_password)
        return True
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def encrypt_secret(plain: str) -> str:
    """Reversibly encrypt a secret (DB password, SP client secret) for storage."""
    if plain is None:
        return ""
    return _FERNET.encrypt(plain.encode()).decode()


def decrypt_secret(stored: str) -> str:
    if not stored:
        return ""
    try:
        return _FERNET.decrypt(stored.encode()).decode()
    except Exception:
        return ""
