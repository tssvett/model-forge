--liquibase formatted sql

--changeset modelforge:001-create-users-table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

--changeset modelforge:001-create-users-index
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
