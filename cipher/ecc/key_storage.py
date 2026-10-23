"""Local storage for encrypted ECC private keys used by the demo client."""

import hashlib
import os
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt


_MAGIC = b"CBXKEY01"
_SALT_SIZE = 16
_NONCE_SIZE = 12


def _derive_file_key(password: str, salt: bytes) -> bytes:
    return Scrypt(salt=salt, length=32, n=2**15, r=8, p=1).derive(
        password.encode("utf-8")
    )


def _aad(username: str) -> bytes:
    return b"ChatBox local private key v1:" + username.strip().lower().encode("utf-8")


def key_directory() -> Path:
    configured = os.getenv("CHATBOX_KEY_DIR")
    return Path(configured).expanduser() if configured else Path.home() / ".chatbox" / "keys"


def key_path(username: str) -> Path:
    user_key = hashlib.sha256(username.strip().lower().encode("utf-8")).hexdigest()
    return key_directory() / f"{user_key}.key"


def public_key_bytes(private_key: ec.EllipticCurvePrivateKey) -> bytes:
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def save_private_key(
    username: str,
    password: str,
    private_key: ec.EllipticCurvePrivateKey,
) -> Path:
    """Encrypt the private key with a password-derived key before writing it."""
    if not password:
        raise ValueError("Password không được để trống")

    destination = key_path(username)
    destination.parent.mkdir(parents=True, exist_ok=True)
    salt = os.urandom(_SALT_SIZE)
    nonce = os.urandom(_NONCE_SIZE)
    private_der = private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    file_key = _derive_file_key(password, salt)
    encrypted = AESGCM(file_key).encrypt(nonce, private_der, _aad(username))
    encrypted_file = _MAGIC + salt + nonce + encrypted

    temporary = destination.with_suffix(".key.tmp")
    temporary.write_bytes(encrypted_file)
    try:
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def load_private_key(username: str, password: str) -> ec.EllipticCurvePrivateKey:
    """Load and decrypt the local key; wrong password raises ValueError."""
    encrypted_file = key_path(username).read_bytes()
    header_size = len(_MAGIC) + _SALT_SIZE + _NONCE_SIZE
    if len(encrypted_file) <= header_size or not encrypted_file.startswith(_MAGIC):
        raise ValueError("File khóa có định dạng không hợp lệ")

    salt_start = len(_MAGIC)
    nonce_start = salt_start + _SALT_SIZE
    salt = encrypted_file[salt_start:nonce_start]
    nonce = encrypted_file[nonce_start:header_size]
    ciphertext = encrypted_file[header_size:]
    file_key = _derive_file_key(password, salt)
    try:
        private_der = AESGCM(file_key).decrypt(
            nonce,
            ciphertext,
            _aad(username),
        )
    except InvalidTag as exc:
        raise ValueError("Password sai hoặc file khóa đã bị thay đổi") from exc

    private_key = serialization.load_der_private_key(private_der, password=None)
    if not isinstance(private_key, ec.EllipticCurvePrivateKey):
        raise ValueError("File khóa không chứa khóa ECC")
    if not isinstance(private_key.curve, ec.SECP256R1):
        raise ValueError("File khóa không dùng đường cong P-256")
    return private_key
