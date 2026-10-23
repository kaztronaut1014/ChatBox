import base64
import os

import requests

from cipher.ecc.key_agreement import create_shared_secret, generate_keypair
from cipher.encryption import decrypt_message, derive_key, encrypt_message


SERVER_URL = "http://127.0.0.1:8000"
CONVERSATION_ID = "alice-bob"


def to_b64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def from_b64(value: str) -> bytes:
    return base64.b64decode(value, validate=True)


def main() -> None:
    # Mô phỏng Alice và Bob tạo khóa ở phía client.
    # Demo này giữ private key trong bộ nhớ, chưa lưu bền giữa các lần chạy.
    alice_private, alice_public = generate_keypair()
    bob_private, bob_public = generate_keypair()

    # Đăng ký khóa công khai lên server.
    requests.put(
        f"{SERVER_URL}/users/alice/public-key",
        json={"public_key_b64": to_b64(alice_public), "key_version": 1},
        timeout=5,
    ).raise_for_status()

    requests.put(
        f"{SERVER_URL}/users/bob/public-key",
        json={"public_key_b64": to_b64(bob_public), "key_version": 1},
        timeout=5,
    ).raise_for_status()

    # Alice lấy public key của Bob từ server.
    bob_response = requests.get(
        f"{SERVER_URL}/users/bob/public-key",
        timeout=5,
    )
    bob_response.raise_for_status()
    bob_public_from_server = from_b64(bob_response.json()["public_key_b64"])

    # Hai client tự tính bí mật ECDH.
    alice_secret = create_shared_secret(alice_private, bob_public_from_server)
    bob_secret = create_shared_secret(bob_private, alice_public)
    assert alice_secret == bob_secret

    # Salt được gửi cùng tin nhắn; nó không cần giữ bí mật.
    salt = os.urandom(16)
    alice_key = derive_key(alice_secret, salt, CONVERSATION_ID)

    aad = f"{CONVERSATION_ID}|alice|bob|v1".encode("utf-8")
    nonce, ciphertext = encrypt_message(
        alice_key,
        "Xin chào Bob 👋",
        aad,
    )

    # Gửi gói mã hóa lên server. Khóa riêng và khóa AES không được gửi.
    post_response = requests.post(
        f"{SERVER_URL}/messages",
        json={
            "conversation_id": CONVERSATION_ID,
            "sender_id": "alice",
            "recipient_id": "bob",
            "ciphertext_b64": to_b64(ciphertext),
            "nonce_b64": to_b64(nonce),
            "salt_b64": to_b64(salt),
            "aad_b64": to_b64(aad),
            "key_version": 1,
        },
        timeout=5,
    )
    post_response.raise_for_status()
    print("Đã lưu tin nhắn:", post_response.json()["message_id"])

    # Bob tải tin nhắn và giải mã ở phía client.
    messages_response = requests.get(
        f"{SERVER_URL}/conversations/{CONVERSATION_ID}/messages",
        timeout=5,
    )
    messages_response.raise_for_status()
    stored_message = messages_response.json()[-1]

    bob_key = derive_key(
        bob_secret,
        from_b64(stored_message["salt_b64"]),
        stored_message["conversation_id"],
    )

    plaintext = decrypt_message(
        bob_key,
        from_b64(stored_message["nonce_b64"]),
        from_b64(stored_message["ciphertext_b64"]),
        from_b64(stored_message["aad_b64"]),
    )

    print("Bob giải mã được:", plaintext)


if __name__ == "__main__":
    main()