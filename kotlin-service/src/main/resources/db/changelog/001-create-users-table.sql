--liquibase formatted sql

--changeset modelforge:001-create-users-table runOnChange:true
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
--rollback DROP TABLE IF EXISTS users;

--changeset modelforge:001-create-users-index runOnChange:true
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
--rollback DROP INDEX IF EXISTS idx_users_email;
