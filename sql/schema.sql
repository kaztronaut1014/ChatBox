IF DB_ID(N'ChatBox') IS NULL
    CREATE DATABASE ChatBox;
GO

USE ChatBox;
GO

IF OBJECT_ID(N'dbo.Users', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.Users (
        Username NVARCHAR(50) NOT NULL PRIMARY KEY,
        PasswordHash CHAR(64) NOT NULL,
        PublicKey VARBINARY(MAX) NOT NULL,
        KeyVersion INT NOT NULL
            CONSTRAINT DF_Users_KeyVersion DEFAULT 1,
        CreatedAt DATETIME2 NOT NULL
            CONSTRAINT DF_Users_CreatedAt DEFAULT SYSUTCDATETIME()
    );
END;
GO

IF OBJECT_ID(N'dbo.Conversations', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.Conversations (
        ConversationId UNIQUEIDENTIFIER NOT NULL PRIMARY KEY,
        CreatedAt DATETIME2 NOT NULL
            CONSTRAINT DF_Conversations_CreatedAt DEFAULT SYSUTCDATETIME()
    );
END;
GO

IF OBJECT_ID(N'dbo.ConversationMembers', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.ConversationMembers (
        ConversationId UNIQUEIDENTIFIER NOT NULL,
        Username NVARCHAR(50) NOT NULL,
        JoinedAt DATETIME2 NOT NULL
            CONSTRAINT DF_ConversationMembers_JoinedAt DEFAULT SYSUTCDATETIME(),

        CONSTRAINT PK_ConversationMembers
            PRIMARY KEY (ConversationId, Username),

        CONSTRAINT FK_ConversationMembers_Conversations
            FOREIGN KEY (ConversationId)
            REFERENCES dbo.Conversations(ConversationId),

        CONSTRAINT FK_ConversationMembers_Users
            FOREIGN KEY (Username)
            REFERENCES dbo.Users(Username)
    );
END;
GO

IF OBJECT_ID(N'dbo.Messages', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.Messages (
        MessageId BIGINT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        ConversationId UNIQUEIDENTIFIER NOT NULL,
        SenderUsername NVARCHAR(50) NOT NULL,
        RecipientUsername NVARCHAR(50) NOT NULL,
        Ciphertext VARBINARY(MAX) NOT NULL,
        Nonce BINARY(12) NOT NULL,
        HkdfSalt VARBINARY(16) NOT NULL,
        Aad VARBINARY(MAX) NOT NULL,
        KeyVersion INT NOT NULL
            CONSTRAINT DF_Messages_KeyVersion DEFAULT 1,
        ProtocolVersion INT NOT NULL
            CONSTRAINT DF_Messages_ProtocolVersion DEFAULT 1,
        CreatedAt DATETIME2 NOT NULL
            CONSTRAINT DF_Messages_CreatedAt DEFAULT SYSUTCDATETIME(),

        CONSTRAINT FK_Messages_Conversations
            FOREIGN KEY (ConversationId)
            REFERENCES dbo.Conversations(ConversationId),

        CONSTRAINT FK_Messages_Sender
            FOREIGN KEY (SenderUsername)
            REFERENCES dbo.Users(Username),

        CONSTRAINT FK_Messages_Recipient
            FOREIGN KEY (RecipientUsername)
            REFERENCES dbo.Users(Username)
    );
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = N'IX_Messages_Conversation_Message'
      AND object_id = OBJECT_ID(N'dbo.Messages')
)
BEGIN
    CREATE INDEX IX_Messages_Conversation_Message
        ON dbo.Messages (ConversationId, MessageId);
END;
GO