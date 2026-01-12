"""Encryption service for securing sensitive data like API keys."""

import base64

from cryptography.fernet import Fernet

from app.config import get_settings


def _get_fernet() -> Fernet:
    """Get Fernet cipher using the app's secret key."""
    settings = get_settings()
    # Derive a valid Fernet key from the secret key
    # Fernet requires a 32-byte base64-encoded key
    key_bytes = settings.secret_key.encode("utf-8")
    # Pad or truncate to 32 bytes
    key_bytes = (key_bytes * 2)[:32]
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def encrypt_value(value: str) -> str:
    """Encrypt a string value and return base64-encoded ciphertext."""
    fernet = _get_fernet()
    encrypted = fernet.encrypt(value.encode("utf-8"))
    return encrypted.decode("utf-8")


def decrypt_value(encrypted_value: str) -> str:
    """Decrypt a base64-encoded ciphertext and return the original string."""
    fernet = _get_fernet()
    decrypted = fernet.decrypt(encrypted_value.encode("utf-8"))
    return decrypted.decode("utf-8")
