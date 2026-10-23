import base64
import binascii
import secrets
from typing import Annotated
from uuid import UUID

import pyodbc
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field

from cipher.ecc.key_agreement import load_public_key
from database.db import connect, initialize_database
from database.repositories import (
    add_message,
    create_user,
    get_or_create_conversation,
    get_messages,
    get_public_key,
    is_conversation_member,
    list_conversations,
    list_users,
    replace_public_key,
    verify_login,
)


app = FastAPI(title="ChatBox API")

# Demo: token được giữ trong bộ nhớ và mất khi server khởi động lại.
# Dùng session store bền vững nếu triển khai thật.
active_tokens: dict[str, str] = {}


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=1)
    public_key_b64: str


class LoginRequest(BaseModel):
    username: str
    password: str


class ConversationRequest(BaseModel):
    peer_username: str = Field(min_length=3, max_length=50)


class MessageRequest(BaseModel):
    conversation_id: str
    recipient_username: str
    ciphertext_b64: str
    nonce_b64: str
    salt_b64: str
    aad_b64: str
    key_version: int = Field(default=1, ge=1)


class PublicKeyUpdateRequest(BaseModel):
    public_key_b64: str


def decode_b64(value: str) -> bytes:
    try:
        return base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=400, detail="Base64 không hợp lệ")


def encode_b64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def current_user(
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Cần đăng nhập")

    token = authorization.removeprefix("Bearer ").strip()
    username = active_tokens.get(token)

    if username is None:
        raise HTTPException(status_code=401, detail="Token không hợp lệ hoặc đã hết hạn")

    return username




@app.on_event("startup")
def startup() -> None:
    initialize_database()


@app.post("/auth/register")
def register(request: RegisterRequest):
    username = request.username.strip().lower()
    public_key = decode_b64(request.public_key_b64)

    try:
        with connect() as connection:
            create_user(connection, username, request.password, public_key)
    except pyodbc.IntegrityError:
        raise HTTPException(status_code=409, detail="Username đã tồn tại")

    return {"status": "ok", "username": username}


@app.post("/auth/login")
def login(request: LoginRequest):
    username = request.username.strip().lower()

    with connect() as connection:
        valid = verify_login(connection, username, request.password)

    if not valid:
        raise HTTPException(status_code=401, detail="Username hoặc password không đúng")

    token = secrets.token_urlsafe(32)
    active_tokens[token] = username

    return {"access_token": token, "token_type": "bearer", "username": username}


@app.post("/auth/logout")
def logout(username: Annotated[str, Depends(current_user)],
           authorization: Annotated[str, Header()]):
    token = authorization.removeprefix("Bearer ").strip()
    active_tokens.pop(token, None)
    return {"status": "ok"}


@app.get("/users/{username}/public-key")
def fetch_public_key(
    username: str,
    requester: Annotated[str, Depends(current_user)],
):
    with connect() as connection:
        result = get_public_key(connection, username.strip().lower())

    if result is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy user")

    public_key, key_version = result
    return {
        "username": username,
        "public_key_b64": encode_b64(public_key),
        "key_version": key_version,
    }


@app.get("/users")
def fetch_users(username: Annotated[str, Depends(current_user)]):
    """Return usernames available to start a direct conversation with."""
    with connect() as connection:
        users = list_users(connection, username)
    return {"users": users}


@app.get("/conversations")
def fetch_conversations(username: Annotated[str, Depends(current_user)]):
    """Return this user's saved chats, including chats with offline users."""
    with connect() as connection:
        conversations = list_conversations(connection, username)
    return {"conversations": conversations}


@app.put("/users/me/public-key")
def replace_my_public_key(
    request: PublicKeyUpdateRequest,
    username: Annotated[str, Depends(current_user)],
):
    """Rotate a user's key after password authentication when a private key is lost."""
    public_key = decode_b64(request.public_key_b64)
    try:
        load_public_key(public_key)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Public key ECC không hợp lệ")

    with connect() as connection:
        key_version = replace_public_key(connection, username, public_key)

    if key_version is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy user")

    return {"status": "ok", "key_version": key_version}


@app.post("/conversations")
def new_conversation(
    request: ConversationRequest,
    username: Annotated[str, Depends(current_user)],
):
    peer = request.peer_username.strip().lower()

    if peer == username:
        raise HTTPException(status_code=400, detail="Không thể tạo hội thoại với chính mình")

    with connect() as connection:
        if get_public_key(connection, peer) is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy user nhận")

        conversation_id = get_or_create_conversation(connection, username, peer)

    return {"conversation_id": conversation_id}


@app.post("/messages")
def post_message(
    request: MessageRequest,
    username: Annotated[str, Depends(current_user)],
):
    try:
        conversation_id = str(UUID(request.conversation_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="conversation_id không hợp lệ")

    recipient = request.recipient_username.strip().lower()
    ciphertext = decode_b64(request.ciphertext_b64)
    nonce = decode_b64(request.nonce_b64)
    salt = decode_b64(request.salt_b64)
    aad = decode_b64(request.aad_b64)

    if len(nonce) != 12:
        raise HTTPException(status_code=400, detail="Nonce phải dài 12 byte")

    with connect() as connection:
        sender_is_member = is_conversation_member(connection, conversation_id, username)
        recipient_is_member = is_conversation_member(connection, conversation_id, recipient)

        if not sender_is_member or not recipient_is_member:
            raise HTTPException(status_code=403, detail="User không thuộc hội thoại này")

        message_id = add_message(
            connection,
            conversation_id,
            username,
            recipient,
            ciphertext,
            nonce,
            salt,
            aad,
            request.key_version,
        )

    return {"status": "ok", "message_id": message_id}


@app.get("/conversations/{conversation_id}/messages")
def fetch_messages(
    conversation_id: str,
    username: Annotated[str, Depends(current_user)],
    after_id: int = Query(default=0, ge=0),
):
    try:
        conversation_id = str(UUID(conversation_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="conversation_id không hợp lệ")

    with connect() as connection:
        if not is_conversation_member(connection, conversation_id, username):
            raise HTTPException(status_code=403, detail="Không có quyền đọc hội thoại")

        messages = get_messages(connection, conversation_id, after_id)

    return [
        {
            **{k: v for k, v in message.items()
               if k not in {"ciphertext", "nonce", "salt", "aad"}},
            "ciphertext_b64": encode_b64(message["ciphertext"]),
            "nonce_b64": encode_b64(message["nonce"]),
            "salt_b64": encode_b64(message["salt"]),
            "aad_b64": encode_b64(message["aad"]),
        }
        for message in messages
    ]
