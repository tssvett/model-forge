--liquibase formatted sql

--changeset modelforge:002-create-tasks-table runOnChange:true
CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    prompt TEXT,
    s3_input_key VARCHAR(512),
    s3_output_key VARCHAR(512),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
--rollback DROP TABLE IF EXISTS tasks;

--changeset modelforge:002-create-tasks-indexes runOnChange:true
CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at);
--rollback DROP INDEX IF EXISTS idx_tasks_created_at;
--rollback DROP INDEX IF EXISTS idx_tasks_status;
--rollback DROP INDEX IF EXISTS idx_tasks_user_id;
