--liquibase formatted sql

--changeset modelforge:005-add-error-message-to-tasks
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS error_message TEXT;
--rollback ALTER TABLE tasks DROP COLUMN IF EXISTS error_message;
