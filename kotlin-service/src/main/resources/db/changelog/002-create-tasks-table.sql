--liquibase formatted sql

--changeset modelforge:002-drop-legacy-tasks-table
--preconditions onFail:MARK_RAN
--precondition-sql-check expectedResult:0 SELECT COUNT(*) FROM information_schema.columns WHERE table_schema='public' AND table_name='tasks' AND column_name='user_id'
DROP TABLE IF EXISTS tasks;

--changeset modelforge:002-create-tasks-table
--preconditions onFail:MARK_RAN
--precondition-sql-check expectedResult:0 SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='tasks'
CREATE TABLE tasks (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    prompt TEXT,
    s3_input_key VARCHAR(512),
    s3_output_key VARCHAR(512),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

--changeset modelforge:002-create-tasks-indexes
--preconditions onFail:MARK_RAN
--precondition-sql-check expectedResult:0 SELECT COUNT(*) FROM pg_indexes WHERE schemaname='public' AND indexname='idx_tasks_user_id'
CREATE INDEX idx_tasks_user_id ON tasks(user_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_created_at ON tasks(created_at);
