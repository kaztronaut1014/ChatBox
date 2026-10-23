import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


def derive_key(
    shared_secret: bytes,
    salt: bytes,
    conversation_id: str,
) -> bytes:
    """Dẫn xuất khóa AES-256 từ bí mật ECDH bằng HKDF."""
    info = f"chatbox-demo-v1:{conversation_id}".encode("utf-8")

    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=info,
    ).derive(shared_secret)


def encrypt_message(
    key: bytes,
    plaintext: str,
    aad: bytes,
) -> tuple[bytes, bytes]:
    """Trả về nonce và ciphertext đã gắn authentication tag."""
    nonce = os.urandom(12)

    ciphertext_and_tag = AESGCM(key).encrypt(
        nonce,
        plaintext.encode("utf-8"),
        aad,
    )

    return nonce, ciphertext_and_tag


def decrypt_message(
    key: bytes,
    nonce: bytes,
    ciphertext_and_tag: bytes,
    aad: bytes,
) -> str:
    """Giải mã và xác minh tag; dữ liệu sai sẽ bị từ chối."""
    plaintext = AESGCM(key).decrypt(
        nonce,
        ciphertext_and_tag,
        aad,
    )

    return plaintext.decode("utf-8")