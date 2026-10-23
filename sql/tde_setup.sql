/*
    One-time TDE setup for the ChatBox database on a local SQL Server instance.

    Before running:
      1. Replace every REPLACE_WITH_* value below.
      2. Ensure the backup folder exists on the SQL Server machine and the SQL
         Server service account can write to it. This is a server-side path.
      3. Run in SSMS as a SQL Server administrator (not using the app account).
      4. Keep the certificate, private-key backup, and passwords outside Git and
         separate from the database/backup files.

    This script backs up the TDE certificate and private key before enabling
    TDE. Completed backup and encryption steps are skipped on reruns.
*/

USE master;
GO

IF DB_ID(N'ChatBox') IS NULL
    THROW 50001, 'Database ChatBox does not exist. Start the app once or create the database first.', 1;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.symmetric_keys
    WHERE name = N'##MS_DatabaseMasterKey##'
)
BEGIN
    CREATE MASTER KEY ENCRYPTION BY PASSWORD = 'zzz';
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.certificates
    WHERE name = N'ChatBoxTDECert'
)
BEGIN
    CREATE CERTIFICATE ChatBoxTDECert
        WITH SUBJECT = 'Certificate protecting the ChatBox TDE database encryption key';
END;
GO

/* Back up the certificate and its private key before using it for TDE.
   Paths must be writable by the SQL Server service account. Skip this if a
   backup has already been recorded, so a safe rerun won't overwrite files. */
IF EXISTS (
    SELECT 1
    FROM sys.certificates
    WHERE name = N'ChatBoxTDECert'
      AND pvt_key_last_backup_date IS NULL
)
BEGIN
    BACKUP CERTIFICATE ChatBoxTDECert
        TO FILE = 'D:\Documents\BMTT\ChatBoxTDECert.cer'
        WITH PRIVATE KEY (
            FILE = 'D:\Documents\BMTT\ChatBoxTDECert_PrivateKey.pvk',
            ENCRYPTION BY PASSWORD = 'zzz'
        );
END;
GO

USE ChatBox;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.dm_database_encryption_keys
    WHERE database_id = DB_ID()
)
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM master.sys.certificates
        WHERE name = N'ChatBoxTDECert'
          AND pvt_key_last_backup_date IS NOT NULL
    )
        THROW 50002, 'TDE certificate backup is missing. Back up ChatBoxTDECert before creating the DEK.', 1;

    CREATE DATABASE ENCRYPTION KEY
        WITH ALGORITHM = AES_256
        ENCRYPTION BY SERVER CERTIFICATE ChatBoxTDECert;
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM master.sys.certificates
    WHERE name = N'ChatBoxTDECert'
      AND pvt_key_last_backup_date IS NOT NULL
)
    THROW 50003, 'TDE certificate backup is missing. Database encryption was not enabled by this script.', 1;

DECLARE @encryption_state INT;

SELECT @encryption_state = encryption_state
FROM sys.dm_database_encryption_keys
WHERE database_id = DB_ID(N'ChatBox');

IF @encryption_state = 1
BEGIN
    ALTER DATABASE ChatBox SET ENCRYPTION ON;
END
ELSE IF @encryption_state IN (2, 3)
BEGIN
    PRINT 'TDE is already enabled or the encryption scan is in progress; skipping ALTER DATABASE.';
END
ELSE
BEGIN
    THROW 50004, 'Could not enable TDE: the database encryption key is missing or in an unexpected state.', 1;
END;
GO

/* Verify completion. encryption_state = 3 means fully encrypted;
   state = 2 means the encryption scan is still running. */
SELECT
    DB_NAME(database_id) AS database_name,
    encryption_state,
    CASE encryption_state
        WHEN 1 THEN 'No database encryption key'
        WHEN 2 THEN 'Encryption scan in progress'
        WHEN 3 THEN 'Encrypted'
        WHEN 4 THEN 'Key change in progress'
        WHEN 5 THEN 'Decryption scan in progress'
        WHEN 6 THEN 'Protection change in progress'
        ELSE 'Unknown'
    END AS encryption_status
FROM sys.dm_database_encryption_keys
WHERE database_id = DB_ID(N'ChatBox');
GO
