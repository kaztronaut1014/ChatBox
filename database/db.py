import os
import re
import logging

import pyodbc


DB_NAME = os.getenv("CHATBOX_DB_NAME", "ChatBox")
SERVER = os.getenv("CHATBOX_SQL_SERVER", os.getenv("COMPUTERNAME", "localhost"))
DRIVER = os.getenv("CHATBOX_SQL_DRIVER", "ODBC Driver 17 for SQL Server")
logger = logging.getLogger(__name__)


def _connection_string(database: str) -> str:
    """Build the ODBC connection string from environment-configurable settings."""
    auth = os.getenv("CHATBOX_SQL_AUTH", "windows").lower()
    parts = [
        f"DRIVER={{{DRIVER}}}",
        f"SERVER={SERVER}",
        f"DATABASE={database}",
        "Encrypt=yes",
        "TrustServerCertificate=yes",
        "Connection Timeout=5",
    ]
    if auth == "windows":
        parts.append("Trusted_Connection=yes")
    elif auth == "sql":
        parts.extend([
            f"UID={os.environ['CHATBOX_SQL_USER']}",
            f"PWD={os.environ['CHATBOX_SQL_PASSWORD']}",
        ])
    else:
        raise ValueError("CHATBOX_SQL_AUTH phải là 'windows' hoặc 'sql'")
    return ";".join(parts) + ";"


def connect():
    return pyodbc.connect(_connection_string(DB_NAME))


def check_tde_status(connection=None) -> bool:
    """Check whether SQL Server reports TDE enabled for the configured DB."""
    owns_connection = connection is None
    current_connection = connection or connect()
    try:
        row = current_connection.cursor().execute(
            "SELECT is_encrypted FROM sys.databases WHERE name = ?", DB_NAME
        ).fetchone()
        if row is None:
            logger.warning("Không tìm thấy database %s để kiểm tra TDE.", DB_NAME)
            return False
        enabled = bool(row[0])
        if enabled:
            logger.info("TDE đã được bật cho database %s.", DB_NAME)
        else:
            logger.warning(
                "TDE chưa bật cho database %s. Chạy sql/tde_setup.sql một lần "
                "trong SSMS bằng tài khoản quản trị SQL Server.",
                DB_NAME,
            )
        return enabled
    finally:
        if owns_connection:
            current_connection.close()


def initialize_database() -> None:
    # Database phải được tạo từ master; kết nối thẳng tới ChatBox trước khi DB
    # tồn tại sẽ thất bại và không bao giờ chạy tới phần tạo bảng.
    master = pyodbc.connect(_connection_string("master"), autocommit=True)
    try:
        if not re.fullmatch(r"[A-Za-z0-9_]+", DB_NAME):
            raise ValueError("CHATBOX_DB_NAME chỉ được chứa chữ, số và dấu gạch dưới")
        master.cursor().execute(
            f"IF DB_ID(N'{DB_NAME}') IS NULL CREATE DATABASE [{DB_NAME}]"
        )
    finally:
        master.close()

    statements = [
        """
        IF OBJECT_ID('dbo.Users', 'U') IS NULL
        CREATE TABLE dbo.Users (
            Username NVARCHAR(50) NOT NULL PRIMARY KEY,
            PasswordHash CHAR(64) NOT NULL,
            PublicKey VARBINARY(MAX) NOT NULL,
            KeyVersion INT NOT NULL DEFAULT 1,
            CreatedAt DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
        )
        """,
        """
        IF OBJECT_ID('dbo.Conversations', 'U') IS NULL
        CREATE TABLE dbo.Conversations (
            ConversationId UNIQUEIDENTIFIER NOT NULL PRIMARY KEY,
            CreatedAt DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
        )
        """,
        """
        IF OBJECT_ID('dbo.ConversationMembers', 'U') IS NULL
        CREATE TABLE dbo.ConversationMembers (
            ConversationId UNIQUEIDENTIFIER NOT NULL,
            Username NVARCHAR(50) NOT NULL,
            JoinedAt DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_ConversationMembers
                PRIMARY KEY (ConversationId, Username),
            CONSTRAINT FK_ConversationMembers_Conversations
                FOREIGN KEY (ConversationId)
                REFERENCES dbo.Conversations(ConversationId),
            CONSTRAINT FK_ConversationMembers_Users
                FOREIGN KEY (Username)
                REFERENCES dbo.Users(Username)
        )
        """,
        """
        IF OBJECT_ID('dbo.Messages', 'U') IS NULL
        CREATE TABLE dbo.Messages (
            MessageId BIGINT IDENTITY(1,1) NOT NULL PRIMARY KEY,
            ConversationId UNIQUEIDENTIFIER NOT NULL,
            SenderUsername NVARCHAR(50) NOT NULL,
            RecipientUsername NVARCHAR(50) NOT NULL,
            Ciphertext VARBINARY(MAX) NOT NULL,
            Nonce BINARY(12) NOT NULL,
            HkdfSalt VARBINARY(16) NOT NULL,
            Aad VARBINARY(MAX) NOT NULL,
            KeyVersion INT NOT NULL DEFAULT 1,
            ProtocolVersion INT NOT NULL DEFAULT 1,
            CreatedAt DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
            CONSTRAINT FK_Messages_Conversations
                FOREIGN KEY (ConversationId)
                REFERENCES dbo.Conversations(ConversationId)
        )
        """,
        """
        IF NOT EXISTS (
            SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_Messages_Sender'
        )
        ALTER TABLE dbo.Messages ADD CONSTRAINT FK_Messages_Sender
            FOREIGN KEY (SenderUsername) REFERENCES dbo.Users(Username)
        """,
        """
        IF NOT EXISTS (
            SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_Messages_Recipient'
        )
        ALTER TABLE dbo.Messages ADD CONSTRAINT FK_Messages_Recipient
            FOREIGN KEY (RecipientUsername) REFERENCES dbo.Users(Username)
        """,
        """
        IF NOT EXISTS (
            SELECT 1 FROM sys.indexes
            WHERE name = 'IX_Messages_Conversation_Message'
              AND object_id = OBJECT_ID('dbo.Messages')
        )
        CREATE INDEX IX_Messages_Conversation_Message
            ON dbo.Messages (ConversationId, MessageId)
        """,
        """
        SET XACT_ABORT ON;
        BEGIN TRANSACTION;

        CREATE TABLE #DuplicateConversationMap (
            DuplicateId UNIQUEIDENTIFIER NOT NULL PRIMARY KEY,
            CanonicalId UNIQUEIDENTIFIER NOT NULL
        );

        ;WITH ConversationPairs AS (
            SELECT
                first_member.ConversationId,
                first_member.Username AS UserA,
                second_member.Username AS UserB
            FROM dbo.ConversationMembers AS first_member
            JOIN dbo.ConversationMembers AS second_member
              ON second_member.ConversationId = first_member.ConversationId
             AND first_member.Username < second_member.Username
            WHERE (
                SELECT COUNT(*)
                FROM dbo.ConversationMembers AS member_count
                WHERE member_count.ConversationId = first_member.ConversationId
            ) = 2
        ), RankedConversations AS (
            SELECT
                pair.ConversationId,
                pair.UserA,
                pair.UserB,
                ROW_NUMBER() OVER (
                    PARTITION BY pair.UserA, pair.UserB
                    ORDER BY conversation.CreatedAt, pair.ConversationId
                ) AS RowNumber
            FROM ConversationPairs AS pair
            JOIN dbo.Conversations AS conversation
              ON conversation.ConversationId = pair.ConversationId
        )
        INSERT INTO #DuplicateConversationMap (DuplicateId, CanonicalId)
        SELECT duplicate.ConversationId, canonical.ConversationId
        FROM RankedConversations AS duplicate
        JOIN RankedConversations AS canonical
          ON canonical.UserA = duplicate.UserA
         AND canonical.UserB = duplicate.UserB
         AND canonical.RowNumber = 1
        WHERE duplicate.RowNumber > 1;

        UPDATE message
        SET ConversationId = duplicate_map.CanonicalId
        FROM dbo.Messages AS message
        JOIN #DuplicateConversationMap AS duplicate_map
          ON duplicate_map.DuplicateId = message.ConversationId;

        DELETE member
        FROM dbo.ConversationMembers AS member
        JOIN #DuplicateConversationMap AS duplicate_map
          ON duplicate_map.DuplicateId = member.ConversationId;

        DELETE conversation
        FROM dbo.Conversations AS conversation
        JOIN #DuplicateConversationMap AS duplicate_map
          ON duplicate_map.DuplicateId = conversation.ConversationId;

        COMMIT TRANSACTION;
        """,
    ]

    connection = connect()
    try:
        with connection:
            cursor = connection.cursor()
            for statement in statements:
                cursor.execute(statement)
    finally:
        connection.close()

    # Run the status query after schema/migration results have been drained and
    # their connection has been committed/closed. ODBC Driver 17 can otherwise
    # report HY000 "Connection is busy with results for another command".
    check_tde_status()
