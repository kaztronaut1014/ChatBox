from dataclasses import dataclass


@dataclass(frozen=True)
class Message:
    id: int
    conversation_id: str
    sender_id: str
    recipient_id: str
    ciphertext: bytes
    nonce: bytes
    salt: bytes
    aad: bytes
    key_version: int
    created_at: str


@dataclass(frozen=True)
class PublicKey:
    user_id: str
    public_key: bytes
    key_version: int