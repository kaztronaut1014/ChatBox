import hashlib
import hmac
import uuid


def hash_password(password: str) -> str:
    """Theo lựa chọn của project: SHA-256 một lượt, không salt."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def create_user(connection, username: str, password: str, public_key: bytes) -> None:
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO dbo.Users (Username, PasswordHash, PublicKey)
        VALUES (?, ?, ?)
        """,
        username,
        hash_password(password),
        public_key,
    )


def verify_login(connection, username: str, password: str) -> bool:
    cursor = connection.cursor()
    row = cursor.execute(
        "SELECT PasswordHash FROM dbo.Users WHERE Username = ?",
        username,
    ).fetchone()

    if row is None:
        return False

    return hmac.compare_digest(row[0].strip(), hash_password(password))


def get_public_key(connection, username: str) -> tuple[bytes, int] | None:
    cursor = connection.cursor()
    row = cursor.execute(
        """
        SELECT PublicKey, KeyVersion
        FROM dbo.Users
        WHERE Username = ?
        """,
        username,
    ).fetchone()

    if row is None:
        return None

    return bytes(row[0]), int(row[1])


def replace_public_key(connection, username: str, public_key: bytes) -> int | None:
    cursor = connection.cursor()
    row = cursor.execute(
        """
        UPDATE dbo.Users
        SET PublicKey = ?, KeyVersion = KeyVersion + 1
        OUTPUT INSERTED.KeyVersion
        WHERE Username = ?
        """,
        public_key,
        username,
    ).fetchone()
    return int(row[0]) if row else None


def list_users(connection, exclude_username: str) -> list[str]:
    cursor = connection.cursor()
    rows = cursor.execute(
        "SELECT Username FROM dbo.Users WHERE Username <> ? ORDER BY Username",
        exclude_username,
    ).fetchall()
    return [str(row[0]) for row in rows]


def list_conversations(connection, username: str) -> list[dict]:
    """List persisted 1-1 chats, newest activity first, without exposing content."""
    cursor = connection.cursor()
    rows = cursor.execute(
        """
        SELECT
            mine.ConversationId,
            peer.Username,
            COALESCE(last_message.CreatedAt, conversation.CreatedAt) AS LastActivity,
            last_message.SenderUsername
        FROM dbo.ConversationMembers AS mine
        JOIN dbo.ConversationMembers AS peer
          ON peer.ConversationId = mine.ConversationId
         AND peer.Username <> mine.Username
        JOIN dbo.Conversations AS conversation
          ON conversation.ConversationId = mine.ConversationId
        OUTER APPLY (
            SELECT TOP (1) message.CreatedAt, message.SenderUsername
            FROM dbo.Messages AS message
            WHERE message.ConversationId = mine.ConversationId
            ORDER BY message.MessageId DESC
        ) AS last_message
        WHERE mine.Username = ?
        ORDER BY COALESCE(last_message.CreatedAt, conversation.CreatedAt) DESC
        """,
        username,
    ).fetchall()

    return [
        {
            "conversation_id": str(row[0]),
            "peer_username": str(row[1]),
            "last_activity": row[2].isoformat(),
            "last_sender": row[3],
        }
        for row in rows
    ]


def get_or_create_conversation(
    connection, username_a: str, username_b: str
) -> str:
    """Return the existing 1-1 conversation, creating it only when absent."""
    cursor = connection.cursor()
    existing = cursor.execute(
        """
        SELECT TOP (1) first_member.ConversationId
        FROM dbo.ConversationMembers AS first_member
        JOIN dbo.ConversationMembers AS second_member
          ON second_member.ConversationId = first_member.ConversationId
        WHERE first_member.Username = ? AND second_member.Username = ?
        ORDER BY first_member.JoinedAt, first_member.ConversationId
        """,
        username_a,
        username_b,
    ).fetchone()
    if existing is not None:
        return str(existing[0])
    return create_conversation(connection, username_a, username_b)


def create_conversation(connection, username_a: str, username_b: str) -> str:
    cursor = connection.cursor()

    conversation_id = cursor.execute(
        """
        INSERT INTO dbo.Conversations (ConversationId)
        OUTPUT INSERTED.ConversationId
        VALUES (NEWID())
        """
    ).fetchone()[0]

    cursor.execute(
        """
        INSERT INTO dbo.ConversationMembers (ConversationId, Username)
        VALUES (?, ?), (?, ?)
        """,
        conversation_id,
        username_a,
        conversation_id,
        username_b,
    )

    return str(conversation_id)


def is_conversation_member(connection, conversation_id: str, username: str) -> bool:
    cursor = connection.cursor()
    row = cursor.execute(
        """
        SELECT 1
        FROM dbo.ConversationMembers
        WHERE ConversationId = ? AND Username = ?
        """,
        conversation_id,
        username,
    ).fetchone()

    return row is not None


def add_message(
    connection,
    conversation_id: str,
    sender: str,
    recipient: str,
    ciphertext: bytes,
    nonce: bytes,
    salt: bytes,
    aad: bytes,
    key_version: int,
) -> int:
    cursor = connection.cursor()
    row = cursor.execute(
        """
        INSERT INTO dbo.Messages (
            ConversationId,
            SenderUsername,
            RecipientUsername,
            Ciphertext,
            Nonce,
            HkdfSalt,
            Aad,
            KeyVersion
        )
        OUTPUT INSERTED.MessageId
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        conversation_id,
        sender,
        recipient,
        ciphertext,
        nonce,
        salt,
        aad,
        key_version,
    ).fetchone()

    return int(row[0])


def get_messages(
    connection, conversation_id: str, after_id: int = 0
) -> list[dict]:
    cursor = connection.cursor()
    rows = cursor.execute(
        """
        SELECT
            MessageId,
            ConversationId,
            SenderUsername,
            RecipientUsername,
            Ciphertext,
            Nonce,
            HkdfSalt,
            Aad,
            KeyVersion,
            CreatedAt
        FROM dbo.Messages
        WHERE ConversationId = ? AND MessageId > ?
        ORDER BY MessageId
        """,
        conversation_id,
        after_id,
    ).fetchall()

    return [
        {
            "id": int(row[0]),
            "conversation_id": str(row[1]),
            "sender_id": row[2],
            "recipient_id": row[3],
            "ciphertext": bytes(row[4]),
            "nonce": bytes(row[5]),
            "salt": bytes(row[6]),
            "aad": bytes(row[7]),
            "key_version": int(row[8]),
            "created_at": row[9].isoformat(),
        }
        for row in rows
    ]
