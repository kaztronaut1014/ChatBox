import base64
import html
import os
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import requests
import streamlit as st

from cipher.ecc.key_agreement import create_shared_secret, generate_keypair
from cipher.ecc.key_storage import (
    load_private_key,
    public_key_bytes,
    save_private_key,
)
from cipher.encryption import decrypt_message, derive_key, encrypt_message


st.set_page_config(page_title="ChatBox", page_icon="💬")
st.title("💬 ChatBox")
st.caption("ECDH · HKDF · AES-GCM · SQL Server")
st.markdown(
    """
    <style>
    .chatbox-message-row {
        display: flex;
        width: 100%;
        margin: 0.35rem 0 0.7rem;
    }
    .chatbox-message-row--outgoing { justify-content: flex-end; }
    .chatbox-message-row--incoming { justify-content: flex-start; }
    .chatbox-message-bubble {
        width: fit-content;
        max-width: 72%;
        padding: 0.65rem 0.9rem;
        border-radius: 1rem;
        overflow-wrap: anywhere;
        color: #f4f4f5;
        background: #252a34;
    }
    .chatbox-message-row--outgoing .chatbox-message-bubble {
        background: #075e54;
    }
    .chatbox-message-time {
        margin-top: 0.35rem;
        text-align: right;
        color: #b8c0cc;
        font-size: 0.72rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def to_b64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def from_b64(value: str) -> bytes:
    return base64.b64decode(value, validate=True)


def format_message_time(value: str) -> str:
    """Display SQL UTC timestamps in Vietnam local time."""
    timestamp = datetime.fromisoformat(value)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)

    vietnam_time = timestamp.astimezone(timezone(timedelta(hours=7)))
    today_vietnam = datetime.now(timezone(timedelta(hours=7))).date()
    if vietnam_time.date() == today_vietnam:
        return vietnam_time.strftime("%H:%M")
    return vietnam_time.strftime("%d/%m/%Y %H:%M")


if "server_url" not in st.session_state:
    st.session_state.server_url = "http://127.0.0.1:8000"
if "pending_identities" not in st.session_state:
    st.session_state.pending_identities = {}


def call_api(method: str, path: str, token: str | None = None, **kwargs):
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"

    response = requests.request(
        method,
        st.session_state.server_url.rstrip("/") + path,
        headers=headers,
        timeout=10,
        **kwargs,
    )
    response.raise_for_status()
    return response.json() if response.content else None


with st.sidebar:
    if st.session_state.get("token"):
        st.caption(f"Đang đăng nhập: **{st.session_state.username}**")
        if st.button("Đăng xuất", use_container_width=True):
            try:
                call_api("POST", "/auth/logout", token=st.session_state.token)
            except requests.RequestException:
                pass
            st.session_state.pop("token", None)
            st.session_state.pop("username", None)
            st.session_state.pop("private_key", None)
            st.session_state.pop("conversation_id", None)
            st.session_state.pop("conversation_peer", None)
            st.rerun()


token = st.session_state.get("token")
username = st.session_state.get("username")
if token and username and "private_key" not in st.session_state:
    # Discard old in-memory-only sessions created before local key persistence.
    st.session_state.pop("token", None)
    st.session_state.pop("username", None)
    token = username = None
    st.info("Phiên cũ đã hết khóa trong bộ nhớ. Đăng nhập lại để nạp khóa đã lưu.")

if not token or not username:
    with st.container(border=True):
        st.subheader("Đăng nhập hoặc tạo tài khoản")
        username_input = st.text_input("Username", key="auth_username").strip().lower()
        password_input = st.text_input(
            "Password", type="password", key="auth_password"
        )
        register_col, login_col = st.columns(2)

        if register_col.button("Tạo tài khoản", use_container_width=True):
            if len(username_input) < 3 or not password_input:
                st.error("Username cần ít nhất 3 ký tự và password không được trống.")
            else:
                registered = False
                try:
                    private_key = st.session_state.pending_identities.get(username_input)
                    if private_key is None:
                        private_key, _ = generate_keypair()
                        st.session_state.pending_identities[username_input] = private_key
                    call_api(
                        "POST",
                        "/auth/register",
                        json={
                            "username": username_input,
                            "password": password_input,
                            "public_key_b64": to_b64(public_key_bytes(private_key)),
                        },
                    )
                    registered = True
                    # Keep an encrypted local copy so a later Streamlit session
                    # can restore the same key instead of generating a new one.
                    save_private_key(username_input, password_input, private_key)
                    st.success(
                        "Tạo tài khoản thành công. Khóa riêng đã lưu mã hóa trên "
                        "thiết bị này. Bấm Đăng nhập để tiếp tục."
                    )
                except requests.HTTPError as exc:
                    st.error(f"Đăng ký thất bại: {exc.response.text}")
                except requests.RequestException as exc:
                    st.error(f"Không kết nối được server: {exc}")
                except (OSError, ValueError) as exc:
                    if registered:
                        st.error(
                            "Tài khoản đã được tạo nhưng không lưu được khóa riêng "
                            f"trên máy: {exc}. Giữ nguyên phiên này và xử lý quyền ghi file."
                        )
                    else:
                        st.error(f"Không tạo/lưu được khóa riêng: {exc}")

        if login_col.button("Đăng nhập", use_container_width=True):
            if not username_input or not password_input:
                st.error("Nhập username và password trước khi đăng nhập.")
            else:
                try:
                    try:
                        private_key = load_private_key(username_input, password_input)
                    except FileNotFoundError:
                        # Lets the user recover if registration succeeded but
                        # writing the key file failed in that same session.
                        private_key = st.session_state.pending_identities.get(
                            username_input
                        )
                        if private_key is None:
                            raise
                    result = call_api(
                        "POST",
                        "/auth/login",
                        json={"username": username_input, "password": password_input},
                    )
                    login_token = result["access_token"]
                    own_key = call_api(
                        "GET",
                        f"/users/{quote(username_input, safe='')}/public-key",
                        token=login_token,
                    )
                    if from_b64(own_key["public_key_b64"]) != public_key_bytes(
                        private_key
                    ):
                        try:
                            call_api("POST", "/auth/logout", token=login_token)
                        except requests.RequestException:
                            pass
                        st.error(
                            "Khóa riêng trên máy không khớp public key của tài khoản. "
                            "Không thể giải mã tin nhắn bằng khóa này."
                        )
                    else:
                        try:
                            save_private_key(
                                username_input, password_input, private_key
                            )
                        except OSError as exc:
                            try:
                                call_api("POST", "/auth/logout", token=login_token)
                            except requests.RequestException:
                                pass
                            st.error(f"Không lưu được khóa riêng trên máy: {exc}")
                            st.stop()
                        st.session_state.token = login_token
                        st.session_state.username = username_input
                        st.session_state.private_key = private_key
                        st.session_state.key_version = own_key["key_version"]
                        st.rerun()
                except FileNotFoundError:
                    st.error(
                        "Không tìm thấy khóa riêng trên máy này. Khóa riêng không được "
                        "lưu trên server nên không thể tải lại từ đó. Hãy khôi phục file "
                        "khóa từ bản sao lưu; nếu không có, cần tạo tài khoản mới và "
                        "các tin nhắn cũ mã hóa bằng khóa đã mất sẽ không đọc được."
                    )
                except (ValueError, TypeError):
                    st.error(
                        "Không mở được file khóa riêng. Kiểm tra password đã dùng "
                        "khi đăng ký tài khoản."
                    )
                except requests.HTTPError as exc:
                    st.error(f"Đăng nhập thất bại: {exc.response.text}")
                except requests.RequestException as exc:
                    st.error(f"Không kết nối được server: {exc}")

        with st.expander("Mất khóa riêng hoặc đăng nhập trên máy mới?"):
            st.warning(
                "Tạo khóa mới sẽ thay public key của tài khoản. Những tin nhắn cũ "
                "được mã hóa bằng khóa đã mất sẽ không giải mã được."
            )
            if st.button("Xác thực và tạo cặp khóa mới", use_container_width=True):
                if not username_input or not password_input:
                    st.error("Nhập username và password trước.")
                else:
                    try:
                        result = call_api(
                            "POST",
                            "/auth/login",
                            json={"username": username_input, "password": password_input},
                        )
                        login_token = result["access_token"]

                        private_key = st.session_state.pending_identities.get(
                            username_input
                        )
                        if private_key is None:
                            private_key, _ = generate_keypair()
                            st.session_state.pending_identities[
                                username_input
                            ] = private_key

                        # Persist first; if SQL update fails, this same pending
                        # key can be used to retry the explicit recovery action.
                        save_private_key(username_input, password_input, private_key)
                        key_result = call_api(
                            "PUT",
                            "/users/me/public-key",
                            token=login_token,
                            json={"public_key_b64": to_b64(public_key_bytes(private_key))},
                        )
                        st.session_state.token = login_token
                        st.session_state.username = username_input
                        st.session_state.private_key = private_key
                        st.session_state.key_version = key_result["key_version"]
                        st.session_state.key_recovery_notice = (
                            "Đã tạo khóa mới. Tin nhắn cũ cần khóa riêng cũ và sẽ "
                            "không đọc được bằng khóa mới."
                        )
                        st.rerun()
                    except requests.HTTPError as exc:
                        st.error(f"Không khôi phục được khóa: {exc.response.text}")
                    except requests.RequestException as exc:
                        st.error(f"Không kết nối được server: {exc}")
                    except (OSError, ValueError) as exc:
                        st.error(f"Không tạo/lưu được khóa mới: {exc}")
    st.stop()


if st.session_state.get("key_recovery_notice"):
    st.warning(st.session_state.pop("key_recovery_notice"))


with st.spinner("Đang tải hội thoại..."):
    try:
        users_result = call_api("GET", "/users", token=token)
        other_users = users_result["users"]
        conversation_result = call_api("GET", "/conversations", token=token)
        conversations = conversation_result["conversations"]
    except requests.HTTPError as exc:
        st.error(f"Không tải được danh sách chat/user: {exc.response.text}")
        st.stop()
    except requests.RequestException as exc:
        st.error(f"Không kết nối được server: {exc}")
        st.stop()


conversation_by_id = {
    item["conversation_id"]: item for item in conversations
}
conversation_by_peer = {
    item["peer_username"]: item for item in conversations
}

with st.sidebar:
    st.divider()
    st.subheader("💬 Tin nhắn")
    search_user = st.text_input(
        "Tìm người dùng",
        placeholder="Nhập username để bắt đầu chat",
        key="chat_user_search",
    ).strip().lower()

    if search_user:
        matches = [
            user for user in other_users if search_user in user.lower()
        ][:8]
        if matches:
            st.caption("Tài khoản đã đăng ký · có thể đang offline")
            for matched_user in matches:
                existing = conversation_by_peer.get(matched_user)
                button_label = (
                    f"Mở chat · {matched_user}"
                    if existing
                    else f"＋  {matched_user}"
                )
                if st.button(
                    button_label,
                    key=f"start_chat_{matched_user}",
                    use_container_width=True,
                ):
                    if existing:
                        st.session_state.conversation_id = existing[
                            "conversation_id"
                        ]
                        st.session_state.conversation_peer = matched_user
                    else:
                        try:
                            created = call_api(
                                "POST",
                                "/conversations",
                                token=token,
                                json={"peer_username": matched_user},
                            )
                            st.session_state.conversation_id = created[
                                "conversation_id"
                            ]
                            st.session_state.conversation_peer = matched_user
                        except requests.HTTPError as exc:
                            st.error(f"Không mở được chat: {exc.response.text}")
                            st.stop()
                        except requests.RequestException as exc:
                            st.error(f"Không kết nối được server: {exc}")
                            st.stop()
                    st.rerun()
        else:
            st.caption("Không tìm thấy username phù hợp.")

    st.markdown("**Hội thoại**")
    if conversations:
        for item in conversations:
            chat_id = item["conversation_id"]
            peer_name = item["peer_username"]
            active = chat_id == st.session_state.get("conversation_id")
            icon = "🟢" if active else "💬"
            if st.button(
                f"{icon}  {peer_name}",
                key=f"open_chat_{chat_id}",
                use_container_width=True,
            ):
                st.session_state.conversation_id = chat_id
                st.session_state.conversation_peer = peer_name
                st.rerun()
            sender = item.get("last_sender")
            if sender:
                summary = "Bạn đã gửi tin nhắn" if sender == username else "Có tin nhắn đã lưu"
            else:
                summary = "Bắt đầu cuộc trò chuyện"
            st.caption(f"{summary} · {item['last_activity']}")
    else:
        st.caption("Chưa có hội thoại. Tìm username phía trên để bắt đầu chat.")


conversation_id = st.session_state.get("conversation_id")
active_conversation = conversation_by_id.get(conversation_id)
if active_conversation is None:
    st.session_state.pop("conversation_id", None)
    st.session_state.pop("conversation_peer", None)
    st.title("💬 Tin nhắn")
    st.info("Chọn một hội thoại ở thanh bên hoặc tìm username để bắt đầu chat.")
    st.stop()

peer = active_conversation["peer_username"]
st.session_state.conversation_peer = peer

try:
    peer_record = call_api(
        "GET",
        f"/users/{quote(peer, safe='')}/public-key",
        token=token,
    )
    peer_public_key = from_b64(peer_record["public_key_b64"])
except requests.HTTPError as exc:
    st.error(f"Không tải được public key của {peer}: {exc.response.text}")
    st.stop()
except requests.RequestException as exc:
    st.error(f"Không tải được public key: {exc}")
    st.stop()


conversation_id = st.session_state.conversation_id
private_key = st.session_state.private_key
st.subheader(f"Chat với {peer}")

message_cache_key = f"chat_message_cache_{conversation_id}"
last_message_id_key = f"chat_last_message_id_{conversation_id}"
if message_cache_key not in st.session_state:
    st.session_state[message_cache_key] = []
    st.session_state[last_message_id_key] = 0


@st.fragment(run_every="3s")
def render_messages():
    try:
        new_messages = call_api(
            "GET",
            f"/conversations/{conversation_id}/messages",
            token=token,
            params={"after_id": st.session_state[last_message_id_key]},
        )
    except requests.RequestException as exc:
        st.error(f"Không tải được tin nhắn: {exc}")
        return

    if new_messages:
        st.session_state[message_cache_key].extend(new_messages)
        st.session_state[last_message_id_key] = max(
            int(message["id"]) for message in new_messages
        )

    for message in st.session_state[message_cache_key]:
        try:
            shared_secret = create_shared_secret(private_key, peer_public_key)
            key = derive_key(
                shared_secret,
                from_b64(message["salt_b64"]),
                message["conversation_id"],
            )
            text = decrypt_message(
                key,
                from_b64(message["nonce_b64"]),
                from_b64(message["ciphertext_b64"]),
                from_b64(message["aad_b64"]),
            )
            sender = message["sender_id"]
            direction = "outgoing" if sender == username else "incoming"
            safe_text = html.escape(text).replace("\n", "<br>")
            safe_time = html.escape(format_message_time(message["created_at"]))
            st.markdown(
                f'<div class="chatbox-message-row chatbox-message-row--{direction}">'
                f'<div class="chatbox-message-bubble">{safe_text}'
                f'<div class="chatbox-message-time">{safe_time}</div>'
                "</div></div>",
                unsafe_allow_html=True,
            )
        except Exception:
            st.warning(f"Không giải mã được message #{message['id']}.")


render_messages()

with st.form("send_message", clear_on_submit=True):
    text = st.text_input("Tin nhắn")
    submitted = st.form_submit_button("Gửi", use_container_width=True)

if submitted and text.strip():
    salt = os.urandom(16)
    aad = f"{conversation_id}|{username}|{peer}|v1".encode("utf-8")
    shared_secret = create_shared_secret(private_key, peer_public_key)
    key = derive_key(shared_secret, salt, conversation_id)
    nonce, ciphertext = encrypt_message(key, text, aad)

    try:
        call_api(
            "POST",
            "/messages",
            token=token,
            json={
                "conversation_id": conversation_id,
                "recipient_username": peer,
                "ciphertext_b64": to_b64(ciphertext),
                "nonce_b64": to_b64(nonce),
                "salt_b64": to_b64(salt),
                "aad_b64": to_b64(aad),
                "key_version": st.session_state.get("key_version", 1),
            },
        )
        st.rerun()
    except requests.HTTPError as exc:
        st.error(f"Gửi tin nhắn thất bại: {exc.response.text}")
    except requests.RequestException as exc:
        st.error(f"Không kết nối được server: {exc}")
