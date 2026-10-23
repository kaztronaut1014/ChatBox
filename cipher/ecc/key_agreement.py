from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


def generate_keypair():
    """Tạo cặp khóa ECC P-256. Khóa riêng phải ở lại client."""
    private_key = ec.generate_private_key(ec.SECP256R1())

    public_key_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    return private_key, public_key_bytes


def load_public_key(public_key_bytes: bytes):
    """Đọc và kiểm tra khóa công khai của đối phương."""
    public_key = serialization.load_der_public_key(public_key_bytes)

    if not isinstance(public_key, ec.EllipticCurvePublicKey):
        raise ValueError("Khóa nhận được không phải khóa ECC")

    if not isinstance(public_key.curve, ec.SECP256R1):
        raise ValueError("Đường cong ECC không được hỗ trợ")

    return public_key


def create_shared_secret(private_key, peer_public_key_bytes: bytes) -> bytes:
    """Tạo bí mật ECDH. Không dùng trực tiếp giá trị này làm khóa AES."""
    peer_public_key = load_public_key(peer_public_key_bytes)
    return private_key.exchange(ec.ECDH(), peer_public_key)